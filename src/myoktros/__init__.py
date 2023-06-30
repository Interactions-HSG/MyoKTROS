#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import asyncio
import configparser
import logging
from pathlib import Path

from .command import Command
from .gesture import Gesture, GestureModel, KerasSequentialModel, KNNClassifier, SVMClassifier


def entrypoint():  # no cov
    parser = argparse.ArgumentParser(
        description="Myo EMG-based KT system for ROS",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="path to the config file (config.ini)",
        type=str,
        default=(Path.cwd() / "config.ini").absolute(),
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
        "--emg-mode",
        help="set the myo.types.EMGMode to use \
        (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified)",
        type=int,
        default=1,
    )
    run_mode.add_argument(
        "--knn-k",
        help="k used for fitting the knn model",
        type=int,
        default=5,
    )
    run_mode.add_argument(
        "--knn-metric",
        help="distance metric used for fitting the knn model",
        choices=['minkowski', 'euclidean', 'manhattan'],
        default='minkowski',
    )
    run_mode.add_argument(
        "--mac",
        help="specify the mac address for Myo",
    )
    run_mode.add_argument(
        "--model-type",
        choices=['keras', 'knn', 'svm'],
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
        "--svm-c",
        help="regularization parameter C used for fitting the svm model (must be strictly positive)",
        type=float,
        default=1.0,
    )
    run_mode.add_argument(
        "--svm-degree",
        help="degree of polynomial function used for fitting the svm model with 'poly' kernel",
        type=int,
        default=3,
    )
    run_mode.add_argument(
        "--svm-gamma",
        help="kernel coefficient used for fitting the svm model",
        choices=['scale', 'auto'],
        default='scale',
    )
    run_mode.add_argument(
        "--svm-kernel",
        help="kernel type used for fitting the svm model",
        choices=['linear', 'poly', 'rbf', 'sigmoid'],
        default='rbf',
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
        help="if specified, only record a specific gesture",
        default="all",
        type=str,
    )
    calibrate_mode.add_argument(
        "--knn-algorithm",
        help="algorithm for fitting the knn model",
        choices=['auto', 'brute', 'ball_tree', 'kd_tree'],
        default='auto',
    )
    calibrate_mode.add_argument(
        "--knn-k",
        help="k for fitting the knn model",
        type=int,
        default=5,
    )
    calibrate_mode.add_argument(
        "--knn-metric",
        help="distance metric for fitting the knn model",
        choices=['minkowski', 'euclidean', 'manhattan'],
        default='minkowski',
    )
    calibrate_mode.add_argument(
        "--mac",
        help="specify the mac address for Myo",
    )
    calibrate_mode.add_argument(
        "--model-type",
        help="model type to calibrate",
        choices=['keras', 'knn', 'svm'],
        default='keras',
    )
    calibrate_mode.add_argument(
        "--n-samples",
        help="number of samples to detect a gesture",
        type=int,
        default=50,
    )
    calibrate_mode.add_argument(
        "--svm-c",
        help="regularization parameter C for fitting the svm model (must be strictly positive)",
        type=float,
        default=1.0,
    )
    calibrate_mode.add_argument(
        "--svm-degree",
        help="degree of polynomial function for fitting the svm model with 'poly' kernel",
        type=int,
        default=3,
    )
    calibrate_mode.add_argument(
        "--svm-gamma",
        help="kernel coefficient for fitting the svm model",
        choices=['scale', 'auto'],
        default='scale',
    )
    calibrate_mode.add_argument(
        "--svm-kernel",
        help="kernel type for fitting the svm model",
        choices=['linear', 'poly', 'rbf', 'sigmoid'],
        default='poly',
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
        "--knn-k",
        help="k used for fitting the knn model",
        type=int,
        default=5,
    )
    test_mode.add_argument(
        "--knn-metric",
        help="distance metric used for fitting the knn model",
        choices=['minkowski', 'euclidean', 'manhattan'],
        default='minkowski',
    )
    test_mode.add_argument(
        "--mac",
        help="specify the mac address for Myo",
    )
    test_mode.add_argument(
        "--model-type",
        help="model type to test",
        choices=['keras', 'knn', 'svm'],
        default='keras',
    )
    test_mode.add_argument(
        "--n-samples",
        help="number of samples to detect a gesture",
        type=int,
        default=50,
    )
    test_mode.add_argument(
        "--svm-c",
        help="regularization parameter C used for fitting the svm model (must be strictly positive)",
        type=float,
        default=1.0,
    )
    test_mode.add_argument(
        "--svm-degree",
        help="degree of polynomial function used for fitting the svm model with 'poly' kernel",
        type=int,
        default=3,
    )
    test_mode.add_argument(
        "--svm-gamma",
        help="kernel coefficient used for fitting the svm model",
        choices=['scale', 'auto'],
        default='scale',
    )
    test_mode.add_argument(
        "--svm-kernel",
        help="kernel type used for fitting the svm model",
        choices=['linear', 'poly', 'rbf', 'sigmoid'],
        default='rbf',
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

    # load the config
    config_path = Path(args.config)
    if not config_path.exists():
        logging.error(f"{config_path.name} doesn't exist")
        exit(1)
    # initialize the GestureEnum class
    Gesture.load_config(config_path)

    if hasattr(args, 'command'):
        logging.info("starting MyoKTROS")
        asyncio.run(args.command(args))
    else:
        parser.print_help()
