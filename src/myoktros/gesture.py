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
    def __init__(
        self,
        name: str,
        aggregate_all: bool,
        ad: str,
        em: EMGMode,
        n_samples: int,
        user: str = "",
    ):
        self.name = name
        self.aggregate_all = aggregate_all
        self.arm_dominance = ad
        if self.aggregate_all:  # force SEND_FILT when aggregate_all
            self.data_columns = [f"data{str(i).zfill(2)}" for i in range(18)]  # 8 + 4 + 3 + 3
            self.emg_mode = EMGMode.SEND_FILT
        else:
            self.data_columns = [f"data{i}" for i in range(8)]
            self.emg_mode = em
        self.n_samples = n_samples
        self.user = user

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
    def read_agg(cls, session: PurePath, arm_dominance: str):
        """
        read emg+imu data for a single session
        """
        if not session.is_dir():
            return None

        # read the data files
        data_files = sorted(
            filter(
                lambda f: any([gnl in f.name for gnl in Gesture.names]),
                session.glob(f"{arm_dominance}-agg-*.csv"),
            )
        )
        if len(data_files) == 0:
            logger.debug(f"no data files found in {session.absolute()}")
            return None
        for f in data_files:
            logger.debug(f"reading {f.absolute()}")

        # read the recorded data for all the gestures during the session
        df = pd.concat(map(cls.read_csv_data, data_files), ignore_index=True)

        df = df.rename(
            columns={
                'fv0': 'data00',
                'fv1': 'data01',
                'fv2': 'data02',
                'fv3': 'data03',
                'fv4': 'data04',
                'fv5': 'data05',
                'fv6': 'data06',
                'fv7': 'data07',
                'quat_w': 'data08',
                'quat_x': 'data09',
                'quat_y': 'data10',
                'quat_z': 'data11',
                'accel_x': 'data12',
                'accel_y': 'data13',
                'accel_z': 'data14',
                'gyro_x': 'data15',
                'gyro_y': 'data16',
                'gyro_z': 'data17',
            }
        )

        # drop the timestamp
        _ = df.pop('timestamp')

        return df

    @classmethod
    def read_emg(cls, session: PurePath, arm_dominance: str, emg_mode: EMGMode):
        """
        read emg data for a single session
        """
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
            logger.debug(f"no data files found in {session.absolute()}")
            return None
        for f in data_files:
            logger.debug(f"reading {f.absolute()}")

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
    def read_data(
        cls,
        data_path: PurePath,
        aggregate_all: bool,
        arm_dominance: str,
        emg_mode: EMGMode,
        n_samples: int,
        user: str = "",
    ):
        """
        aggregate and read all the data
        """
        data = None
        # split the data per subject by using the suffix
        if user != "":
            sessions = sorted(data_path.glob(f"*-{user}"))
        else:
            sessions = sorted(data_path.glob('*'))
        for session in sessions:
            if aggregate_all:
                df = cls.read_agg(session, arm_dominance)
            else:
                df = cls.read_emg(session, arm_dominance, emg_mode)

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
            df['gesture'] = df['id'].apply(lambda x: int(x.split('-')[0]))
            df = df.set_index('id')

            if data is None:
                data = df
            else:
                data = pd.concat([data, df])

        return data

    @classmethod
    def train_test_split(cls, data: pd.DataFrame, test_size=0.25):
        pass


class KerasSequentialModel(GestureModel):
    def __init__(
        self,
        aggregate_all: bool,
        arm_dominance: str,
        assets_path: PurePath,
        emg_mode: EMGMode,
        n_samples: int,
        user: str = "",
    ):
        super().__init__('keras', aggregate_all, arm_dominance, emg_mode, n_samples, user)
        # check if the model exists
        model_path = KerasSequentialModel.get_model_path(
            aggregate_all,
            arm_dominance,
            assets_path,
            emg_mode,
            n_samples,
            user,
        )
        if not model_path.exists():
            logger.error(f"model: {model_path.absolute()} not found")
            exit(1)

        self.model = tf.keras.models.load_model(model_path.absolute())

    def evaluate(self, test_features, test_labels):
        self.model.evaluate(test_features, test_labels)

    @classmethod
    def fit(
        cls,
        x_train: pd.DataFrame,
        x_test: pd.Series,
        y_train: pd.DataFrame,
        y_test: pd.Series,
        aggregate_all: bool,
        arm_dominance: str,
        assets_path: PurePath,
        emg_mode: EMGMode,
        n_samples: int,
        user: str = "",
    ):
        """
        fit saves the model in assets_path
        """
        shape = x_train.shape[1]
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
            x_train,
            y_train,
            batch_size=BATCH_SIZE,
            callbacks=[early_stopping, model_checkpoint],
            epochs=EPOCHS,
            shuffle=True,
            validation_data=(x_test, y_test),
            validation_split=0.3,
        )
        # logger.info(f"history: {h.history}")

        # load best weights
        model.load_weights(weight_path)

        # evaluate on the validation sets
        model.evaluate(x_test, y_test)

        # save the model
        model_path = KerasSequentialModel.get_model_path(
            aggregate_all,
            arm_dominance,
            assets_path,
            emg_mode,
            n_samples,
            user,
        )
        model.save(model_path.absolute())
        logger.info(f"new model saved at {model_path.absolute()}")

        return model

    @classmethod
    def get_model_path(
        cls,
        aggregate_all: bool,
        arm_dominance: str,
        assets_path: PurePath,
        emg_mode: EMGMode,
        n_samples: int,
        user: str = "",
    ):
        if aggregate_all:
            mode = "agg"
        else:
            mode = emg_mode.name.lower()
        if user != "":
            return assets_path / f"keras-{arm_dominance}-{mode}-{n_samples}-samples-{user}-model"
        return assets_path / f"keras-{arm_dominance}-{mode}-{n_samples}-samples-model"

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
        aggregate_all: bool,
        arm_dominance: str,
        assets_path: PurePath,
        emg_mode: EMGMode,
        knn_k: int,
        knn_metric: str,
        n_samples: int,
        user: str = "",
    ):
        super().__init__('knn', aggregate_all, arm_dominance, emg_mode, n_samples, user)
        # check if the model exists
        model_path = KNNClassifier.get_model_path(
            aggregate_all,
            arm_dominance,
            assets_path,
            emg_mode,
            knn_k,
            knn_metric,
            n_samples,
            user,
        )

        if not model_path.exists():
            logger.error(f"model: {model_path.absolute()} not found")
            exit(1)

        self.model = joblib.load(model_path.absolute())

    @classmethod
    def fit(
        cls,
        x_train: pd.DataFrame,
        x_test: pd.Series,
        y_train: pd.DataFrame,
        y_test: pd.Series,
        aggregate_all: bool,
        arm_dominance: str,
        assets_path: PurePath,
        emg_mode: EMGMode,
        knn_k: int,
        knn_algorithm: str,
        knn_metric: str,
        n_samples: int,
        user: str = "",
    ):
        """
        fit saves the model in assets_path
        """
        model = KNeighborsClassifier(n_neighbors=knn_k, algorithm=knn_algorithm, metric=knn_metric)
        model.fit(x_train, np.ravel(y_train))

        # save the classifier with joblib
        model_path = KNNClassifier.get_model_path(
            aggregate_all,
            arm_dominance,
            assets_path,
            emg_mode,
            knn_k,
            knn_metric,
            n_samples,
            user,
        )
        joblib.dump(model, model_path.absolute(), protocol=2)
        logger.info(f"new model saved at {model_path.absolute()}")

        return model

    @classmethod
    def get_model_path(
        cls,
        aggregate_all: bool,
        arm_dominance: str,
        assets_path: PurePath,
        emg_mode: EMGMode,
        knn_k: int,
        knn_metric: str,
        n_samples: int,
        user: str = "",
    ):
        if aggregate_all:
            mode = "agg"
        else:
            mode = emg_mode.name.lower()
        if user != "":
            return (
                assets_path
                / f"knn-{knn_k}-{knn_metric}-{arm_dominance}-{mode}-{n_samples}-samples-{user}-model.pkl"  # noqa: E501
            )
        return assets_path / f"knn-{knn_k}-{knn_metric}-{arm_dominance}-{mode}-{n_samples}-samples-model.pkl"

    def predict(self, queue: list):
        # feat = np.array(queue).reshape(1, -1)
        df = pd.DataFrame(queue, columns=self.data_columns)
        feat = df.groupby(df.index // self.n_samples, group_keys=True).agg(['mean', 'std']).iloc[0].to_numpy()
        pred = self.model.predict(feat.reshape(1, -1))[0]
        return Gesture.Enum(pred)


class SVMClassifier(GestureModel):
    def __init__(
        self,
        aggregate_all: bool,
        arm_dominance: str,
        assets_path: PurePath,
        emg_mode: EMGMode,
        n_samples: int,
        svm_c: float,
        svm_degree: int,
        svm_gamma: str,
        svm_kernel: str,
        user: str = "",
    ):
        super().__init__('svm', aggregate_all, arm_dominance, emg_mode, n_samples, user)
        # check if the model exists
        model_path = SVMClassifier.get_model_path(
            aggregate_all,
            arm_dominance,
            assets_path,
            emg_mode,
            n_samples,
            svm_c,
            svm_degree,
            svm_gamma,
            svm_kernel,
            user,
        )
        if not model_path.exists():
            logger.error(f"model: {model_path.absolute()} not found")
            exit(1)

        self.model = joblib.load(model_path.absolute())

    @classmethod
    def fit(
        cls,
        x_train: pd.DataFrame,
        x_test: pd.Series,
        y_train: pd.DataFrame,
        y_test: pd.Series,
        aggregate_all: bool,
        arm_dominance: str,
        assets_path: PurePath,
        emg_mode: EMGMode,
        n_samples: int,
        svm_c: float,
        svm_degree: int,
        svm_gamma: str,
        svm_kernel: str,
        user: str = "",
    ):
        """
        fit saves the model in assets_path
        """
        if svm_kernel == 'poly':
            model = make_pipeline(StandardScaler(), SVC(C=svm_c, kernel=svm_kernel, degree=svm_degree, gamma=svm_gamma))
        elif svm_kernel == 'linear':
            model = make_pipeline(StandardScaler(), SVC(C=svm_c, kernel=svm_kernel))
        else:
            model = make_pipeline(StandardScaler(), SVC(C=svm_c, kernel=svm_kernel, gamma=svm_gamma))

        model.fit(x_train, np.ravel(y_train))

        # save the classifier with joblib
        model_path = SVMClassifier.get_model_path(
            aggregate_all,
            arm_dominance,
            assets_path,
            emg_mode,
            n_samples,
            svm_c,
            svm_degree,
            svm_gamma,
            svm_kernel,
            user,
        )
        joblib.dump(model, model_path.absolute(), protocol=2)
        logger.info(f"new model saved at {model_path.absolute()}")

        return model

    @classmethod
    def get_model_path(
        cls,
        aggregate_all: bool,
        arm_dominance: str,
        assets_path: PurePath,
        emg_mode: EMGMode,
        n_samples: int,
        svm_c: float,
        svm_degree: int,
        svm_gamma: str,
        svm_kernel: str,
        user: str = "",
    ):
        if aggregate_all:
            mode = "agg"
        else:
            mode = emg_mode.name.lower()
        if user != "":
            suffix = f"-{user}-model.pkl"
        else:
            suffix = "-model.pkl"
        if svm_kernel == 'poly':
            model_path = assets_path / (
                f"svm-{svm_c}-{svm_kernel}-{svm_degree}-{svm_gamma}-{arm_dominance}-{mode}-{n_samples}-samples"  # noqa: E501
                + suffix
            )
        elif svm_kernel == 'linear':
            model_path = assets_path / (
                f"svm-{svm_c}-{svm_kernel}-{arm_dominance}-{mode}-{n_samples}-samples" + suffix  # noqa: E501
            )
        else:
            model_path = assets_path / (
                f"svm-{svm_c}-{svm_kernel}-{svm_gamma}-{arm_dominance}-{mode}-{n_samples}-samples"  # noqa: E501
                + suffix
            )
        return model_path

    def predict(self, queue: list):
        # feat = np.array(queue).reshape(1, -1)
        df = pd.DataFrame(queue, columns=self.data_columns)
        feat = df.groupby(df.index // self.n_samples, group_keys=True).agg(['mean', 'std']).iloc[0].to_numpy()
        pred = self.model.predict(feat.reshape(1, -1))[0]
        return Gesture.Enum(pred)
