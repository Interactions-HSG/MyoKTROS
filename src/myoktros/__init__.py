#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import asyncio
import logging
from pathlib import Path

from .command import Command
from .gesture import Gesture, GestureModel, KerasSequentialModel, KNNClassifier


def entrypoint():  # no cov
    parser = argparse.ArgumentParser(
        description="Myo EMG-based KT system for ROS",
    )
    commands = parser.add_subparsers(
        title='commands',
    )

    run_mode = commands.add_parser(
        'run',
        conflict_handler='resolve',
        description='Run MyoKTROS',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    run_mode.add_argument(
        "--arm-dominance",
        help="left/right arm wearing the Myo",
        choices=['left', 'right'],
        default='right',
    )
    run_mode.add_argument(
        "-c",
        "--robot-config",
        help="path config file (config.ini)",
        type=str,
        default="config.ini",
    )
    run_mode.add_argument(
        "--emg-mode",
        help="set the myo.types.EMGMode to use \
        (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified)",
        type=int,
        default=1,
    )
    run_mode.add_argument(
        "--mac",
        help="specify the mac address for Myo",
    )
    run_mode.add_argument(
        "--model-type",
        choices=['keras', 'knn'],
        default='keras',
        help="model type to detect the gestures",
    )
    run_mode.add_argument(
        "--n-samples",
        help="number of samples to detect a gesture",
        type=int,
        default=50,
    )
    run_mode.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="sets the log level to debug",
    )
    run_mode.set_defaults(command=Command.run)

    calibrate_mode = commands.add_parser(
        'calibrate',
        conflict_handler='resolve',
        description="Calibrate the gesture model by recoding the user's EMG",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    calibrate_mode.add_argument(
        "--arm-dominance",
        help="left/right arm wearing the Myo",
        choices=['left', 'right'],
        default='right',
    )
    calibrate_mode.add_argument(
        "--data",
        help="path to the data directory to save recorded data",
        type=str,
        default=(Path.cwd() / "data").absolute(),
    )
    calibrate_mode.add_argument(
        "--duration",
        help="seconds to record each gesture for recoding",
        type=int,
        default=30,
    )
    calibrate_mode.add_argument(
        "--emg-mode",
        help="set the myo.types.EMGMode to calibrate with \
        (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified)",
        type=int,
        default=1,
    )
    calibrate_mode.add_argument(
        "-g",
        "--gesture",
        help=f"if specified, only record a specific gesture {[g.name for g in Gesture]}",
        default="all",
        type=str,
    )
    calibrate_mode.add_argument(
        "--k",
        help="k for fitting the knn model",
        type=int,
        default=15,
    )
    calibrate_mode.add_argument(
        "--mac",
        help="specify the mac address for Myo",
    )
    calibrate_mode.add_argument(
        "--model-type",
        help="model type to calibrate",
        choices=['keras', 'knn'],
        default='keras',
    )
    calibrate_mode.add_argument(
        "--n-samples",
        help="number of samples to detect a gesture",
        type=int,
        default=50,
    )
    calibrate_mode.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="sets the log level to debug",
    )
    cm_only_options = calibrate_mode.add_mutually_exclusive_group()
    cm_only_options.add_argument(
        "--only-record",
        action='store_true',
        help="only record EMG data without training a model",
    )
    cm_only_options.add_argument(
        "--only-train",
        action='store_true',
        help="only train a model without recording EMG data",
    )
    calibrate_mode.set_defaults(command=Command.calibrate)

    test_mode = commands.add_parser(
        'test',
        conflict_handler='resolve',
        description='test the model to detect the gestures without attaching to a robot',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    test_mode.add_argument(
        "--arm-dominance",
        help="left/right arm wearing the Myo",
        choices=['left', 'right'],
        default='right',
    )
    test_mode.add_argument(
        "--emg-mode",
        help="set the myo.types.EMGMode for testing \
        (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified)",
        type=int,
        default=1,
    )
    test_mode.add_argument(
        "--mac",
        help="specify the mac address for Myo",
    )
    test_mode.add_argument(
        "--model-type",
        help="model type to test",
        choices=['keras', 'knn'],
        default='keras',
    )
    test_mode.add_argument(
        "--n-samples",
        help="number of samples to detect a gesture",
        type=int,
        default=50,
    )
    test_mode.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="sets the log level to debug",
    )
    test_mode.set_defaults(command=Command.test)

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
