#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import asyncio
import logging
from pathlib import Path

from .command import Command


def entrypoint():  # no cov
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Myo EMG-based KT system for ROS",
    )
    commands = parser.add_subparsers(
        title='commands',
        description='valid subcommands',
        help='MyoKTROS mode',
    )

    keras_mode = commands.add_parser(
        'keras',
        conflict_handler='resolve',
    )
    keras_mode.add_argument(
        "-a",
        "--address",
        help="the IP address for the ROS server",
        default="127.0.0.1",
    )
    keras_mode.add_argument(
        "-l",
        "--queue-length",
        help="sets the queue length to collect gestures to detect",
        default=20,
    )
    keras_mode.add_argument(
        "-m",
        "--mac",
        help="specify the mac address for Myo",
    )
    keras_mode.add_argument(
        "-p",
        "--port",
        help="the port for the ROS server",
        default=8765,
    )
    keras_mode.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="sets the log level to debug",
    )
    keras_mode.set_defaults(command=Command.keras)

    knn_mode = commands.add_parser(
        'knn',
        conflict_handler='resolve',
    )
    knn_mode.add_argument(
        "-m",
        "--mac",
        help="specify the mac address for Myo",
    )
    knn_mode.add_argument(
        "--samples",
        help="number of samples for the knn classifier",
        default=3,
    )
    knn_mode.add_argument(
        "--periods",
        help="number of sampling periods for the knn classifier",
        default=10,
    )
    knn_mode.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="sets the log level to debug",
    )
    knn_mode.set_defaults(command=Command.knn)

    record_mode = commands.add_parser(
        'record',
        conflict_handler='resolve',
    )
    record_mode.add_argument(
        "--duration",
        help="seconds to record each gesture for recoding",
        type=int,
        default=10,
    )
    record_mode.add_argument(
        "--emg-mode",
        choices=[1, 2, 3],
        help="set the myo.types.EMGMode for recording \
        (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified)",
        type=int,
        default=1,
    )
    record_mode.add_argument(
        "-m",
        "--mac",
        help="specify the mac address for Myo",
    )
    record_mode.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="sets the log level to debug",
    )
    record_mode.set_defaults(command=Command.record)

    train_mode = commands.add_parser(
        'train',
        conflict_handler='resolve',
    )
    train_mode.add_argument(
        "--epochs",
        help="the epocchs for fitting the model",
        type=int,
        default=30,
    )
    train_mode.add_argument(
        "--data-path",
        help="the path to the directory containing recorded data",
        type=int,
        default=(Path.cwd() / "assets" / "keras_gesture_data").absolute(),
    )
    train_mode.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="sets the log level to debug",
    )
    train_mode.set_defaults(command=Command.train)

    validate_mode = commands.add_parser(
        'validate',
        conflict_handler='resolve',
    )
    validate_mode.add_argument(
        "--duration",
        help="seconds to record each gesture for validation",
        type=int,
        default=10,
    )
    validate_mode.add_argument(
        "--emg-mode",
        choices=[1, 2, 3],
        help="set the myo.types.EMGMode for validation \
        (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified)",
        type=int,
        default=1,
    )
    validate_mode.add_argument(
        "-m",
        "--mac",
        help="specify the mac address for Myo",
    )
    validate_mode.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="sets the log level to debug",
    )
    validate_mode.set_defaults(command=Command.validate)

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )
    # logging.getLogger("transitions.core").setLevel(logging.ERROR)

    if hasattr(args, 'command'):
        logging.info("starting MyoKTROS")
        asyncio.run(args.command(args))
    else:
        parser.print_help()
