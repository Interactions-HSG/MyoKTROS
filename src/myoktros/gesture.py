# -*- coding: utf-8 -*-
import logging
import math
from enum import Enum
from pathlib import Path, PurePath

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from myo.types import FVData

logger = logging.getLogger(__name__)


class Gesture(Enum):
    RELAX = 0
    GRAB = 1
    STRETCH_FINGER = 2
    FLEXION = 3
    HORN = 4
    # EXTENSION = 5
    # GUN = 6


class KerasSequentialModel:
    default_model_path = Path(__file__).parent.parent.parent / "assets" / "keras_gesture_model"

    def __init__(self):
        self.model = None
        modelpath = self.default_model_path
        if modelpath.exists() and modelpath.is_dir():
            self.load(self.default_model_path)
        else:
            logger.error(f"{modelpath.absolute()} not found")

    @classmethod
    def fit(cls, datapath: PurePath, epochs: int):
        # make numpy values easier to read.
        np.set_printoptions(precision=3, suppress=True)
        df = pd.concat(map(pd.read_csv, list(datapath.glob("SEND_FILT-*.csv"))), ignore_index=True)
        # the mask value in FVData is not useful
        df = df.drop(columns="mask")

        labels = df.pop('gesture')
        _ = df.pop('timestamp')
        features = df.copy()

        # all features are in the same unit
        features = np.array(features)

        # keras.Sequential
        normalize = tf.keras.layers.Normalization()
        normalize.adapt(features)
        model = tf.keras.Sequential(
            [
                normalize,
                # first hidden layer, try diffrent number of perceptrons (100 here)
                # 8 arv/rms/alt channels on the input
                tf.keras.layers.Dense(100, activation="relu", input_shape=(8,)),
                # second hidden layer
                tf.keras.layers.Dense(30, activation="relu"),
                # output layer, N gestures
                tf.keras.layers.Dense(len(Gesture), activation="sigmoid"),
            ]
        )
        model.compile(
            loss=tf.keras.losses.SparseCategoricalCrossentropy(),
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        )

        # actual training
        model.fit(
            features,
            labels,
            epochs=epochs,  # depends on hyperparameters
            # validation_data=(valid,valid_labels),
            # callbacks=[early_stopping, model_checkpoint],
        )

        modelpath = cls.default_model_path
        model.save(modelpath.absolute())
        logger.info(f"new model saved at {modelpath.absolute()}")

    def load(self, p: PurePath):
        self.model = tf.keras.models.load_model(p.absolute())

    def predict(self, fvd: FVData):
        preds = self.model.predict(np.array(fvd.fv), verbose=0)
        return Gesture(np.argmax(preds, axis=1)[0])


class KNNClassifier:
    def __init__(self, n_periods: int = 3, n_samples: int = 3):
        p = Path(__file__).parent.parent.parent / "assets" / "knn_classifier.pkl"
        self.knn = joblib.load(p.absolute())
        self.n_periods = n_periods
        self.n_samples = n_samples

    def predict(self, queue: list):
        # recreate Felix's EMG data normalization
        n_periods = self.n_periods
        n_samples = self.n_samples
        n_sensors = len(queue[0])  # should be 8

        features = [None] * n_periods
        for p in range(n_periods):
            buf = [0] * n_sensors * 2  # raw(8) + std(8) = 16
            for s in range(n_samples):
                for i in range(n_sensors):
                    emg_data = queue[p * n_samples + s]
                    v = emg_data[i]
                    buf[i] += abs(v / n_samples)
                    buf[n_sensors + i] += v * v / n_samples

            # replace the offset 8-15 with std
            for i in range(n_sensors):
                std = math.sqrt(buf[n_sensors + i] - (buf[i] ** 2))
                buf[n_sensors + i] = std

            features[p] = buf

        pred = [None] * n_periods
        for i, feat in enumerate(features):
            pred[i] = self.knn.predict(np.array(feat).reshape(1, -1))[0]

        return Gesture(max(set(pred), key=pred.count))
