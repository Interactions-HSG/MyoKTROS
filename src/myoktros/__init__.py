#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import asyncio
import logging
from pathlib import Path

from myo.types import ClassifierMode, EMGMode, IMUMode, Pose

from .client import KerasClient, KNNClient, RecorderClient, ValidationClient
from .gesture import Gesture, KerasSequentialModel
from .robot import TalkingRobot

logger = logging.getLogger(__name__)


async def main(args: argparse.Namespace):
    mc = None
    if args.mode == "keras":
        while mc is None:
            mc = await KerasClient.with_device(args.mac)
        mc.set_queue_length(args.keras_queue_length)  # 1 gesture/sec
        await mc.setup(
            classifier_mode=ClassifierMode.ENABLED,
            emg_mode=EMGMode.SEND_FILT,
            imu_mode=IMUMode.SEND_EVENTS,
        )
        await mc.start()

    elif args.mode == "knn":
        while mc is None:
            mc = await KNNClient.with_device(args.mac)
        mc.set_knn_classifier(args.knn_periods, args.knn_samples)
        await mc.setup(emg_mode=EMGMode.SEND_EMG)
        await mc.start()

    elif args.mode == "record":
        rc = None
        while rc is None:
            rc = await RecorderClient.with_device(args.mac)
        await rc.record(EMGMode(args.emg_mode), args.duration)
        exit(0)

    elif args.mode == "train":
        KerasSequentialModel.fit(args.train_data_path, args.train_epochs)
        exit(0)

    elif args.mode == "validate":
        vc = None
        while vc is None:
            vc = await ValidationClient.with_device(args.mac)
        vc.set_model(KerasSequentialModel())
        await vc.validate(EMGMode(args.emg_mode), args.duration)
        exit(0)

    else:
        logger.error("unknown mode: {args.mode}")
        exit(1)

    robot = TalkingRobot()
    mc.set_robot(robot)
    await robot.setup()

    if args.mode == "keras":
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
        await mc.stop()
        await mc.sleep()


def entrypoint():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Myo EMG-based KT system for ROS",
    )
    parser.add_argument(
        "mode",
        choices=["keras", "knn", "record", "train", "validate"],
        help="mode to select",
    )
    parser.add_argument(
        "-a",
        "--address",
        help="the IP address for the ROS server",
        default="127.0.0.1",
    )
    parser.add_argument(
        "-l",
        "--keras-queue-length",
        help="sets the queue length to collect gestures to detect",
        default=20,
    )
    parser.add_argument(
        "-m",
        "--mac",
        help="specify the mac address for Myo",
    )
    parser.add_argument(
        "--knn_samples",
        help="number of samples for the knn classifier",
        default=3,
    )
    parser.add_argument(
        "--knn_periods",
        help="number of sampling periods for the knn classifier",
        default=10,
    )
    parser.add_argument(
        "--duration",
        help="seconds to record each gesture for recoding/validation",
        type=int,
        default=30,
    )
    parser.add_argument(
        "--emg-mode",
        choices=[1, 2, 3],
        help="set the myo.types.EMGMode for recording/validation \
        (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified)",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--train-epochs",
        help="the epocchs for fitting the model",
        type=int,
        default=30,
    )
    parser.add_argument(
        "--train-data-path",
        help="the path to the directory containing recorded data",
        type=int,
        default=(Path.cwd() / "assets" / "keras_gesture_data").absolute(),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="sets the log level to debug",
    )

    parser.add_argument("-p", "--port", help="the port for the ROS server", default=8765)

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )
    # logging.getLogger("transitions.core").setLevel(logging.ERROR)

    asyncio.run(main(args))
