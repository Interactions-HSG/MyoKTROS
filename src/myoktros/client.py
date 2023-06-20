import logging
from collections import deque

from myo import MyoClient
from myo.types import (
    ClassifierEvent,
    ClassifierEventType,
    EMGData,
    FVData,
    MotionEvent,
    MotionEventType,
    Pose,
)
from transitions.core import MachineError

from .gesture import Gesture, GestureClassifierLegacy, GestureClassifierModel

logger = logging.getLogger(__name__)


class KerasClient(MyoClient):
    def __init__(self):
        super().__init__()
        logger.info("loading the keras gesture model...")
        self.model = GestureClassifierModel()
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
            elif all(pred == Gesture.RELAX for pred in self.queue):
                logger.info(Gesture.RELAX)
            elif all(pred == Gesture.GRAB for pred in self.queue):
                logger.info(Gesture.GRAB)
                await self.robot.grabbed()
            elif all(pred == Gesture.STRETCH_FINGER for pred in self.queue):
                logger.info(Gesture.STRETCH_FINGER)
                await self.robot.confirm()
            elif all(pred == Gesture.EXTENSION for pred in self.queue):
                logger.info(Gesture.EXTENSION)
                await self.robot.play_once()
            elif all(pred == Gesture.FLEXION for pred in self.queue):
                logger.info(Gesture.EXTENSION)
            elif all(pred == Gesture.HORN for pred in self.queue):
                logger.info(Gesture.HORN)
            elif all(pred == Gesture.GUN for pred in self.queue):
                logger.info(Gesture.GUN)
                # await self.robot.delete()
            else:
                return
        except MachineError:
            pass
        self.last_gesture = pred
        self.queue = deque([], self.queue_max_length)

    async def on_motion_event(self, me: MotionEvent):
        if me.t == MotionEventType.TAP:
            logger.info(f"{MotionEventType.TAP}: {me.tap_count} {me.tap_direction}")

    def set_queue_length(self, n):
        self.queue_max_length = n
        self.queue = deque([], n)

    def set_robot(self, robot):
        self.robot = robot


class LegacyClient(MyoClient):
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

    def set_gesture_classifier_legacy(self, legacy_n_periods, legacy_n_samples):
        self.legacy_n_periods = legacy_n_periods
        self.legacy_n_samples = legacy_n_samples
        logger.info("loading the legacy gesture classifier...")
        self.model = GestureClassifierLegacy(legacy_n_periods, legacy_n_samples)

    def set_robot(self, robot):
        self.robot = robot
