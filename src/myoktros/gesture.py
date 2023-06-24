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
np.set_printoptions(precision=3, suppress=True)


BATCH_SIZE = 50
EPOCHS = 1000
LEARNING_RATE = 1e-3
N_SENSORS = 8


class Gesture(Enum):
    REST = 0
    GRAB = 1
    TIGER = 2
    HORN = 3
    PEACE = 4
    TENNET = 5
    # OK = 6


class GestureModel:
    def __init__(self, name: str, ad: str, em: EMGMode, n_samples: int):
        self.name = name
        self.arm_dominance = ad
        self.emg_mode = em
        self.n_samples = n_samples

    @classmethod
    def read_data(cls, data_path: PurePath, arm_dominance: str, emg_mode: EMGMode, n_samples: int):
        # iterate the record directories
        data = None
        for session in sorted(data_path.glob('*')):
            if not session.is_dir():
                continue

            # read the data files
            gesture_names = [g.name.lower() for g in Gesture]
            data_files = sorted(
                filter(
                    lambda f: any([gnl in f.name for gnl in gesture_names]),
                    session.glob(f"{arm_dominance}-{emg_mode.name.lower()}-*.csv"),
                )
            )
            if len(data_files) == 0:
                logger.info(f"no data files found in {session.absolute()}")
                continue
            for f in data_files:
                logger.info(f"reading {f.absolute()}")

            # read the recorded data for all the gestures during the session
            df = pd.concat(map(pd.read_csv, data_files), ignore_index=True)

            if emg_mode == EMGMode.SEND_FILT:
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

            # build the unique id column and make it as the new index
            df['id'] = df.apply(lambda x: f"{session.name}-{x['gesture']}-{x['seq']}", axis=1)
            df = df.drop(['index', 'seq'], axis=1)

            # pivot each sample for gseq
            df = df.pivot(columns=['sample'], index='id')

            if data is None:
                data = df
            else:
                data = pd.concat([data, df])

        # remove duplicate gesture columns
        """
        PerformanceWarning: DataFrame is highly fragmented.
        This is usually the result of calling `frame.insert` many times, which has poor performance.
        Consider joining all columns at once using pd.concat(axis=1) instead.
        To get a de-fragmented frame, use `newframe = frame.copy()`
        """
        if data is not None:
            data['gesture'] = data.pop('gesture')[0]

        return data


class KerasSequentialModel(GestureModel):
    def __init__(self, assets_path: PurePath, arm_dominance: str, emg_mode: EMGMode, n_samples: int):
        super().__init__('keras', arm_dominance, emg_mode, n_samples)
        # check if the model exists
        model_path = assets_path / f"keras-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model"
        if not model_path.exists():
            logger.error(f"model: {model_path.absolute()} not found")
            exit(1)

        self.model = tf.keras.models.load_model(model_path.absolute())

    def evaluate(self, test_features, test_labels):
        self.model.evaluate(test_features, test_labels)

    @classmethod
    def fit(cls, args: argparse.Namespace):
        arm_dominance = args.arm_dominance
        assets = Path(__file__).parent.parent.parent / "assets"
        data_path = Path(args.data)
        emg_mode = EMGMode(args.emg_mode)
        n_samples = args.n_samples

        # read the data files
        features = cls.read_data(
            data_path,
            arm_dominance,
            emg_mode,
            n_samples,
        )

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
                # 1st hidden layer
                tf.keras.layers.Dense(200, activation="sigmoid", input_shape=(shape,)),
                # 2nd hidden layer
                tf.keras.layers.Dense(100, activation="sigmoid"),
                # 3rd hidden layer
                tf.keras.layers.Dense(50, activation="sigmoid"),
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
        weight_path = assets / f"keras-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model" / "weights.h5"
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
        model_path = assets / f"keras-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model"
        model.save(model_path.absolute())
        logger.info(f"new model saved at {model_path.absolute()}")

    def predict(self, queue: list):
        feat = np.array(queue).reshape(1, -1)
        preds = self.model.predict(feat, verbose=0)

        return Gesture(np.argmax(preds, axis=1)[0])


class KNNClassifier(GestureModel):
    def __init__(self, assets_path: PurePath, arm_dominance: str, emg_mode: EMGMode, n_samples):
        super().__init__('knn', arm_dominance, emg_mode, n_samples)
        # check if the model exists
        model_path = assets_path / f"knn-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model.pkl"
        if not model_path.exists():
            logger.error(f"model: {model_path.absolute()} not found")
            exit(1)

        self.model = joblib.load(model_path.absolute())

    @classmethod
    def fit(cls, args: argparse.Namespace):
        arm_dominance = args.arm_dominance
        data_path = Path(args.data)
        emg_mode = EMGMode(args.emg_mode)
        n_samples = args.n_samples

        # read the data files
        features = cls.read_data(
            data_path,
            arm_dominance,
            emg_mode,
            n_samples,
        )
        labels = features.pop('gesture')

        model = KNeighborsClassifier(n_neighbors=args.k, metric="euclidean")
        model.fit(features, np.ravel(labels))

        # save the classifier with joblib
        model_path = (
            Path(__file__).parent.parent.parent
            / "assets"
            / f"knn-{arm_dominance}-{emg_mode.name.lower()}-{args.n_samples}-samples-model.pkl"
        )
        joblib.dump(model, model_path.absolute(), protocol=2)
        logger.info(f"new model saved at {model_path.absolute()}")

    def predict(self, queue: list):
        feat = np.array(queue).reshape(1, -1)
        # TODO: check the knn predict return
        pred = self.model.predict(feat.reshape(1, -1))
        return Gesture(max(set(pred), key=pred.count))
