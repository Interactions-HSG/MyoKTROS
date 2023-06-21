import asyncio
import logging
import time
from collections import deque
from pathlib import Path, PurePath

from myo import MyoClient
from myo.types import (
    ClassifierEvent,
    ClassifierEventType,
    EMGData,
    EMGMode,
    FVData,
    MotionEvent,
    MotionEventType,
    Pose,
    VibrationType,
)
from transitions.core import MachineError

from .gesture import Gesture, KerasSequentialModel, KNNClassifier

logger = logging.getLogger(__name__)


class KerasClient(MyoClient):
    def __init__(self):
        super().__init__()
        logger.info("loading the keras gesture model...")
        self.model = KerasSequentialModel()
        self.robot = None
        self.queue = deque([0] * 10, 10)
        self.last_gesture = None
        self.last_pose = None

    async def on_classifier_event(self, ce: ClassifierEvent):
        logger.info(ce.t)
        # TODO: wait for the arm sync
        if ce.t == ClassifierEventType.POSE:
            logger.info(ce.pose)
            self.last_pose = ce.pose
            try:
                if ce.pose == Pose.REST:
                    pass
                elif ce.pose == Pose.FIST:
                    await self.robot.grabbed()
                elif ce.pose == Pose.WAVE_IN:
                    # await self.robot.previous()
                    pass
                elif ce.pose == Pose.WAVE_OUT:
                    # await self.robot.next()
                    pass
                elif ce.pose == Pose.FINGERS_SPREAD:
                    pass
                elif ce.pose == Pose.DOUBLE_TAP:
                    await self.robot.cancel()
            except MachineError:
                pass

    async def on_fv_data(self, fvd: FVData):
        pred = self.model.predict(fvd)
        self.queue.append(pred)
        if len(self.queue) < self.queue_max_length:
            return
        try:
            if pred == self.last_gesture:
                pass
            gesture = None
            for g in Gesture:
                if all(pred == g for pred in self.queue):
                    gesture = pred
                    break
            if gesture is None:  # no match
                return
        except MachineError:
            pass
        # invoke trigger
        logger.info(gesture)
        trigger = self.robot.trigger_map[gesture]
        if trigger:
            await trigger()
        self.last_gesture = gesture
        self.queue = deque([], self.queue_max_length)

    async def on_motion_event(self, me: MotionEvent):
        if me.t == MotionEventType.TAP:
            logger.info(f"{MotionEventType.TAP}: {me.tap_count} {me.tap_direction}")

    def set_queue_length(self, n):
        self.queue_max_length = n
        self.queue = deque([], n)

    def set_robot(self, robot):
        self.robot = robot


class KNNClient(MyoClient):
    def __init__(self):
        super().__init__()
        self.model = None
        self.robot = None
        self.queue = []
        self.n_periods = 3
        self.n_samples = 10

    async def on_emg_data(self, data: EMGData):
        self.queue.append(data)
        # wait until the queue to fill up
        if len(self.queue) == self.n_periods * self.n_samples:
            pred = self.model.predict(self.queue)
            self.queue = []
            try:
                if pred == Gesture.RELAX:
                    pass
                elif pred == Gesture.GRAB:
                    await self.robot.grabbed()
                elif pred == Gesture.STRETCH_FINGER:
                    await self.robot.confirm()
                elif pred == Gesture.EXTENSION:
                    # await self.robot.cancel()
                    pass
                elif pred == Gesture.FLEXION:
                    # await self.robot.delete()
                    pass
            except MachineError:
                pass

    def set_knn_classifier(self, n_periods, n_samples):
        self.n_periods = n_periods
        self.n_samples = n_samples
        logger.info("loading the legacy knn classifier...")
        self.model = KNNClassifier(n_periods, n_samples)

    def set_robot(self, robot):
        self.robot = robot


class RecorderClient(MyoClient):
    def __init__(self):
        super().__init__()
        self.buf = []
        self.emg_mode = EMGMode.NONE
        self.gesture = None

    async def on_emg_data(self, emg: EMGData):
        line = ",".join(map(str, emg + (self.gesture.value,)))
        self.buf.append(line)

    async def on_fv_data(self, fvd: FVData):
        line = ",".join(map(str, (time.time(),) + fvd.fv + (fvd.mask, self.gesture.value)))
        self.buf.append(line)

    async def record(self, em: EMGMode, seconds: int):
        self.emg_mode = em
        for gesture in Gesture:
            self.buf = []
            self.gesture = gesture

            # notify the user and start
            logger.info("")
            logger.info("start recording")
            logger.info("")
            logger.info(gesture.name)
            logger.info("")
            logger.info(f"with {self.emg_mode.name} for {seconds} seconds")

            # count 5
            for i in range(5, 0, -1):
                logger.info(f"starting in {i}")
                await self.vibrate(VibrationType.SHORT)
                await asyncio.sleep(1)

            logger.info("go!")
            await self.vibrate(VibrationType.MEDIUM)
            await self.start()

            # record
            for i in range(seconds, 0, -1):
                await asyncio.sleep(1)
                if i % 5 == 0:
                    logger.info(f"{i} seconds left")
                else:
                    logger.info(".")

            # stop
            await self.stop()

            # write to file
            outpath = self.setup_output(gesture, self.emg_mode)
            with open(outpath.absolute(), "a") as f:
                for line in self.buf:
                    print(line, file=f)
            logger.info(f"saved the recorded data to {outpath.absolute()}")

    def setup_output(self, g: Gesture, em: EMGMode) -> PurePath:
        assets = Path.cwd() / "assets"
        if not assets.exists():
            assets.mkdir()
        datadir = assets / "keras_gesture_data"
        if not datadir.exists():
            datadir.mkdir()
        now = time.strftime("%Y%m%d%H%M%S")
        p = datadir / f"{em.name}-{g.name}-{now}.csv"
        with open(p.absolute(), "w") as f:
            if em == EMGMode.SEND_FILT:
                print("timestamp,fv0,fv1,fv2,fv3,fv4,fv5,fv6,fv7,mask,gesture", file=f)
            else:
                print("emg0,emg1,emg2,emg3,emg4,emg5,emg6,emg7,gesture", file=f)

        return p
