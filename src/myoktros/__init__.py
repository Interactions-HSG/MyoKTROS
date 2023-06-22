#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import asyncio
import logging
from pathlib import Path

from .command import Command


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
        "-a",
        "--address",
        help="IP address for the ROS server",
        default="127.0.0.1",
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
        "--model",
        choices=['keras', 'knn'],
        default='keras',
        help="gesture detection model",
    )
    run_mode.add_argument(
        "--n-samples",
        help="number of samples for 1 period",
        default=3,
    )
    run_mode.add_argument(
        "--n-periods",
        help="number of periods to be evaluated by the keras model",
        default=3,
    )
    run_mode.add_argument(
        "-p",
        "--port",
        help="port for the ROS server",
        default=8765,
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
        description="Calibrate a keras.Sequential model by recoding the user's EMG",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        default=10,
    )
    calibrate_mode.add_argument(
        "--emg-mode",
        help="set the myo.types.EMGMode to calibrate with \
        (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified)",
        type=int,
        default=1,
    )
    calibrate_mode.add_argument(
        "--epochs",
        help="epochs for fitting the keras model",
        type=int,
        default=1000,
    )
    calibrate_mode.add_argument(
        "--k",
        help="k for fitting the knn model",
        type=int,
        default=15,
    )
    calibrate_mode.add_argument(
        "--learning_rate",
        help="learning_rate for fitting the keras model",
        type=float,
        default=0.0001,
    )
    calibrate_mode.add_argument(
        "--mac",
        help="specify the mac address for Myo",
    )
    calibrate_mode.add_argument(
        "--model",
        help="model to calibrate",
        choices=['keras', 'knn'],
        default='keras',
    )
    calibrate_mode.add_argument(
        "--n-samples",
        help="number of samples for 1 period",
        default=10,
    )
    calibrate_mode.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="sets the log level to debug",
    )
    calibrate_mode.set_defaults(command=Command.calibrate)

    train_mode = commands.add_parser(
        'train',
        conflict_handler='resolve',
        description='Train the gesture model',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    train_mode.add_argument(
        "--data",
        help="path to the data directory to train the model with",
        type=str,
        default=(Path.cwd() / "data").absolute(),
    )
    train_mode.add_argument(
        "--emg-mode",
        help="set the myo.types.EMGMode to train on \
        (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified)",
        type=int,
        default=1,
    )
    train_mode.add_argument(
        "--epochs",
        help="epochs for fitting the model",
        type=int,
        default=1000,
    )
    train_mode.add_argument(
        "--k",
        help="k for fitting the knn model",
        type=int,
        default=15,
    )
    train_mode.add_argument(
        "--learning_rate",
        help="learning_rate for fitting the keras model",
        type=float,
        default=0.0001,
    )
    train_mode.add_argument(
        "--model",
        help="model to (re-)train",
        choices=['keras', 'knn'],
        default='keras',
    )
    train_mode.add_argument(
        "--n-samples",
        help="number of samples for 1 period",
        default=10,
        type=int,
    )
    train_mode.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="sets the log level to debug",
    )
    train_mode.set_defaults(command=Command.train)

    evaluate_mode = commands.add_parser(
        'evaluate',
        conflict_handler='resolve',
        description='evaluate the model performance for detecting the gestures',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    evaluate_mode.add_argument(
        "--duration",
        help="seconds to record each gesture for evaluation",
        type=int,
        default=5,
    )
    evaluate_mode.add_argument(
        "--emg-mode",
        help="set the myo.types.EMGMode to evaluate with \
        (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified)",
        type=int,
        default=1,
    )
    evaluate_mode.add_argument(
        "--mac",
        help="specify the mac address for Myo",
    )
    evaluate_mode.add_argument(
        "--model",
        help="model to evaluate",
        choices=['keras', 'knn'],
        default='keras',
    )
    evaluate_mode.add_argument(
        "--n-samples",
        help="number of samples for 1 period",
        default=10,
    )
    evaluate_mode.add_argument(
        "--n-periods",
        help="number of periods to be evaluated by the keras model",
        default=3,
    )
    evaluate_mode.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="sets the log level to debug",
    )
    evaluate_mode.set_defaults(command=Command.evaluate)

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
