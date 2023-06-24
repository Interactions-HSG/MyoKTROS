import argparse
import asyncio
import logging

from myo.types import Pose

from .client import EvaluaterClient, GestureClient, RecorderClient, DEFAULT_TRIGGER_MAP
from .gesture import Gesture, KerasSequentialModel, KNNClassifier
from .robot import TalkingRobot

logger = logging.getLogger(__name__)


class Command:  # no cov
    @classmethod
    async def run(cls, args: argparse.Namespace):
        logger.info('looking for a Myo device...')
        c = None
        while c is None:
            c = await GestureClient.with_device(args.mac)
            if c is None:
                logger.info('rescanning for a Myo device...')

        await c.configure(args)
        await c.start()

        # TODO: configure the robot with args
        robot = TalkingRobot()
        await robot.setup()

        # register the triggers
        tm = DEFAULT_TRIGGER_MAP
        tm[Gesture.GRAB] = robot.grabbed
        tm[Gesture.THUMBS_UP] = robot.play
        tm[Gesture.HORN] = robot.cancel
        tm[Pose.DOUBLE_TAP] = robot.confirm
        c.trigger_map = tm

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
    async def calibrate(cls, args: argparse.Namespace):
        if not args.only_train:
            await cls.train(args)
        if not args.only_record:
            await cls.train(args)
        exit(0)

    @classmethod
    async def record(cls, args: argparse.Namespace):
        logger.info('looking for a Myo device...')
        rc = None
        while rc is None:
            rc = await RecorderClient.with_device(args.mac)
            if rc is None:
                logger.info('rescanning for a Myo device...')

        await rc.record(args)

    @classmethod
    async def train(cls, args: argparse.Namespace):
        if args.model_type == 'keras':
            KerasSequentialModel.fit(args)
        elif args.model_type == 'knn':
            KNNClassifier.fit(args)

    @classmethod
    async def test(cls, args: argparse.Namespace):
        logger.info('looking for a Myo device...')
        ec = None
        while ec is None:
            ec = await EvaluaterClient.with_device(args.mac)
            if ec is None:
                logger.info('rescanning for a Myo device...')

        await ec.configure(args)
        await ec.start()
        try:
            while True:
                await asyncio.sleep(60)
        except asyncio.exceptions.CancelledError:
            pass
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("stopping the session...")
            await ec.stop()
            await ec.sleep()
