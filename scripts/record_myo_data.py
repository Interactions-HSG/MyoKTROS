#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import asyncio
import logging
import time
from pathlib import Path, PurePath

from myo.types import EMGData, EMGMode, FVData

from myoktros.gesture import Gesture
from myoktros.myo_manager import MyoManager

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
)


def setup_output(g: Gesture, em: EMGMode) -> PurePath:
    out_dir = Path(__file__).parent.parent / "assets"
    if not out_dir.exists():
        out_dir.mkdir()
    now = time.strftime("%Y%m%d%H%M%S")
    p = out_dir / f"{em.name}-{g.name}-{now}.csv"
    with open(p.absolute(), "w") as f:
        if em == EMGMode.SEND_FILT:
            print("fv0,fv1,fv2,fv3,fv4,fv5,fv6,fv7,mask,gesture", file=f)
        else:
            print("emg0,emg1,emg2,emg3,emg4,emg5,emg6,emg7,gesture", file=f)

    return p


async def main(args: argparse.Namespace):
    logger.info("scanning for a Myo device...")
    mm = None
    while mm is None:
        mm = await MyoManager.with_device(args.mac)

    logger.info("connected to a Myo")

    global gesture, buf
    gesture = Gesture(args.gesture)
    emg_mode = EMGMode(args.emg_mode)
    outpath = setup_output(gesture, emg_mode)
    buf = []

    def write_emg_data_to_csv(emg_data: EMGData):
        global gesture, buf
        line = ",".join(map(str, emg_data + (gesture.value,)))
        buf.append(line)

    def write_fv_data_to_csv(fv_data: FVData):
        global gesture, buf
        line = ",".join(map(str, fv_data.fv + (fv_data.mask, gesture.value)))
        buf.append(line)

    if emg_mode == EMGMode.SEND_FILT:
        mm.on_fv_data = write_fv_data_to_csv
    else:
        mm.on_emg_data = write_emg_data_to_csv

    await mm.setup(emg_mode=emg_mode)
    logger.info(f"start recording {gesture.name} data with {emg_mode.name} for {args.seconds} seconds")
    await asyncio.sleep(2)
    await mm.start()

    # record
    await asyncio.sleep(args.seconds)
    await mm.stop()
    await mm.sleep()

    with open(outpath.absolute(), "a") as f:
        for line in buf:
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
