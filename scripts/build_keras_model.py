#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from myo.types import EMGMode
from tensorflow.keras import layers

# from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
# from myoktros.gesture import Gesture

# make numpy values easier to read.
np.set_printoptions(precision=3, suppress=True)

assets = Path(__file__).parent.parent / "assets"
datadir = assets / "keras_gesture_data"
df = pd.concat(map(pd.read_csv, list(datadir.glob(f"{EMGMode.SEND_FILT.name}-*.csv"))), ignore_index=True)

# the mask value in FVData is not useful
df = df.drop(columns="mask")

labels = df.pop('gesture')
_ = df.pop('timestamp')
features = df.copy()

# all features are in the same unit
features = np.array(features)

# keras.Sequential
normalize = layers.Normalization()
normalize.adapt(features)
model = tf.keras.Sequential(
    [
        normalize,
        # first hidden layer, try diffrent number of perceptrons (100 here)
        # 8 arv/rms/alt channels on the input
        layers.Dense(100, activation="relu", input_shape=(8,)),
        # second hidden layer
        layers.Dense(30, activation="relu"),
        # output layer, 7 gestures
        layers.Dense(7, activation="sigmoid"),
    ]
)
model.compile(
    loss=tf.keras.losses.SparseCategoricalCrossentropy(),
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
)

# train
# save best weights to avoid overfitting
"""
weights_path = assets / "weights.h5"
model_checkpoint = ModelCheckpoint(
    weights_path.absolute(),
    save_best_only=True,
    save_weights_only=True,
)
# stopping criterion
early_stopping = EarlyStopping(monitor='val_loss', patience=5)
"""
# actual training
history = model.fit(
    features,
    labels,
    epochs=30,  # depends on hyperparameters
    # validation_data=(valid,valid_labels),
    # callbacks=[early_stopping, model_checkpoint],
)

modelpath = assets / "keras_gesture_model"
model.save(modelpath.absolute())
