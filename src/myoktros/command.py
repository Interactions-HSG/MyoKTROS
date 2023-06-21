import argparse
import asyncio
import logging

from myo.types import ClassifierMode, EMGMode, IMUMode, Pose

from .client import KerasClient, KNNClient, RecorderClient, ValidationClient
from .gesture import Gesture, KerasSequentialModel
from .robot import TalkingRobot

logger = logging.getLogger(__name__)


class Command:  # no cov
    @classmethod
    async def keras(cls, args: argparse.Namespace):
        c = None
        while c is None:
            c = await KerasClient.with_device(args.mac)
        c.set_queue_length(args.queue_length)  # 1 gesture/sec
        await c.setup(
            classifier_mode=ClassifierMode.ENABLED,
            emg_mode=EMGMode.SEND_FILT,
            imu_mode=IMUMode.SEND_EVENTS,
        )
        await c.start()

        robot = TalkingRobot()
        c.set_robot(robot)
        await robot.setup()

        robot.trigger_map = {
            Gesture.RELAX: None,
            Gesture.GRAB: robot.grabbed,
            Gesture.STRETCH_FINGER: None,
            Gesture.FLEXION: None,
            Gesture.HORN: robot.play,
            # Gesture.EXTENSION: None,
            # Gesture.GUN: None,
            Pose.DOUBLE_TAP: robot.confirm,
            Pose.FINGERS_SPREAD: robot.cancel,
        }

        try:
            while True:
                await asyncio.sleep(60)
        except asyncio.exceptions.CancelledError:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("closing the session...")
            await c.stop()
            await c.sleep()

    @classmethod
    async def knn(cls, args: argparse.Namespace):
        c = None
        while c is None:
            c = await KNNClient.with_device(args.mac)
        c.set_knn_classifier(args.periods, args.samples)
        await c.setup(emg_mode=EMGMode.SEND_EMG)
        await c.start()

        robot = TalkingRobot()
        c.set_robot(robot)
        await robot.setup()

        try:
            while True:
                await asyncio.sleep(60)
        except asyncio.exceptions.CancelledError:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("closing the session...")
            await c.stop()
            await c.sleep()

    @classmethod
    async def record(cls, args: argparse.Namespace):
        rc = None
        while rc is None:
            rc = await RecorderClient.with_device(args.mac)
        await rc.record(EMGMode(args.emg_mode), args.duration)
        exit(0)

    @classmethod
    async def train(cls, args: argparse.Namespace):
        KerasSequentialModel.fit(args.data_path, args.epochs)
        exit(0)

    @classmethod
    async def validate(cls, args: argparse.Namespace):
        vc = None
        while vc is None:
            vc = await ValidationClient.with_device(args.mac)
        vc.set_model(KerasSequentialModel())
        await vc.validate(EMGMode(args.emg_mode), args.duration)
        exit(0)
