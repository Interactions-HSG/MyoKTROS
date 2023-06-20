#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import asyncio
import logging

from myo.types import ClassifierMode, EMGMode, IMUMode

from .client import KerasClient, LegacyClient
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

    elif args.mode == "legacy":
        while mc is None:
            mc = await LegacyClient.with_device(args.mac)
        mc.set_gesture_classifier_legacy(args.legacy_n_periods, args.legacy_n_samples)
        await mc.setup(emg_mode=EMGMode.SEND_EMG)
        await mc.start()

    else:
        exit(0)

    robot = TalkingRobot()
    mc.set_robot(robot)
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
        "-l",
        "--keras-queue-length",
        help="sets the queue length to collect gestures to detect",
        default=15,
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
    logging.getLogger("transitions.core").setLevel(logging.ERROR)

    asyncio.run(main(args))
