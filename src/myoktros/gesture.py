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

BATCH_SIZE = 100
EPOCHS = 1000
LEARNING_RATE = 1e-4
N_SENSORS = 8


class Gesture(Enum):
    RELAX = 0
    GRAB = 1
    STRETCH_FINGER = 2
    EXTENSION = 3
    THUMBS_UP = 4


class GestureModel:
    def __init__(self, name: str, em: EMGMode, n_samples: int):
        self.name = name
        self.emg_mode = em
        self.n_samples = n_samples

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

        def f(x, n):
            # reindex data per gesture
            x = x.reset_index(drop=False)
            # trim extra data to fit in multiples of n rows
            x.drop(x.tail(x.shape[0] % n).index, inplace=True)
            # save the 0 to n samples as a group
            return x.groupby(x.index // n, group_keys=True).apply(lambda x: x.reset_index(drop=False))

        # frame each n_samples
        df = df.groupby('gesture', group_keys=False).apply(f, n_samples)

        # drop the per gesture index and keep sequence # (level_0)
        df = df.drop(['level_0'], axis=1).reset_index(drop=False)
        df = df.rename(columns={'level_0': 'seq', 'level_1': 'sample'})

        # build gesture-seq column and make it as the new index
        df['gseq'] = df.apply(lambda x: f"{x['gesture']}-{x['seq']}", axis=1)
        df = df.drop(['index', 'seq'], axis=1)

        # pivot each sample for gseq
        df = df.pivot(columns=['sample'], index='gseq')

        # remove duplicate gesture columns
        df['gesture'] = df.pop('gesture')[0]

        return df


class KerasSequentialModel(GestureModel):
    def __init__(self, em: EMGMode, n_samples: int, model_path: PurePath):
        super().__init__('keras', em, n_samples)
        self.model = tf.keras.models.load_model(model_path.absolute())

    def evaluate(self, test_features, test_labels):
        self.model.evaluate(test_features, test_labels)

    @classmethod
    def fit(cls, args: argparse.Namespace):
        assets = Path(__file__).parent.parent.parent / "assets"
        em = EMGMode(args.emg_mode)
        n_samples = args.n_samples

        # read the data files
        features = cls.read_data(args)

        # reserve 10% samples for validation
        val_features = features.groupby('gesture').apply(lambda x: x.sample(frac=0.1)).reset_index(drop=True)

        # split the data into features and labels
        labels = features.pop('gesture')
        val_labels = val_features.pop('gesture')

        # input_shape: N_SENSORS*n_samples
        shape = features.shape[1]
        assert shape == N_SENSORS * n_samples

        # keras.Sequential
        normalize = tf.keras.layers.Normalization()
        normalize.adapt(features)
        model = tf.keras.Sequential(
            [
                normalize,
                # first hidden layer
                tf.keras.layers.Dense(100, activation="relu", input_shape=(shape,)),
                # second hidden layer
                tf.keras.layers.Dense(64, activation="relu"),
                # output layer, N gestures
                tf.keras.layers.Dense(len(Gesture), activation="softmax", name="prediction"),
            ]
        )
        model.compile(
            # optimizer=tf.keras.optimizers.RMSprop(),  # Optimizer
            # optimizer="rmsprop",
            optimizer=tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE),
            loss=tf.keras.losses.SparseCategoricalCrossentropy(),
            # loss="sparse_categorical_crossentropy",
            metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
            # metrics=["sparse_categorical_accuracy"],
        )
        # save best weights to avoid overfitting
        weight_path = assets / f"keras-{em.name}-{n_samples}-samples-weights.h5"
        model_checkpoint = tf.keras.callbacks.ModelCheckpoint(
            weight_path,
            save_best_only=True,
            save_weights_only=True,
        )
        # stopping criterion
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=5,
        )
        history = model.fit(
            features,
            labels,
            batch_size=BATCH_SIZE,
            callbacks=[early_stopping, model_checkpoint],
            epochs=EPOCHS,
            shuffle=True,
            validation_data=(val_features, val_labels),
            validation_split=0.3,
        )
        _ = history

        # load best weights
        model.load_weights(weight_path)

        # evaluate on the validation sets
        model.evaluate(val_features, val_labels)

        # save the model
        model_path = assets / f"keras-{em.name}-{n_samples}-samples-model"
        model.save(model_path.absolute())
        logger.info(f"new model saved at {model_path.absolute()}")

    def predict(self, queue: list):
        feat = np.array(queue).reshape(1, -1)
        preds = self.model.predict(feat, verbose=0)

        return Gesture(np.argmax(preds, axis=1)[0])


class KNNClassifier(GestureModel):
    def __init__(self, em: EMGMode, n_samples, model_path: PurePath):
        super().__init__('knn', em, n_samples)
        self.model = joblib.load(model_path.absolute())

    @classmethod
    def fit(cls, args: argparse.Namespace):
        em = EMGMode(args.emg_mode)

        # read the data files
        features = cls.read_data(args)
        labels = features.pop('gesture')

        model = KNeighborsClassifier(n_neighbors=args.k, metric="euclidean")
        model.fit(features, np.ravel(labels))

        # save the classifier with joblib
        model_path = (
            Path(__file__).parent.parent.parent / "assets" / f"knn-{em.name}-{args.n_samples}-samples-model.pkl"
        )
        joblib.dump(model, model_path.absolute(), protocol=2)
        logger.info(f"new model saved at {model_path.absolute()}")

    def predict(self, queue: list):
        feat = np.array(queue).reshape(1, -1)
        # TODO: check the knn predict return
        pred = self.model.predict(feat.reshape(1, -1))
        return Gesture(max(set(pred), key=pred.count))
