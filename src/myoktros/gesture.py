# -*- coding: utf-8 -*-
import logging
import math
from pathlib import Path

import aenum
import joblib
import myo
import numpy as np

logger = logging.getLogger(__name__)


class Gesture(aenum.Enum):
    RELAX = 0
    GRAB = 1
    STRETCH_FINGER = 2
    BEND_WRIST = 3  # extension
    FLEXION = 4


class GestureClassifierKeras:
    def __init__(self, n_periods: int = 3, n_samples: int = 3):
        p = Path(__file__).parent.parent.parent / "assets" / "keras_classifier.pkl"
        self.model = joblib.load(p.absolute())

    def predict(self, data: myo.FVData):
        return Gesture(self.model.predict(data))


class GestureClassifierLegacy:
    def __init__(self, n_periods: int = 3, n_samples: int = 3):
        p = Path(__file__).parent.parent.parent / "assets" / "legacy_classifier.pkl"
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
