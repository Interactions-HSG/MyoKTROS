#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import asyncio
import logging
import time
from pathlib import Path, PurePath

from myo import MyoClient
from myo.types import EMGData, EMGMode, FVData, VibrationType

from myoktros.gesture import Gesture

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
)


class RecorderClient(MyoClient):
    def __init__(self):
        super().__init__()
        self.buf = []
        self.gesture = None

    async def on_emg_data(self, emg: EMGData):
        line = ",".join(map(str, emg + (self.gesture.value,)))
        self.buf.append(line)

    async def on_fv_data(self, fvd: FVData):
        line = ",".join(map(str, (time.time(),) + fvd.fv + (fvd.mask, self.gesture.value)))
        self.buf.append(line)

    def set_gesture(self, g):
        self.gesture = g


def setup_output(g: Gesture, em: EMGMode) -> PurePath:
    datadir = Path(__file__).parent.parent / "assets" / "keras_gesture_data"
    if not datadir.exists():
        datadir.mkdir()
    now = time.strftime("%Y%m%d%H%M%S")
    p = datadir / f"{em.name}-{g.name}-{now}.csv"
    with open(p.absolute(), "w") as f:
        if em == EMGMode.SEND_FILT:
            print("timestamp,fv0,fv1,fv2,fv3,fv4,fv5,fv6,fv7,mask,gesture", file=f)
        else:
            print("emg0,emg1,emg2,emg3,emg4,emg5,emg6,emg7,gesture", file=f)

    return p


async def main(args: argparse.Namespace):
    logger.info("scanning for a Myo device...")
    rc = None
    while rc is None:
        rc = await RecorderClient.with_device(args.mac)

    gesture = Gesture(args.gesture)
    rc.set_gesture(gesture)
    emg_mode = EMGMode(args.emg_mode)
    outpath = setup_output(gesture, emg_mode)

    await rc.setup(emg_mode=emg_mode)
    logger.info(f"start recording {gesture.name} data with {emg_mode.name} for {args.seconds} seconds")
    logger.info("starting in 3")
    await rc.vibrate(VibrationType.SHORT)
    await asyncio.sleep(1)
    logger.info("starting in 2")
    await rc.vibrate(VibrationType.SHORT)
    await asyncio.sleep(1)
    logger.info("starting in 1")
    await rc.vibrate(VibrationType.SHORT)
    await asyncio.sleep(1)
    logger.info("go!")
    await rc.vibrate(VibrationType.MEDIUM)
    await rc.start()

    # record
    await asyncio.sleep(args.seconds)
    await rc.stop()
    await rc.sleep()

    with open(outpath.absolute(), "a") as f:
        for line in rc.buf:
            print(line, file=f)

    logger.info(f"saved the recorded data to {outpath.absolute()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Record train data from EMG data stream via Myo",
    )
    parser.add_argument(
        "gesture",
        metavar="N",
        help="the gesture to record (the enum value of myoktros.Gesture)",
        type=int,
    )
    parser.add_argument(
        "--emg-mode",
        choices=[1, 2, 3],
        help="set the myo.types.EMGMode (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified)",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--mac",
        help="the mac address for Myo",
    )
    parser.add_argument(
        "--seconds",
        help="the duration to record in seconds",
        type=int,
        default=30,
    )
    args = parser.parse_args()

    try:
        _ = Gesture(args.gesture)
    except Exception:
        print(f"invalid gesture enum: {args.gesture}")
        exit(-1)
    asyncio.run(main(args))
