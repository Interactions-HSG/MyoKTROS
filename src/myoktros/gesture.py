# -*- coding: utf-8 -*-
import argparse
import logging
from enum import Enum
from pathlib import Path, PurePath

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from myo.types import EMGMode
from sklearn.neighbors import KNeighborsClassifier

logger = logging.getLogger(__name__)

N_SENSORS = 8


class Gesture(Enum):
    RELAX = 0
    GRAB = 1
    STRETCH_FINGER = 2
    EXTENSION = 3
    THUMBS_UP = 4
    HORN = 5


class GestureModel:
    def __init__(self, name: str, em: EMGMode, n_periods: int, n_samples: int):
        self.name = name
        self.emg_mode = em
        self.n_periods = n_periods
        self.n_samples = n_samples

    def extract_features_from_queue(self, queue: list):
        assert len(queue) == self.n_periods * self.n_samples
        features = [None] * self.n_periods
        for p in range(self.n_periods):
            buf = []
            for s in range(self.n_samples):  # for each n_samples
                data = queue[p * self.n_samples + s]
                buf.append(data)

            npbuf = np.array(buf)
            features[p] = np.concatenate((np.mean(npbuf, axis=0), np.std(npbuf, axis=0)))

        return features

    @classmethod
    def read_data(cls, args):
        data_path = Path(args.data)
        em = EMGMode(args.emg_mode)
        n_samples = args.n_samples

        # make numpy values easier to read.
        np.set_printoptions(precision=3, suppress=True)

        # read the data files
        data_files = list(data_path.glob(f"*-{em.name}-*.csv"))
        if len(data_files) == 0:
            logger.error(f"no data files found in {data_path.absolute()}")
            exit(1)
        df = pd.concat(map(pd.read_csv, data_files), ignore_index=True)

        if em == EMGMode.SEND_FILT:
            # drop the mask for FVData
            _ = df.pop('mask')

        # drop the timestamp
        _ = df.pop('timestamp')

        # extract the features for each n_samples
        features = []
        for gesture in Gesture:
            # get the rows with `g`
            g = gesture.value
            data = df[df['gesture'] == g].copy()

            # drop the last n rows to match with the multiple of n_samples
            n = data.shape[0] % n_samples
            data.drop(data.tail(n).index, inplace=True)

            # drop the column that only contians `g`
            _ = data.pop('gesture')

            # compute the mean and the standard deviation for n_samples
            for i in range(int(data.shape[0] / n_samples)):
                sample = data.iloc[i : i + 3, :]
                feat = np.concatenate((sample.mean(), sample.std(), (g,)))
                features.append(feat)

        # fmt: off
        columns = [
            [f"data{i}" for i in range(N_SENSORS)]
            + [f"std{i}" for i in range(N_SENSORS)]
            + ['gesture',],
        ]
        # fmt: on

        features = pd.DataFrame(features, columns=columns)
        labels = features.pop('gesture')

        return features, labels


class KerasSequentialModel(GestureModel):
    def __init__(self, em: EMGMode, n_periods: int, n_samples: int, model_path: PurePath):
        super().__init__('keras', em, n_periods, n_samples)
        self.model = tf.keras.models.load_model(model_path.absolute())

    @classmethod
    def fit(cls, args: argparse.Namespace):
        em = EMGMode(args.emg_mode)
        epochs = args.epochs
        learning_rate = args.learning_rate
        n_samples = args.n_samples

        # read the data files
        features, labels = cls.read_data(args)

        # SEND_FILT => input_shape: 8*2
        # SEND_EMG or SEND_RAW => input_shape: 16*2
        # assert n_sensors * 2 == features.shape[1]
        shape = features.shape[1]

        # keras.Sequential
        normalize = tf.keras.layers.Normalization()
        normalize.adapt(features)
        model = tf.keras.Sequential(
            [
                normalize,
                # first hidden layer, try diffrent number of perceptrons (100 here)
                # 16/32 arv/rms/alt channels on the input
                tf.keras.layers.Dense(100, activation="relu", input_shape=(shape,)),
                # second hidden layer
                tf.keras.layers.Dense(30, activation="relu"),
                # output layer, N gestures
                tf.keras.layers.Dense(len(Gesture), activation="sigmoid"),
            ]
        )
        model.compile(
            loss=tf.keras.losses.SparseCategoricalCrossentropy(),
            optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        )
        model.fit(
            features,
            labels,
            epochs=epochs,
        )

        # save the model
        model_path = Path(__file__).parent.parent.parent / "assets" / f"keras-{em.name}-{n_samples}-samples-model"
        model.save(model_path.absolute())
        logger.info(f"new model saved at {model_path.absolute()}")

    def predict(self, queue: list):
        features = self.extract_features_from_queue(queue)
        pred = [None] * self.n_periods
        for i, feat in enumerate(features):
            preds = self.model.predict(feat, verbose=0)
            pred[i] = np.argmax(preds, axis=1)[0]

        return Gesture(max(set(pred), key=pred.count))


class KNNClassifier(GestureModel):
    def __init__(self, em: EMGMode, n_periods: int, n_samples, model_path: PurePath):
        super().__init__('knn', em, n_periods, n_samples)
        self.model = joblib.load(model_path.absolute())

    @classmethod
    def fit(cls, args: argparse.Namespace):
        em = EMGMode(args.emg_mode)

        # read the data files
        features, labels = cls.read_data(args)

        model = KNeighborsClassifier(n_neighbors=args.k, metric="euclidean")
        model.fit(features, np.ravel(labels))

        # save the classifier with joblib
        model_path = (
            Path(__file__).parent.parent.parent / "assets" / f"knn-{em.name}-{args.n_samples}-samples-model.pkl"
        )
        joblib.dump(model, model_path.absolute(), protocol=2)
        logger.info(f"new model saved at {model_path.absolute()}")

    def predict(self, queue: list):
        features = self.extract_features_from_queue(queue)
        pred = [None] * self.n_periods
        for i, feat in enumerate(features):
            pred[i] = self.model.predict(np.array(feat).reshape(1, -1))[0]

        return Gesture(max(set(pred), key=pred.count))
