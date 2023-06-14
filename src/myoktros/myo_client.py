# -*- coding: utf-8 -*-
import asyncio
import logging

import myo
from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic

logger = logging.getLogger(__name__)


class MyoClient:
    def __init__(self):
        self.m = None
        self.c = None

    @classmethod
    async def with_device(cls, mac=None):
        self = cls()
        if mac and mac != "":
            self.m = await myo.Device.with_mac(mac)
        else:
            self.m = await myo.Device.with_uuid()

        self.c = BleakClient(self.m.device)
        await self.c.connect()
        logger.info(f"connected to {self.m.device.name}")

        return self

    def on_classifier_event(self, ce: myo.ClassifierEvent):
        raise NotImplementedError()

    def on_emg_data(self, data: myo.FVData):
        raise NotImplementedError()

    def on_imu_data(self, data: myo.IMUData):
        raise NotImplementedError()

    def on_motion_event(self, me: myo.MotionEvent):
        raise NotImplementedError()

    def notify_callback(self, sender: BleakGATTCharacteristic, data: bytearray):
        """
        invoke the on_* callbacks
        """
        name = myo.Handle(sender.handle).name
        if name == myo.Handle.CLASSIFIER_EVENT.name:
            self.on_classifier_event(myo.ClassifierEvent(data))
        elif name == myo.Handle.FV_DATA.name:
            self.on_emg_data(myo.FVData(data))
        elif name == myo.Handle.IMU_DATA.name:
            self.on_imu_data(myo.IMUData(data))
        elif name == myo.Handle.MOTION_EVENT.name:
            self.on_motion_event(myo.MotionEvent(data))

    async def setup(
        self, emg_mode=myo.EMGMode.SEND_FILT, imu_mode=myo.IMUMode.NONE, classifier_mode=myo.ClassifierMode.DISABLED
    ):
        logger.info(f"setting up the myo: {self.m.device.name}")
        battery = await self.m.battery_level(self.c)
        logger.info(f"remaining battery: {battery} %")
        # vibrate short *3
        await self.m.vibrate(self.c, myo.VibrationType.SHORT)
        await self.m.vibrate(self.c, myo.VibrationType.SHORT)
        await self.m.vibrate(self.c, myo.VibrationType.SHORT)
        # led red
        await self.m.led(self.c, [255, 0, 0], [255, 0, 0])
        # never sleep
        await self.m.set_sleep_mode(self.c, myo.SleepMode.NEVER_SLEEP)
        # enable emg, imu, classifier events
        await self.m.set_mode(
            self.c,
            emg_mode,
            imu_mode,
            classifier_mode,
        )
        # led green
        await self.m.led(self.c, [0, 255, 0], [0, 255, 0])

    async def sleep(self):
        """
        put the device to sleep
        """
        logger.info(f"sleep {self.m.device.name}")
        # led purple
        await self.m.led(self.c, [100, 100, 100], [100, 100, 100])
        # normal sleep
        await self.m.set_sleep_mode(self.c, myo.SleepMode.NORMAL)
        await asyncio.sleep(0.5)
        await self.c.disconnect()

    async def start(self):
        """
        start notify/indicate
        """
        logger.info(f"start notifying from {self.m.device.name}")
        # vibrate short
        await self.m.vibrate(self.c, myo.VibrationType.SHORT)
        # subscribe for notify/indicate
        await self.c.start_notify(myo.Handle.FV_DATA.value, self.notify_callback)
        await self.c.start_notify(myo.Handle.IMU_DATA.value, self.notify_callback)
        await self.c.start_notify(myo.Handle.MOTION_EVENT.value, self.notify_callback)
        await self.c.start_notify(myo.Handle.CLASSIFIER_EVENT.value, self.notify_callback)
        # await self.c.start_notify(myo.Handle.FV_DATA.value, callback)
        # led cyan
        await self.m.led(self.c, [0, 255, 255], [0, 255, 255])

    async def stop(self):
        """
        stop notify/indicate
        """
        # vibrate short*2
        await self.m.vibrate(self.c, myo.VibrationType.SHORT)
        await self.m.vibrate(self.c, myo.VibrationType.SHORT)
        # unsubscribe from notify/indicate
        await self.c.stop_notify(myo.Handle.FV_DATA.value)
        await self.c.stop_notify(myo.Handle.IMU_DATA.value)
        await self.c.stop_notify(myo.Handle.MOTION_EVENT.value)
        await self.c.stop_notify(myo.Handle.CLASSIFIER_EVENT.value)
        # led green
        await self.m.led(self.c, [0, 255, 0], [0, 255, 0])
        logger.info(f"stopped notification from {self.m.device.name}")
