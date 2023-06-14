#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

import joblib
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier

p = Path(__file__).parent.parent / "assets" / "legacy_features_felix.csv"
df = pd.read_csv(p.absolute(), header=None, index_col=None)
# drop the names
# df.columns = [
#    "EMG1",
#    "EMG2",
#    "EMG3",
#    "EMG4",
#    "EMG5",
#    "EMG6",
#    "EMG7",
#    "EMG8",
#    "VAR1",
#    "VAR2",
#    "VAR3",
#    "VAR4",
#    "VAR5",
#    "VAR6",
#    "VAR7",
#    "VAR8",
#    "class",
# ]

X_train = df.drop(df.columns[-1], axis=1)
y_train = df[df.columns[-1]]
k = 15
knn = KNeighborsClassifier(n_neighbors=k, metric="euclidean")
knn.fit(X_train, y_train)

# save the classifier with joblib
p = Path(__file__).parent.parent / "assets" / "legacy_classifier.pkl"
joblib.dump(knn, p.absolute(), protocol=2)
