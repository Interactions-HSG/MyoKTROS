# -*- coding: utf-8 -*-
import configparser
import logging
from enum import Enum
from pathlib import Path, PurePath

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from myo.types import EMGMode, Pose
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)
np.set_printoptions(precision=3, suppress=True)


BATCH_SIZE = 100
EPOCHS = 1000
LEARNING_RATE = 1e-3
N_SENSORS = 8


class BaseGesture(Enum):
    def __new__(cls, value):
        member = object.__new__(cls)
        member._value_ = value
        return member


class Gesture:
    __slots__ = ("Enum", "names")

    @classmethod
    def load_config(cls, p=Path.cwd() / 'config.ini'):
        config = configparser.ConfigParser()
        config.read(p)
        gestures = config['myoktros']['gestures'].strip().split("\n")
        cls.load_list(gestures)

    @classmethod
    def load_list(cls, gestures):
        cls.Enum = BaseGesture('Gesture.Enum', [(g, i) for i, g in enumerate(gestures)])
        cls.names = [g.name.lower() for g in cls.Enum]


class GestureModel:
    data_columns = [f"data{i}" for i in range(8)]

    def __init__(self, name: str, ad: str, em: EMGMode, n_samples: int):
        self.name = name
        self.arm_dominance = ad
        self.emg_mode = em
        self.n_samples = n_samples

    @classmethod
    def get_default_trigger_map(cls):
        tm = {}
        for g in Gesture.Enum:
            tm[g] = None
        for p in Pose:
            tm[p] = None
        return tm

    @classmethod
    def read_csv_data(cls, p: PurePath):
        for g in Gesture.Enum:
            if g.name.lower() in p.name:
                df = pd.read_csv(p)
                df['gesture'] = g.value
                return df
        return None

    @classmethod
    def read_data(cls, session: PurePath, arm_dominance: str, emg_mode: EMGMode):
        if not session.is_dir():
            return None

        # read the data files
        data_files = sorted(
            filter(
                lambda f: any([gnl in f.name for gnl in Gesture.names]),
                session.glob(f"{arm_dominance}-{emg_mode.name.lower()}-*.csv"),
            )
        )
        if len(data_files) == 0:
            logger.info(f"no data files found in {session.absolute()}")
            return None
        for f in data_files:
            logger.info(f"reading {f.absolute()}")

        # read the recorded data for all the gestures during the session
        df = pd.concat(map(cls.read_csv_data, data_files), ignore_index=True)

        if emg_mode == EMGMode.SEND_FILT:
            # drop the mask for FVData
            _ = df.pop('mask')
            df = df.rename(
                columns={
                    'fv0': 'data0',
                    'fv1': 'data1',
                    'fv2': 'data2',
                    'fv3': 'data3',
                    'fv4': 'data4',
                    'fv5': 'data5',
                    'fv6': 'data6',
                    'fv7': 'data7',
                }
            )
        else:
            df = df.rename(
                columns={
                    'emg0': 'data0',
                    'emg1': 'data1',
                    'emg2': 'data2',
                    'emg3': 'data3',
                    'emg4': 'data4',
                    'emg5': 'data5',
                    'emg6': 'data6',
                    'emg7': 'data7',
                }
            )

        # drop the timestamp
        _ = df.pop('timestamp')

        return df

    @classmethod
    def read_data_agg(cls, data_path: PurePath, arm_dominance: str, emg_mode: EMGMode, n_samples: int):
        data = None
        for session in sorted(data_path.glob('*')):
            df = cls.read_data(session, arm_dominance, emg_mode)

            if df is None:
                continue

            def f(x, n):
                # reindex data per gesture
                x = x.reset_index(drop=False)
                # trim extra data to fit in multiples of n rows
                x.drop(x.tail(x.shape[0] % n).index, inplace=True)
                # save the 0 to n samples as a group
                return x.groupby(x.index // n, group_keys=True).agg(['mean', 'std'])

            # frame each n_samples
            df = df.groupby('gesture', group_keys=False).apply(f, n_samples)

            # build the unique id column and make it as the new index
            df['id'] = df.apply(
                lambda x: f"{int(x['gesture']['mean'])}-{session.name}-{int(x['index']['mean'])}", axis=1
            )
            df = df.drop(['index', 'gesture'], axis=1)
            df['gesture'] = df['id'].apply(lambda x: int(x[0]))
            df = df.set_index('id')

            if data is None:
                data = df
            else:
                data = pd.concat([data, df])

        return data

    @classmethod
    def read_data_wide(cls, data_path: PurePath, arm_dominance: str, emg_mode: EMGMode, n_samples: int):
        # iterate the record directories
        data = None
        for session in sorted(data_path.glob('*')):
            df = cls.read_data(session, arm_dominance, emg_mode)

            if df is None:
                continue

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
            g = data.pop('gesture')[0]
            data['gesture'] = g

        return data


class KerasSequentialModel(GestureModel):
    def __init__(self, arm_dominance: str, assets_path: PurePath, emg_mode: EMGMode, n_samples: int):
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
    def fit(cls, arm_dominance: str, assets_path: PurePath, data_path: PurePath, emg_mode: EMGMode, n_samples: int):
        # read the data files
        features = cls.read_data_agg(
            data_path,
            arm_dominance,
            emg_mode,
            n_samples,
        )

        # reserve 10% samples for validation
        x_val = features.groupby('gesture').apply(lambda x: x.sample(frac=0.1)).reset_index(drop=True)

        # split the data into features and labels
        labels = features.pop('gesture')
        y_val = x_val.pop('gesture')

        # strip std
        # features = features.iloc[:, features.columns.get_level_values(1) == 'mean']
        # x_val = x_val.iloc[:, x_val.columns.get_level_values(1) == 'mean']

        x_train, x_test, y_train, y_test = train_test_split(features, labels, test_size=0.33, random_state=42)

        shape = features.shape[1]
        logger.info(f"input_shape: {shape}")

        # keras.Sequential
        model = tf.keras.Sequential(
            [
                # 1st hidden layer
                tf.keras.layers.Dense(200, activation="sigmoid", input_shape=(shape,)),
                # 2nd hidden layer
                tf.keras.layers.Dense(100, activation="sigmoid"),
                # 3rd hidden layer
                tf.keras.layers.Dense(50, activation="sigmoid"),
                # output layer, N gestures
                tf.keras.layers.Dense(len(Gesture.Enum), activation="sigmoid", name="prediction"),
            ]
        )
        model.compile(
            # optimizer=tf.keras.optimizers.RMSprop(),  # Optimizer
            # optimizer="rmsprop",
            optimizer=tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE),
            # loss=tf.keras.losses.SparseCategoricalCrossentropy(),
            loss="sparse_categorical_crossentropy",
            # metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
            metrics=["sparse_categorical_accuracy"],
        )
        # save best weights to avoid overfitting
        weight_path = (
            assets_path / f"keras-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model" / "weights.h5"
        )
        model_checkpoint = tf.keras.callbacks.ModelCheckpoint(
            weight_path,
            save_best_only=True,
            save_weights_only=True,
        )
        # stopping criterion
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            min_delta=1e-4,
            patience=10,  # number of epochs with no improvement
        )
        h = model.fit(  # noqa: F841
            features,
            labels,
            batch_size=BATCH_SIZE,
            callbacks=[early_stopping, model_checkpoint],
            epochs=EPOCHS,
            shuffle=True,
            validation_data=(x_val, y_val),
            validation_split=0.3,
        )
        # logger.info(f"history: {h.history}")

        # load best weights
        model.load_weights(weight_path)

        # evaluate on the validation sets
        model.evaluate(x_test, y_test)

        # save the model
        model_path = assets_path / f"keras-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model"
        model.save(model_path.absolute())
        logger.info(f"new model saved at {model_path.absolute()}")

        return model

    def predict(self, queue: list):
        # feat = np.array(queue).reshape(1, -1)  # reduce the dimension for the input layer
        df = pd.DataFrame(queue, columns=self.data_columns)
        # feat = df.groupby(df.index // self.n_samples, group_keys=True).agg(['mean']).iloc[0].to_numpy()
        feat = df.groupby(df.index // self.n_samples, group_keys=True).agg(['mean', 'std']).iloc[0].to_numpy()
        preds = self.model.predict(feat.reshape(1, -1), verbose=0)
        return Gesture.Enum(np.argmax(preds, axis=1))


class KNNClassifier(GestureModel):
    def __init__(
        self,
        arm_dominance: str,
        assets_path: PurePath,
        emg_mode: EMGMode,
        k: int,
        knn_metric: str,
        n_samples: int,
    ):
        super().__init__('knn', arm_dominance, emg_mode, n_samples)
        # check if the model exists
        model_path = (
            assets_path / f"knn-{k}-{knn_metric}-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model.pkl"
        )

        if not model_path.exists():
            logger.error(f"model: {model_path.absolute()} not found")
            exit(1)

        self.model = joblib.load(model_path.absolute())

    @classmethod
    def fit(
        cls,
        arm_dominance: str,
        assets_path: PurePath,
        data_path: PurePath,
        emg_mode: EMGMode,
        k: int,
        knn_algorithm: str,
        knn_metric: str,
        n_samples: int,
    ):
        # read the data files
        features = cls.read_data_agg(
            data_path,
            arm_dominance,
            emg_mode,
            n_samples,
        )
        labels = features.pop('gesture')
        # features = features.iloc[:, features.columns.get_level_values(1) == 'mean']

        model = KNeighborsClassifier(n_neighbors=k, algorithm=knn_algorithm, metric=knn_metric)
        model.fit(features, np.ravel(labels))

        # save the classifier with joblib
        model_path = (
            assets_path / f"knn-{k}-{knn_metric}-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model.pkl"
        )
        joblib.dump(model, model_path.absolute(), protocol=2)
        logger.info(f"new model saved at {model_path.absolute()}")

        return model

    def predict(self, queue: list):
        # feat = np.array(queue).reshape(1, -1)
        df = pd.DataFrame(queue, columns=self.data_columns)
        feat = df.groupby(df.index // self.n_samples, group_keys=True).agg(['mean', 'std']).iloc[0].to_numpy()
        pred = self.model.predict(feat.reshape(1, -1))[0]
        return Gesture.Enum(pred)


class SVMClassifier(GestureModel):
    def __init__(
        self,
        arm_dominance: str,
        assets_path: PurePath,
        emg_mode: EMGMode,
        n_samples: int,
        svm_c: float,
        svm_degree: int,
        svm_gamma: str,
        svm_kernel: str,
    ):
        super().__init__('svm', arm_dominance, emg_mode, n_samples)
        # check if the model exists
        if svm_kernel == 'poly':
            model_path = (
                assets_path
                / f"svm-{svm_c}-{svm_kernel}-{svm_degree}-{svm_gamma}-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model.pkl"  # noqa: E501
            )
        elif svm_kernel == 'linear':
            model_path = (
                assets_path
                / f"svm-{svm_c}-{svm_kernel}-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model.pkl"  # noqa: E501
            )
        else:
            model_path = (
                assets_path
                / f"svm-{svm_c}-{svm_kernel}-{svm_gamma}-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model.pkl"  # noqa: E501
            )

        if not model_path.exists():
            logger.error(f"model: {model_path.absolute()} not found")
            exit(1)

        self.model = joblib.load(model_path.absolute())

    @classmethod
    def fit(
        cls,
        arm_dominance: str,
        assets_path: PurePath,
        data_path: PurePath,
        emg_mode: EMGMode,
        n_samples: int,
        svm_c: float,
        svm_degree: int,
        svm_gamma: str,
        svm_kernel: str,
    ):
        # read the data files
        features = cls.read_data_agg(
            data_path,
            arm_dominance,
            emg_mode,
            n_samples,
        )
        labels = features.pop('gesture')
        # features = features.iloc[:, features.columns.get_level_values(1) == 'mean']

        if svm_kernel == 'poly':
            model = make_pipeline(StandardScaler(), SVC(C=svm_c, kernel=svm_kernel, degree=svm_degree, gamma=svm_gamma))
        elif svm_kernel == 'linear':
            model = make_pipeline(StandardScaler(), SVC(C=svm_c, kernel=svm_kernel))
        else:
            model = make_pipeline(StandardScaler(), SVC(C=svm_c, kernel=svm_kernel, gamma=svm_gamma))

        model.fit(features, np.ravel(labels))

        # save the classifier with joblib
        if svm_kernel == 'poly':
            model_path = (
                assets_path
                / f"svm-{svm_c}-{svm_kernel}-{svm_degree}-{svm_gamma}-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model.pkl"  # noqa: E501
            )
        elif svm_kernel == 'linear':
            model_path = (
                assets_path
                / f"svm-{svm_c}-{svm_kernel}-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model.pkl"  # noqa: E501
            )
        else:
            model_path = (
                assets_path
                / f"svm-{svm_c}-{svm_kernel}-{svm_gamma}-{arm_dominance}-{emg_mode.name.lower()}-{n_samples}-samples-model.pkl"  # noqa: E501
            )
        joblib.dump(model, model_path.absolute(), protocol=2)
        logger.info(f"new model saved at {model_path.absolute()}")

        return model

    def predict(self, queue: list):
        # feat = np.array(queue).reshape(1, -1)
        df = pd.DataFrame(queue, columns=self.data_columns)
        feat = df.groupby(df.index // self.n_samples, group_keys=True).agg(['mean', 'std']).iloc[0].to_numpy()
        pred = self.model.predict(feat.reshape(1, -1))[0]
        return Gesture.Enum(pred)
