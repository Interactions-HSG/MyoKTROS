import argparse
import asyncio
import logging
import time
from collections import deque
from pathlib import Path, PurePath

from myo import AggregatedData, MyoClient
from myo.types import (
    ClassifierEventType,
    ClassifierMode,
    EMGMode,
    IMUMode,
    MotionEventType,
    VibrationType,
)
from transitions.core import MachineError

from .gesture import Gesture, KerasSequentialModel, KNNClassifier, SVMClassifier

logger = logging.getLogger(__name__)


class GestureClient(MyoClient):
    def __init__(self, aggregate_all=True, aggregate_emg=True):
        super().__init__(aggregate_all=aggregate_all, aggregate_emg=aggregate_emg)
        # the following instance attributes need to be set by configure()
        self.arm_dominance = None
        self.last_gesture = None
        self.gesture_queue = None
        self.model = None
        self.n_samples = None
        self.agg_queue = None
        self.data_queue = None
        self.trigger_map = {}

    async def configure(self, args: argparse.Namespace):
        # set the initial attributes
        self.aggregate_all = args.aggregate_all
        self.arm_dominance = args.arm_dominance
        self.emg_mode = args.emg_mode
        self.gesture_queue = deque([Gesture.Enum(0)] * args.gesture_queue_length, args.gesture_queue_length)
        self.last_gesture = Gesture.Enum(0)
        self.n_samples = args.n_samples
        self.data_queue = deque([], self.n_samples)

        self.user = args.user

        # load the model
        assets_path = Path(__file__).parent.parent.parent / "assets"
        if args.model_type == 'keras':
            self.model = KerasSequentialModel(self.arm_dominance, assets_path, self.emg_mode, args.n_samples, self.user)
        elif args.model_type == 'knn':
            self.model = KNNClassifier(
                self.arm_dominance,
                assets_path,
                self.emg_mode,
                args.knn_k,
                args.knn_metric,
                args.n_samples,
                args.user,
            )
        elif args.model_type == 'svm':
            self.model = SVMClassifier(
                self.arm_dominance,
                assets_path,
                self.emg_mode,
                args.n_samples,
                args.svm_c,
                args.svm_degree,
                args.svm_gamma,
                args.svm_kernel,
                args.user,
            )
        else:
            logger.error(f"invalid model: {args.model_type}")
            exit(1)

        # setup the MyoClient
        if self.aggregate_all:
            await self.setup(
                classifier_mode=ClassifierMode.DISABLED,
                emg_mode=EMGMode.SEND_FILT,
                imu_mode=IMUMode.SEND_DATA,
            )
        else:
            await self.setup(
                classifier_mode=ClassifierMode.ENABLED,  # get ClassifierEvent
                emg_mode=self.emg_mode,  # configure the EMGMode
                imu_mode=IMUMode.SEND_ALL,  # get everything about IMU
            )

    async def on_classifier_event(self, ce):
        # TODO: do something when the arm is unsynced?
        if ce.t == ClassifierEventType.POSE:
            # TODO: verify ClassifierEvent triggers
            try:
                trigger = self.trigger_map[ce.pose]
                await trigger()
            except KeyError:  # no registration
                return
            except MachineError:  # invalid transition
                return
            except TypeError:  # None
                return
        else:
            # logger.info(ce.t)
            pass

    async def on_emg(self, data):
        # wait until the queue to fill up
        self.data_queue.append(data)
        if len(self.data_queue) < self.n_samples:
            return

        # predict the gesture
        pred = self.model.predict(self.data_queue)

        # invoke the on_gesture
        await self.on_gesture(pred)

        # clear the queue
        self.data_queue = deque([], self.n_samples)

    async def on_emg_data_aggregated(self, emg):
        await self.on_emg(emg)

    async def on_fv_data(self, fvd):
        await self.on_emg(fvd.fv)

    async def on_gesture(self, gesture: Gesture.Enum):
        # inject g into FIFO
        self.gesture_queue.append(gesture)
        # logger.info(self.gesture_queue)

        if not all(g == gesture for g in self.gesture_queue):
            return

        # skip if the same gesture
        if self.last_gesture and gesture == self.last_gesture:
            return

        # save this gesture
        self.last_gesture = gesture
        logger.info(gesture)

        # invoke the trigger
        try:
            trigger = self.trigger_map[gesture]
            await trigger()
        except KeyError:  # no registration
            return
        except MachineError:  # invalid transition
            return
        except TypeError:  # None
            return

    async def on_imu_data(self, imu):
        # TODO: something can be done with IMU as well
        pass

    async def on_motion_event(self, me):
        if me.t == MotionEventType.TAP:
            # logger.info(f"{MotionEventType.TAP}: {me.tap_count} {me.tap_direction}")
            pass

    def set_robot(self, robot):
        self.robot = robot


class RecorderClient(MyoClient):
    def __init__(self, aggregate_all=True, aggregate_emg=True):
        super().__init__(aggregate_all=aggregate_all, aggregate_emg=aggregate_emg)
        # used by callbacks
        self.buf = []
        self.emg_buf = []
        self.imu_buf = []
        self.gestures = []
        self._buf_lock = asyncio.Lock()

    async def on_aggregated_data(self, ad: AggregatedData):
        line = f"{time.time()},{ad}"
        async with self._buf_lock:
            self.buf.append(line)

    async def on_emg_data_aggregated(self, emg):
        line = ",".join(map(str, (time.time(),) + emg))
        async with self._buf_lock:
            self.emg_buf.append(line)

    async def on_fv_data(self, fvd):
        line = ",".join(map(str, (time.time(),) + fvd.fv + (fvd.mask,)))
        async with self._buf_lock:
            self.emg_buf.append(line)

    async def on_imu_data(self, imu):
        line = ",".join(map(str, (time.time(),) + imu))
        async with self._buf_lock:
            self.imu_buf.append(line)

    async def record(self, args: argparse.Namespace):
        self.gestures = [g for g in Gesture.Enum]
        if args.gesture != "all" and args.gesture != "":
            gn = args.gesture.upper()
            try:
                self.gestures = [
                    Gesture.Enum[gn],
                ]
            except KeyError:
                logger.error(f"{gn} is not a valid gesture")
                exit(1)

        # setup the MyoClient
        if self.aggregate_all:
            # get the emg + IMU data streams (accel, gyro, and orientation)
            await self.setup(
                classifier_mode=ClassifierMode.DISABLED,
                emg_mode=EMGMode.SEND_FILT,
                imu_mode=IMUMode.SEND_DATA,
            )
        else:
            await self.setup(
                classifier_mode=ClassifierMode.ENABLED,  # get ClassifierEvent
                emg_mode=self.emg_mode,  # configure the EMGMode
                imu_mode=IMUMode.SEND_ALL,  # get everything about IMU
            )

        # prepare the datapath
        data_path = Path(args.data)
        if not data_path.exists():
            data_path.mkdir()

        # create a new record directory with the current datetime
        out_path = data_path / (time.strftime("%Y%m%d%H%M%S") + f"-{args.user}")
        if out_path.exists():
            # this should (almost) never occurs, but just in case
            logger.info(f"{out_path.absolute()} already exists; backing up")
            out_path.rename(data_path / out_path.name + ".bak")
        out_path.mkdir()

        for gesture in self.gestures:
            async with self._buf_lock:
                self.buf = []
                self.emg_buf = []
                self.imu_buf = []

            # start
            await start_countdown(
                self.vibrate,
                gesture,
                args.arm_dominance,
                args.duration,
                "recording",
            )
            await self.start()

            # record
            await wait_countdown(args.duration)

            # stop
            await self.stop()

            # write emg to file
            if self.aggregate_all:
                p = out_path / f"{args.arm_dominance}-agg-{gesture.name.lower()}.csv"
                with open(p.absolute(), "w") as f:
                    print(
                        "timestamp,fv0,fv1,fv2,fv3,fv4,fv5,fv6,fv7,quat_w,quat_x,quat_y,quat_z,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z",  # noqa: E501
                        file=f,
                    )
                    async with self._buf_lock:
                        for line in self.buf:
                            print(line, file=f)
                logger.info(f"saved the aggregated data recording to {p.absolute()}")
            else:
                p = self.setup_emg_output(
                    out_path,
                    args.arm_dominance,
                    EMGMode(args.emg_mode),
                    gesture,
                )
                with open(p.absolute(), "a") as f:
                    async with self._buf_lock:
                        for line in self.emg_buf:
                            print(line, file=f)
                logger.info(f"saved the recorded emg data to {p.absolute()}")
                # write imu to file
                p = out_path / f"{args.arm_dominance}-imu-{gesture.name.lower()}.csv"
                with open(p.absolute(), "w") as f:
                    print("timestamp,quat_w,quat_x,quat_y,quat_z,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z", file=f)
                    async with self._buf_lock:
                        for line in self.imu_buf:
                            print(line, file=f)
                logger.info(f"saved the recorded imu data to {p.absolute()}")

    def setup_emg_output(
        self,
        out_path: PurePath,
        arm_dominance: str,
        emg_mode: EMGMode,
        g: Gesture.Enum,
    ) -> PurePath:
        # build the new data filename
        p = out_path / f"{arm_dominance}-{emg_mode.name.lower()}-{g.name.lower()}.csv"
        with open(p.absolute(), "w") as f:
            if emg_mode == EMGMode.SEND_FILT:
                print("timestamp,fv0,fv1,fv2,fv3,fv4,fv5,fv6,fv7,mask", file=f)
            else:
                print(
                    "timestamp,emg0,emg1,emg2,emg3,emg4,emg5,emg6,emg7",  # noqa
                    file=f,
                )

        return p


class EvaluaterClient(GestureClient):
    def __init__(self, aggregate_all=True, aggregate_emg=True):
        super().__init__(aggregate_all=True, aggregate_emg=True)
        self.last_gesture = Gesture.Enum(0)

    async def on_gesture(self, gesture: Gesture.Enum):
        # inject g into FIFO
        self.gesture_queue.append(gesture)
        logger.info(self.gesture_queue)

        # take the most frequent gestures from the immediate gesture_queue
        # gesture = max(set(self.gesture_queue), key=self.gesture_queue.count)
        if not all(g == gesture for g in self.gesture_queue):
            return

        # skip if the same gesture
        if self.last_gesture and gesture == self.last_gesture:
            return

        # save this gesture
        self.last_gesture = gesture
        logger.info(gesture)

    # async def on_emg(self, data):
    #     self.buf.append(data)


async def start_countdown(vibrate, gesture, arm_dominance, duration, action=""):
    # notify the user and start
    logger.info("")
    logger.info(f"start {action}")
    logger.info("")
    logger.info(gesture.name)
    logger.info("")
    logger.info(f"- on the {arm_dominance} arm")
    logger.info(f"- for {duration} seconds")
    logger.info("")

    # count 5
    for i in range(5, 0, -1):
        logger.info(f"starting in {i}")
        await vibrate(VibrationType.SHORT)
        await asyncio.sleep(1)

    logger.info("go!")
    logger.info("")
    await vibrate(VibrationType.MEDIUM)


async def wait_countdown(duration, count=5):
    for i in range(duration, 0, -1):
        await asyncio.sleep(1)
        if i % count == 0:
            logger.info(f"{i} seconds left")
        else:
            logger.info("|")
