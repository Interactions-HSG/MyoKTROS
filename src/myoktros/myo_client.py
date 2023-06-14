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
        self.classifier_mode = None
        self.emg_mode = None
        self.imu_mode = None

    @classmethod
    async def with_device(cls, mac=None):
        self = cls()
        if mac and mac != "":
            self.m = await myo.Device.with_mac(mac)
        else:
            self.m = await myo.Device.with_uuid()

        if self.m is None:
            return None
        self.c = BleakClient(self.m.device)
        if self.c is None:
            return None

        await self.c.connect()
        logger.info(f"connected to {self.m.device.name}")

        return self

    def emg_data_aggregate(self, handle, emg_data: myo.EMGData):
        if handle in [
            myo.Handle.EMG0_DATA,
            myo.Handle.EMG1_DATA,
            myo.Handle.EMG2_DATA,
            myo.Handle.EMG3_DATA,
        ]:
            self.on_emg_data(emg_data.sample1)
            self.on_emg_data(emg_data.sample2)

    def on_classifier_event(self, ce: myo.ClassifierEvent):
        raise NotImplementedError()

    def on_emg_data(self, data):  # data: list of 8 8-bit unsigned short
        raise NotImplementedError()

    def on_fv_data(self, data: myo.FVData):
        raise NotImplementedError()

    def on_imu_data(self, data: myo.IMUData):
        raise NotImplementedError()

    def on_motion_event(self, me: myo.MotionEvent):
        raise NotImplementedError()

    def notify_callback(self, sender: BleakGATTCharacteristic, data: bytearray):
        """
        invoke the on_* callbacks
        """
        handle = myo.Handle(sender.handle)
        if handle == myo.Handle.CLASSIFIER_EVENT:
            self.on_classifier_event(myo.ClassifierEvent(data))
        elif handle == myo.Handle.FV_DATA:
            self.on_fv_data(myo.FVData(data))
        elif handle == myo.Handle.IMU_DATA:
            self.on_imu_data(myo.IMUData(data))
        elif handle == myo.Handle.MOTION_EVENT:
            self.on_motion_event(myo.MotionEvent(data))
        else:  # on EMG[0-3]_DATA handle
            self.emg_data_aggregate(handle, myo.EMGData(data))

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
        # setup modes
        self.emg_mode = emg_mode
        self.imu_mode = imu_mode
        self.classifier_mode = classifier_mode
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
        if self.emg_mode in [myo.EMGMode.SEND_EMG, myo.EMGMode.SEND_RAW]:
            await self.c.start_notify(myo.Handle.EMG0_DATA.value, self.notify_callback)
            await self.c.start_notify(myo.Handle.EMG1_DATA.value, self.notify_callback)
            await self.c.start_notify(myo.Handle.EMG2_DATA.value, self.notify_callback)
            await self.c.start_notify(myo.Handle.EMG3_DATA.value, self.notify_callback)
        elif self.emg_mode == myo.EMGMode.SEND_FILT:
            await self.c.start_notify(myo.Handle.FV_DATA.value, self.notify_callback)
        if self.imu_mode not in [myo.IMUMode.NONE, myo.IMUMode.SEND_EVENTS]:
            await self.c.start_notify(myo.Handle.IMU_DATA.value, self.notify_callback)
        if self.imu_mode in [myo.IMUMode.SEND_EVENTS, myo.IMUMode.SEND_ALL]:
            await self.c.start_notify(myo.Handle.MOTION_EVENT.value, self.notify_callback)
        if self.classifier_mode == myo.ClassifierMode.ENABLED:
            await self.c.start_notify(myo.Handle.CLASSIFIER_EVENT.value, self.notify_callback)
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
        if self.emg_mode in [myo.EMGMode.SEND_EMG, myo.EMGMode.SEND_RAW]:
            await self.c.stop_notify(myo.Handle.EMG0_DATA.value)
            await self.c.stop_notify(myo.Handle.EMG1_DATA.value)
            await self.c.stop_notify(myo.Handle.EMG2_DATA.value)
            await self.c.stop_notify(myo.Handle.EMG3_DATA.value)
        elif self.emg_mode == myo.EMGMode.SEND_FILT:
            await self.c.stop_notify(myo.Handle.FV_DATA.value)
        if self.imu_mode not in [myo.IMUMode.NONE, myo.IMUMode.SEND_EVENTS]:
            await self.c.stop_notify(myo.Handle.IMU_DATA.value)
        if self.imu_mode in [myo.IMUMode.SEND_EVENTS, myo.IMUMode.SEND_ALL]:
            await self.c.stop_notify(myo.Handle.MOTION_EVENT.value)
        if self.classifier_mode == myo.ClassifierMode.ENABLED:
            await self.c.stop_notify(myo.Handle.CLASSIFIER_EVENT.value)
        # led green
        await self.m.led(self.c, [0, 255, 0], [0, 255, 0])
        logger.info(f"stopped notification from {self.m.device.name}")
