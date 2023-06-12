# -*- coding: utf-8 -*-
import argparse
import asyncio
import logging

from .gesture import Gesture
from .mode import Mode
from .ros import XArm7


async def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Myo EMG-based KT system for ROS",
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
        "-p", "--port", help="the port for the ROS server", default=8765
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )
    logging.getLogger("myoktros").setLevel(level=log_level)
    logging.info(f"connecting to {args.address}:{args.port}...")

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


def entrypoint():
    asyncio.run(main())
