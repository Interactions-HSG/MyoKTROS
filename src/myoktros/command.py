import argparse
import asyncio
import configparser
import logging

# import tomllib
from pathlib import Path

from myo.types import EMGMode, Pose

from .client import EvaluaterClient, GestureClient, RecorderClient
from .gesture import Gesture, GestureModel, KerasSequentialModel, KNNClassifier, SVMClassifier
from .robot import Lite6ROSWS, XArm7ROSWS

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

        # read configuration
        config = configparser.ConfigParser()
        config.read(Path(args.config))
        rc = config['myoktros.robot']
        robot = None

        # initialize the robot
        if rc['driver'] == 'xarm_rosws':
            rc = rc['myoktros.robot.xarm_rosws']
            if rc['model'] == 'lite6':
                robot = Lite6ROSWS(rc['ip'], int(rc['port']))
            elif rc['model'] == 'xarm7':
                robot = XArm7ROSWS(rc['ip'], int(rc['port']))

        if robot is None:
            exit(1)

        await robot.setup()

        # TODO: trigger map assignment can be entirely done in the config
        # register the triggers
        tm = GestureModel.get_default_trigger_map()
        tmc = config['myoktros.trigger_map']
        try:
            tm[Gesture.Enum[tmc['grabbed']]] = robot.grabbed
            tm[Gesture.Enum[tmc['play']]] = robot.play
            tm[Gesture.Enum[tmc['confirm']]] = robot.confirm
            tm[Gesture.Enum[tmc['delete']]] = robot.delete
        except KeyError as e:
            logger.error(f"{e} is not a valid gesture")
            exit(1)

        tm[Pose.DOUBLE_TAP] = robot.cancel
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
            await cls.record(args)
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
        await rc.sleep()

    @classmethod
    async def train(cls, args: argparse.Namespace):
        assets_path = Path(__file__).parent.parent.parent / "assets"
        data_path = Path(args.data)
        emg_mode = EMGMode(args.emg_mode)
        if args.model_type == 'keras':
            KerasSequentialModel.fit(
                args.arm_dominance,
                assets_path,
                data_path,
                emg_mode,
                args.n_samples,
            )
        elif args.model_type == 'knn':
            KNNClassifier.fit(
                args.arm_dominance,
                assets_path,
                data_path,
                emg_mode,
                args.knn_k,
                args.knn_algorithm,
                args.knn_metric,
                args.n_samples,
            )
        elif args.model_type == 'svm':
            SVMClassifier.fit(
                args.arm_dominance,
                assets_path,
                data_path,
                emg_mode,
                args.n_samples,
                args.svm_c,
                args.svm_degree,
                args.svm_gamma,
                args.svm_kernel,
            )

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
