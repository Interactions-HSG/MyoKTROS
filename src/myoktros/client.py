import argparse
import asyncio
import logging
import pickle
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
    Pose,
    VibrationType,
)
from transitions.core import MachineError

from .gesture import Gesture, KerasSequentialModel, KNNClassifier

logger = logging.getLogger(__name__)


DEFAULT_TRIGGER_MAP = {}
for g in Gesture:
    DEFAULT_TRIGGER_MAP[g] = None
for p in Pose:
    DEFAULT_TRIGGER_MAP[p] = None


class GestureClient(MyoClient):
    def __init__(self):
        super().__init__()
        # the following instance attributes need to be set by configure()
        self.last_gesture = None
        self.model = None
        self.n_samples = None
        self.n_periods = None
        self.queue = None
        self.trigger_map = DEFAULT_TRIGGER_MAP

    async def configure(self, args: argparse.Namespace):
        # check if the model exists
        assets = Path(__file__).parent.parent.parent / "assets"
        ext = ".pkl" if args.model == 'knn' else ""
        em = EMGMode(args.emg_mode)
        model_path = assets / f"{args.model}-{em.name}-{args.n_samples}-samples-model{ext}"
        if not model_path.exists():
            logger.error(f"model: {model_path.absolute()} not found")
            exit(1)

        # load the model
        if args.model == 'keras':
            self.model = KerasSequentialModel(em, args.n_periods, args.n_samples, model_path)
        elif args.model == 'knn':
            self.model = KNNClassifier(em, args.n_periods, args.n_samples, model_path)
        else:
            logger.error(f"invalid model: {args.model}")
            exit(1)

        # setup the MyoClient
        em = EMGMode(args.emg_mode)
        await self.setup(
            classifier_mode=ClassifierMode.ENABLED,  # get ClassifierEvent
            emg_mode=EMGMode(args.emg_mode),  # configure the EMGMode
            imu_mode=IMUMode.SEND_ALL,  # get everything about IMU
        )
        self.aggregate_emg = True  # always enable EMGData aggregation

        # set the initial attributes
        self.last_gesture = Gesture.RELAX
        self.n_samples = args.n_samples
        self.n_periods = args.n_periods
        self.queue = deque([], self.n_periods * self.n_samples)

    async def on_classifier_event(self, ce):
        logger.info(ce.t)
        # TODO: do something when the arm is unsynced?
        if ce.t == ClassifierEventType.POSE:
            trigger = self.trigger_map[ce.pose]
            if trigger:
                try:
                    await trigger()
                except MachineError:
                    pass

    async def on_emg(self, data):
        # wait until the queue to fill up
        self.queue.append(data)
        if len(self.queue) < self.n_periods * self.n_samples:
            return

        # predict the gesture
        pred = self.model.predict(self.queue)

        # invoke the on_gesture
        await self.on_gesture(pred)

        # clear the queue
        self.queue = deque([], self.n_periods * self.n_samples)

    async def on_emg_data_aggregated(self, emg):
        await self.on_emg(emg)

    async def on_fv_data(self, fvd):
        await self.on_emg(fvd.fv)

    async def on_gesture(self, gesture: Gesture):
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
            logger.info(f"{MotionEventType.TAP}: {me.tap_count} {me.tap_direction}")

    def set_robot(self, robot):
        self.robot = robot


class RecorderClient(MyoClient):
    def __init__(self):
        super().__init__()
        self.buf = []
        self.gesture = None

    async def on_emg_data_aggregated(self, emg):
        line = ",".join(map(str, (time.time(),) + emg + (self.gesture.value,)))
        self.buf.append(line)

    async def on_fv_data(self, fvd):
        line = ",".join(map(str, (time.time(),) + fvd.fv + (fvd.mask, self.gesture.value)))
        self.buf.append(line)

    async def record(self, args: argparse.Namespace):
        # setup myo
        em = EMGMode(args.emg_mode)
        await self.setup(emg_mode=em)
        self.aggregate_emg = True  # always enable EMGData aggregation

        # prepare the datapath
        data_path = Path(args.data)
        if not data_path.exists():
            data_path.mkdir()

        # rotate the existing data to backup
        backup_path = data_path / "backup"
        old_data_files = sorted(data_path.glob(f"*-{em.name}-*.csv"))
        if len(old_data_files) > 0:
            if not backup_path.exists():
                backup_path.mkdir()
            for pp in old_data_files:
                logger.info(f"moving the existing data to 'backup': {pp.name}")
                pp.rename(backup_path / pp.name)

        # use the current datetime as the data id
        now = time.strftime("%Y%m%d%H%M%S")

        for gesture in Gesture:
            self.buf = []
            self.gesture = gesture

            # start
            # TODO: perhaps wait for the user's DOUBLE_TAP?
            await start_countdown(self.vibrate, gesture, em, args.duration, "recording")
            await self.start()

            # record
            await wait_countdown(args.duration)

            # stop
            await self.stop()

            # write to file
            out_path = self.setup_output(data_path, now, em, gesture)
            with open(out_path.absolute(), "a") as f:
                for line in self.buf:
                    print(line, file=f)
            logger.info(f"saved the recorded data to {out_path.absolute()}")

    def setup_output(self, data_path: PurePath, now: str, em: EMGMode, g: Gesture) -> PurePath:
        # build the new data filename
        p = data_path / f"{now}-{em.name}-{g.name}.csv"
        with open(p.absolute(), "w") as f:
            if em == EMGMode.SEND_FILT:
                print("timestamp,fv0,fv1,fv2,fv3,fv4,fv5,fv6,fv7,mask,gesture", file=f)
            else:
                print(
                    "timestamp,emg0,emg1,emg2,emg3,emg4,emg5,emg6,emg7,gesture",  # noqa
                    file=f,
                )

        return p


class EvaluaterClient(GestureClient):
    def __init__(self):
        super().__init__()

    async def on_gesture(self, gesture: Gesture):
        self.buf.append(gesture)

    async def evaluate(self, args: argparse.Namespace):
        duration = args.duration
        em = EMGMode(args.emg_mode)
        n_samples = args.n_samples

        results = {}
        for gesture in Gesture:
            self.buf = []
            self.gesture = gesture

            # start
            await start_countdown(self.vibrate, gesture, em, duration, "validating")
            await self.start()

            # record
            await wait_countdown(duration)

            # stop
            await self.stop()

            # save the result
            results[gesture] = self.buf

        # report at the end
        for g, r in results.items():
            acc = r.count(g) / len(r) * 100
            logger.info(f"accuracy for {g.name}: {acc:.2f}%")

        # save the result to a pickle file
        data_path = Path.cwd() / "data"
        now = time.strftime("%Y%m%d%H%M%S")
        p = data_path / f"{args.model}-{em.name}-{n_samples}-samples-evaluation-{now}.pkl"
        with p.open('wb') as f:
            pickle.dump(results, f, protocol=pickle.HIGHEST_PROTOCOL)


async def start_countdown(vibrate, gesture, em, seconds, action=""):
    # notify the user and start
    logger.info("")
    logger.info(f"start {action}")
    logger.info("")
    logger.info(gesture.name)
    logger.info("")
    logger.info(f"with {em.name} for {seconds} seconds")

    # count 5
    for i in range(5, 0, -1):
        logger.info(f"starting in {i}")
        await vibrate(VibrationType.SHORT)
        await asyncio.sleep(1)

    logger.info("go!")
    await vibrate(VibrationType.MEDIUM)


async def wait_countdown(seconds):
    for i in range(seconds, 0, -1):
        await asyncio.sleep(1)
        if i % 5 == 0:
            logger.info(f"{i} seconds left")
        else:
            logger.info("|")
