# -*- coding: utf-8 -*-
import argparse
import asyncio
import logging

import myo.types as mt

# from .kt_mode import KTMode
# from .ros import XArm7
from .gesture import Gesture, GestureClassifierLegacy, GestureClassifierModel
from .myo_manager import MyoManager

logger = logging.getLogger(__name__)


async def main(args: argparse.Namespace):
    if args.mode == "keras":
        logger.info("loading the keras gesture model...")
        global gcm
        gcm = GestureClassifierModel()
        logger.info("scanning for a Myo device...")
        mm = None
        while mm is None:
            mm = await MyoManager.with_device(args.mac)

        def callback(fvd: mt.FVData):
            global gcm
            pred = gcm.predict(fvd)
            logger.info(pred)

        mm.on_fv_data = callback
        await mm.setup(emg_mode=mt.EMGMode.SEND_FILT)
        await mm.start()

    elif args.mode == "legacy":
        logger.info("loading the legacy gesture classifier...")
        global gcl
        gcl = GestureClassifierLegacy(args.legacy_n_periods, args.legacy_n_samples)
        logger.info("scanning for a Myo device...")
        mm = None
        while mm is None:
            mm = await MyoManager.with_device(args.mac)

        mm.on_emg_data = get_legacy_classifier(args.legacy_n_periods, args.legacy_n_samples)
        await mm.setup(emg_mode=mt.EMGMode.SEND_EMG)
        await mm.start()

    else:
        exit(0)

    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.exceptions.CancelledError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("closing the session...")
        await mm.stop()
        await mm.sleep()

    """
    xarm7 = XArm7()
    pred = Gesture.zero

    def update():
        return None

    while True:
        # Standard Mode
        if pred == Gesture.zero:
            xarm7.set_mode(Mode.STANDARD_MODE)

        # Teach Mode
        elif pred == Gesture.one:
            xarm7.set_mode(Mode.TEACH_MODE)

        # Confirm Position
        elif pred == Gesture.two:
            xarm7.record()

        # Toggle Gripper
        elif pred == Gesture.three:
            xarm7.gripper.toggle()

        # Delete the last confirmed position
        elif pred == Gesture.four:
            xarm7.undo()

        # Finish Teaching
        elif pred is None:
            break

        pred = update()
        await asyncio.sleep(1)

    logging.info("executing the recorded sequence")
    xarm7.execute()
    """


def on_gesture(g: Gesture):
    logger.info(f"gesture: {g.name}")


def get_legacy_classifier(n_periods: int = 3, n_samples: int = 10):
    global queue
    queue = []

    def on_emg_data(data):
        logger.debug(f"emg: {data}")
        global queue
        queue.append(data)
        # wait until the queue to fill up
        if len(queue) == n_periods * n_samples:
            global gcl
            g = gcl.predict(queue)
            on_gesture(g)
            queue = []

    return on_emg_data


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
        help="specify the Myo's mac address",
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
