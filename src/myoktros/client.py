import argparse
import asyncio
import logging
import time
from collections import deque
from pathlib import Path, PurePath

from myo import MyoClient
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
    def __init__(self):
        super().__init__()
        # always enable EMGData aggregation
        self.aggregate_emg = True
        # the following instance attributes need to be set by configure()
        self.arm_dominance = None
        self.last_gesture = None
        self.emg_mode = None
        self.model = None
        self.n_samples = None
        self.queue = None
        self.trigger_map = {}

    async def configure(self, args: argparse.Namespace):
        # set the initial attributes
        self.arm_dominance = args.arm_dominance
        self.emg_mode = EMGMode(args.emg_mode)
        self.last_gesture = Gesture.Enum(0)
        self.n_samples = args.n_samples
        self.queue = deque([], self.n_samples)

        # load the model
        assets_path = Path(__file__).parent.parent.parent / "assets"
        if args.model_type == 'keras':
            self.model = KerasSequentialModel(self.arm_dominance, assets_path, self.emg_mode, args.n_samples)
        elif args.model_type == 'knn':
            self.model = KNNClassifier(
                self.arm_dominance,
                assets_path,
                self.emg_mode,
                args.knn_k,
                args.knn_metric,
                args.n_samples,
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
            )
        else:
            logger.error(f"invalid model: {args.model_type}")
            exit(1)

        # setup the MyoClient
        await self.setup(
            classifier_mode=ClassifierMode.ENABLED,  # get ClassifierEvent
            emg_mode=self.emg_mode,  # configure the EMGMode
            imu_mode=IMUMode.SEND_ALL,  # get everything about IMU
        )

    async def on_classifier_event(self, ce):
        # TODO: do something when the arm is unsynced?
        if ce.t == ClassifierEventType.POSE:
            # TODO: verify ClassifierEvent triggers
            trigger = self.trigger_map[ce.pose]
            if trigger:
                try:
                    await trigger()
                except MachineError:
                    pass
        else:
            # logger.info(ce.t)
            pass

    async def on_emg(self, data):
        # wait until the queue to fill up
        self.queue.append(data)
        if len(self.queue) < self.n_samples:
            return

        # predict the gesture
        pred = self.model.predict(self.queue)

        # invoke the on_gesture
        await self.on_gesture(pred)

        # clear the queue
        self.queue = deque([], self.n_samples)

    async def on_emg_data_aggregated(self, emg):
        await self.on_emg(emg)

    async def on_fv_data(self, fvd):
        await self.on_emg(fvd.fv)

    async def on_gesture(self, gesture: Gesture.Enum):
        # TODO: verify gesture triggers
        # skip if the same gesture
        if self.last_gesture and gesture == self.last_gesture:
            return

        # save the this gesture
        self.last_gesture = gesture

        # invoke the trigger
        logger.info(gesture)
        trigger = self.trigger_map[gesture]
        if trigger:
            try:
                await trigger()
            except MachineError:
                pass

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
    def __init__(self):
        super().__init__()
        # always enable EMGData aggregation
        self.aggregate_emg = True
        # used by callbacks
        self.buf = []
        self.gestures = []

    async def on_emg_data_aggregated(self, emg):
        line = ",".join(map(str, (time.time(),) + emg))
        self.buf.append(line)

    async def on_fv_data(self, fvd):
        line = ",".join(map(str, (time.time(),) + fvd.fv + (fvd.mask,)))
        self.buf.append(line)

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

            # setup myo
        arm_dominance = args.arm_dominance
        data_path = Path(args.data)
        duration = args.duration
        emg_mode = EMGMode(args.emg_mode)
        await self.setup(emg_mode=emg_mode)

        # prepare the datapath
        if not data_path.exists():
            data_path.mkdir()

        # create a new record directory with the current datetime
        out_path = data_path / time.strftime("%Y%m%d%H%M%S")
        if out_path.exists():
            logger.info(f"{out_path.absolute()} already exists; backing up")
            out_path.rename(data_path / out_path.name + ".bak")
        out_path.mkdir()

        for gesture in self.gestures:
            self.buf = []

            # start
            # TODO: perhaps wait for the user's DOUBLE_TAP?
            await start_countdown(self.vibrate, gesture, arm_dominance, emg_mode, duration, "recording")
            await self.start()

            # record
            await wait_countdown(duration)

            # stop
            await self.stop()

            # write to file
            p = self.setup_output(out_path, arm_dominance, emg_mode, gesture)
            with open(p.absolute(), "a") as f:
                for line in self.buf:
                    print(line, file=f)
            logger.info(f"saved the recorded data to {p.absolute()}")

    def setup_output(self, out_path: PurePath, arm_dominance: str, emg_mode: EMGMode, g: Gesture.Enum) -> PurePath:
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
    def __init__(self):
        super().__init__()
        self.last_gesture = Gesture.Enum(0)

    async def on_gesture(self, g: Gesture.Enum):
        if self.last_gesture != g:
            self.last_gesture = g
            logger.info(g)

    # async def on_emg(self, data):
    #     self.buf.append(data)


async def start_countdown(vibrate, gesture, arm_dominance, emg_mode, duration, action=""):
    # notify the user and start
    logger.info("")
    logger.info(f"start {action}")
    logger.info("")
    logger.info(gesture.name)
    logger.info("")
    logger.info(f"- on the {arm_dominance} arm")
    logger.info(f"- with {emg_mode.name.lower()}")
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
