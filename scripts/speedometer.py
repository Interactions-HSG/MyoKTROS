#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import asyncio
import logging
import time

from myo import MyoClient
from myo.types import (
    EMGMode,
    IMUMode,
    VibrationType,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
)


class MeasurementClient(MyoClient):
    def __init__(self):
        super().__init__()
        self.emg_buf = []
        self.fv_buf = []
        self.imu_buf = []

    async def on_emg_data_aggregate(self, emg):
        record = (time.time(),) + emg
        self.emg_buf.append(record)

    async def on_fv_data(self, fvd):
        record = (time.time(),) + fvd.fv
        self.fv_buf.append(record)

    async def on_imu_data(self, imu):
        record = (time.time(), imu)
        self.imu_buf.append(record)


async def main(args: argparse.Namespace):
    logger.info("scanning for a Myo device...")
    mc = None
    while mc is None:
        mc = await MeasurementClient.with_device(args.mac)

    emg_mode = EMGMode(args.emg_mode)
    imu_mode = IMUMode(args.imu_mode)

    await mc.setup(emg_mode=emg_mode, imu_mode=imu_mode)
    mc.aggregate_emg = True  # enable emg aggregation
    logger.info("starting in 3")
    await mc.vibrate(VibrationType.SHORT)
    await asyncio.sleep(1)
    logger.info("starting in 2")
    await mc.vibrate(VibrationType.SHORT)
    await asyncio.sleep(1)
    logger.info("starting in 1")
    await mc.vibrate(VibrationType.SHORT)
    await asyncio.sleep(1)
    logger.info("go!")
    await mc.vibrate(VibrationType.MEDIUM)
    await mc.start()

    # record
    await asyncio.sleep(args.seconds)
    await mc.stop()
    await mc.sleep()

    if emg_mode in [EMGMode.SEND_EMG, EMGMode.SEND_RAW]:
        start_time = mc.emg_buf[0][0]
        end_time = mc.emg_buf[-1][0]
        sample = len(mc.emg_buf)
        throughput = sample / (end_time - start_time)
        logger.info(f"EMGData: {throughput:.2f} S/s")

    if emg_mode == EMGMode.SEND_FILT:
        start_time = mc.fv_buf[0][0]
        end_time = mc.fv_buf[-1][0]
        sample = len(mc.fv_buf)
        throughput = sample / (end_time - start_time)
        logger.info(f"FVData: {throughput:.2f} S/s")

    if imu_mode in [IMUMode.SEND_ALL, IMUMode.SEND_DATA]:
        start_time = mc.imu_buf[0][0]
        end_time = mc.imu_buf[-1][0]
        sample = len(mc.imu_buf)
        throughput = sample / (end_time - start_time)
        logger.info(f"IMUData: {throughput:.2f} S/s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Measure the data stream throughput from Myo",
    )
    parser.add_argument(
        "--emg-mode",
        choices=[0, 1, 2, 3],
        help="set the myo.types.EMGMode \
        (0: disabled, 1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified)",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--imu-mode",
        choices=[0, 1, 2, 3],
        help="set the myo.types.IMUMode (0: disabled, 1: data, 2: event, 3: all)",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--mac",
        help="the mac address for Myo",
    )
    parser.add_argument(
        "--seconds",
        help="the duration to record in seconds",
        type=int,
        default=10,
    )
    args = parser.parse_args()

    asyncio.run(main(args))
