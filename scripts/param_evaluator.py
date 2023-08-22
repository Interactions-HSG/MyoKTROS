#!/usr/bin/env python3
import logging
import time
from pathlib import Path

import myo
import myoktros
import numpy as np
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split  # , KFold


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
)

# global variables
aggregate_all = False
arm_dominance = "right"
assets_path = Path(__file__).parent.parent / "assets"
config_path = Path(__file__).parent.parent / "config.ini"
data_path = Path.cwd() / "data"
emg_mode = myo.types.EMGMode.SEND_FILT
knn_k = 3
knn_algorithm = "auto"
knn_metric = "minkowski"
svm_c = 1.0
svm_degree = 3
svm_gamma = "scale"

# eval parameters
# users = ['jan', 'ganesh', 'lukas', 'erik', 'kim', 'kenan', 'felix']
users = ['iomz']

# configurations
myoktros.Gesture.load_config(config_path)

# options
np.set_printoptions(precision=3, suppress=True)
print(myoktros.Gesture.names)

date = time.strftime("%Y%m%d%H%M%S")
p = data_path / f"eval-{date}.csv"
with open(p.absolute(), "w") as f:
    print("user,n_samples,train_size,model,acc,t", file=f)

# TODO: change u to '' and adjust train_size incrementation from 10 to 100
for u in users:
    for n_samples in [5, 25, 50]:
        features = myoktros.GestureModel.read_data(data_path, aggregate_all, arm_dominance, emg_mode, n_samples, u)
        labels = features.pop('gesture')
        x_train_split, x_test, y_train_split, y_test = train_test_split(
            features, labels, train_size=0.85, random_state=42
        )

        for count in range(1, 1000):
            train_size = len(myoktros.Gesture.names) * count
            if len(y_train_split) <= train_size:
                continue
            x_train, _, y_train, _ = train_test_split(
                x_train_split, y_train_split, train_size=train_size, random_state=42
            )
            logger.info(f"evaluating {u}: n_samples: {n_samples}, train_size: {train_size}")

            ksm, ksm_t = myoktros.KerasSequentialModel.fit(
                x_train,
                x_test,
                y_train,
                y_test,
                aggregate_all,
                arm_dominance,
                assets_path,
                emg_mode,
                n_samples,
                u,
            )

            knn, knn_t = myoktros.KNNClassifier.fit(
                x_train,
                x_test,
                y_train,
                y_test,
                aggregate_all,
                arm_dominance,
                assets_path,
                emg_mode,
                knn_k,
                knn_algorithm,
                knn_metric,
                n_samples,
                u,
            )

            svm_linear, svm_linear_t = myoktros.SVMClassifier.fit(
                x_train,
                x_test,
                y_train,
                y_test,
                aggregate_all,
                arm_dominance,
                assets_path,
                emg_mode,
                n_samples,
                svm_c,
                svm_degree,
                svm_gamma,
                'linear',
                u,
            )
            svm_poly, svm_poly_t = myoktros.SVMClassifier.fit(
                x_train,
                x_test,
                y_train,
                y_test,
                aggregate_all,
                arm_dominance,
                assets_path,
                emg_mode,
                n_samples,
                svm_c,
                svm_degree,
                svm_gamma,
                'poly',
                u,
            )
            svm_rbf, svm_rbf_t = myoktros.SVMClassifier.fit(
                x_train,
                x_test,
                y_train,
                y_test,
                aggregate_all,
                arm_dominance,
                assets_path,
                emg_mode,
                n_samples,
                svm_c,
                svm_degree,
                svm_gamma,
                'rbf',
                u,
            )

            with open(p.absolute(), "a") as f:
                user = u
                if user == '':
                    user = 'all'

                # ksm
                ksm_acc = ksm.evaluate(x_test, y_test)[1]
                print(f"{user},{n_samples},{train_size},DNN,{ksm_acc},{ksm_t}", file=f)

                # knn
                predicted_labels = knn.predict(x_test.values)
                knn_acc = accuracy_score(y_test, predicted_labels)
                print(f"{user},{n_samples},{train_size},KNN,{knn_acc},{knn_t}", file=f)

                # svm
                predicted_labels = svm_linear.predict(x_test.values)
                svm_acc = accuracy_score(y_test, predicted_labels)
                print(f"{user},{n_samples},{train_size},SVM_linear,{svm_acc},{svm_linear_t}", file=f)
                predicted_labels = svm_poly.predict(x_test.values)
                svm_acc = accuracy_score(y_test, predicted_labels)
                print(f"{user},{n_samples},{train_size},SVM_poly,{svm_acc},{svm_poly_t}", file=f)
                predicted_labels = svm_rbf.predict(x_test.values)
                svm_acc = accuracy_score(y_test, predicted_labels)
                print(f"{user},{n_samples},{train_size},SVM_rbf,{svm_acc},{svm_rbf_t}", file=f)
