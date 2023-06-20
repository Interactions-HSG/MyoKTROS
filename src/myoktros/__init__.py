# -*- coding: utf-8 -*-
import argparse
import asyncio
import logging

from myo import MyoClient, EMGData, EMGMode, FVData
from transitions.core import MachineError

from .gesture import Gesture, GestureClassifierLegacy, GestureClassifierModel
from .robot import Robot

logger = logging.getLogger(__name__)


class EmptyRobot(Robot):
    async def disable_free_drive(self):
        await asyncio.sleep(0.1)

    async def enable_free_drive(self):
        await asyncio.sleep(0.1)

    async def get_pose(self):
        await asyncio.sleep(0.1)
        return 0

    async def move(self):
        await asyncio.sleep(1)

    async def speak(self, text):
        if text != "":
            await asyncio.create_subprocess_exec("say", text)


class KerasClient(MyoClient):
    def __init__(self):
        super().__init__()
        logger.info("loading the keras gesture model...")
        self.model = GestureClassifierModel()
        self.robot = None

    async def on_fv_data(self, fvd: FVData):
        pred = self.model.predict(fvd)
        try:
            if pred == Gesture.RELAX:
                pass
            elif pred == Gesture.GRAB:
                await self.robot.grabbed()
            elif pred == Gesture.STRETCH_FINGER:
                await self.robot.confirm()
            elif pred == Gesture.BEND_WRIST:
                await self.robot.cancel()
            elif pred == Gesture.FLEXION:
                await self.robot.delete()
        except MachineError:
            pass

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
                elif pred == Gesture.BEND_WRIST:
                    await self.robot.cancel()
                elif pred == Gesture.FLEXION:
                    await self.robot.delete()
            except MachineError:
                pass

    def set_gesture_classifier_legacy(self, legacy_n_periods, legacy_n_samples):
        self.legacy_n_periods = legacy_n_periods
        self.legacy_n_samples = legacy_n_samples
        logger.info("loading the legacy gesture classifier...")
        self.model = GestureClassifierLegacy(legacy_n_periods, legacy_n_samples)

    def set_robot(self, robot):
        self.robot = robot


async def main(args: argparse.Namespace):
    mc = None
    if args.mode == "keras":
        while mc is None:
            mc = await KerasClient.with_device(args.mac)
        await mc.setup(emg_mode=EMGMode.SEND_FILT)
        await mc.start()

    elif args.mode == "legacy":
        while mc is None:
            mc = await LegacyClient.with_device(args.mac)
        mc.set_gesture_classifier_legacy(args.legacy_n_periods, args.legacy_n_samples)
        await mc.setup(emg_mode=EMGMode.SEND_EMG)
        await mc.start()

    else:
        exit(0)

    robot = EmptyRobot()
    await robot.setup()
    mc.set_robot(robot)

    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.exceptions.CancelledError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("closing the session...")
        await mc.stop()
        await mc.sleep()


def entrypoint():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Myo EMG-based KT system for ROS",
    )
    parser.add_argument(
        "--mode",
        choices=["keras", "legacy"],
        default="keras",
        help="mode to select",
    )
    parser.add_argument(
        "-a",
        "--address",
        help="the IP address for the ROS server",
        default="127.0.0.1",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="sets the log level to debug",
    )
    parser.add_argument(
        "-m",
        "--mac",
        help="specify the mac address for Myo",
    )
    parser.add_argument(
        "--legacy_n_samples",
        help="number of samples for the legacy classifier",
        default=3,
    )
    parser.add_argument(
        "--legacy_n_periods",
        help="number of sampling periods for the legacy classifier",
        default=10,
    )
    parser.add_argument("-p", "--port", help="the port for the ROS server", default=8765)

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )
    asyncio.run(main(args))
