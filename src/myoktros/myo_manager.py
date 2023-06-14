# -*- coding: utf-8 -*-
import asyncio
import logging

import myo.types as mt
from myo import Myo
from myo.handle import Handle
from bleak.backends.characteristic import BleakGATTCharacteristic

logger = logging.getLogger(__name__)


class MyoManager:
    def __init__(self):
        self.m = None
        self.classifier_mode = None
        self.emg_mode = None
        self.imu_mode = None

    @classmethod
    async def with_device(cls, mac=None):
        self = cls()
        while self.m is None:
            if mac and mac != "":
                self.m = await Myo.with_mac(mac)
            else:
                self.m = await Myo.with_uuid()

        return self

    def emg_data_aggregate(self, handle, emg_data: mt.EMGData):
        if handle in [
            Handle.EMG0_DATA,
            Handle.EMG1_DATA,
            Handle.EMG2_DATA,
            Handle.EMG3_DATA,
        ]:
            self.on_emg_data(emg_data.sample1)
            self.on_emg_data(emg_data.sample2)

    def on_classifier_event(self, ce: mt.ClassifierEvent):
        raise NotImplementedError()

    def on_emg_data(self, data):  # data: list of 8 8-bit unsigned short
        raise NotImplementedError()

    def on_fv_data(self, data: mt.FVData):
        raise NotImplementedError()

    def on_imu_data(self, data: mt.IMUData):
        raise NotImplementedError()

    def on_motion_event(self, me: mt.MotionEvent):
        raise NotImplementedError()

    def notify_callback(self, sender: BleakGATTCharacteristic, data: bytearray):
        """
        invoke the on_* callbacks
        """
        handle = Handle(sender.handle)
        if handle == Handle.CLASSIFIER_EVENT:
            self.on_classifier_event(mt.ClassifierEvent(data))
        elif handle == Handle.FV_DATA:
            self.on_fv_data(mt.FVData(data))
        elif handle == Handle.IMU_DATA:
            self.on_imu_data(mt.IMUData(data))
        elif handle == Handle.MOTION_EVENT:
            self.on_motion_event(mt.MotionEvent(data))
        else:  # on EMG[0-3]_DATA handle
            self.emg_data_aggregate(handle, mt.EMGData(data))

    async def setup(
        self,
        emg_mode=mt.EMGMode.SEND_FILT,
        imu_mode=mt.IMUMode.NONE,
        classifier_mode=mt.ClassifierMode.DISABLED,
    ):
        logger.info(f"setting up the myo: {self.m.device.name}")
        battery = await self.m.battery_level()
        logger.info(f"remaining battery: {battery} %")
        # vibrate short *3
        await self.m.vibrate(mt.VibrationType.SHORT)
        await self.m.vibrate(mt.VibrationType.SHORT)
        await self.m.vibrate(mt.VibrationType.SHORT)
        # led red
        await self.m.led([255, 0, 0], [255, 0, 0])
        # never sleep
        await self.m.set_sleep_mode(mt.SleepMode.NEVER_SLEEP)
        # setup modes
        self.emg_mode = emg_mode
        self.imu_mode = imu_mode
        self.classifier_mode = classifier_mode
        await self.m.set_mode(
            emg_mode,
            imu_mode,
            classifier_mode,
        )
        # led green
        await self.m.led([0, 255, 0], [0, 255, 0])

    async def sleep(self):
        """
        put the device to sleep
        """
        logger.info(f"sleep {self.m.device.name}")
        # led purple
        await self.m.led([100, 100, 100], [100, 100, 100])
        # normal sleep
        await self.m.set_sleep_mode(mt.SleepMode.NORMAL)
        await asyncio.sleep(0.5)
        await self.m.disconnect()

    async def start(self):
        """
        start notify/indicate
        """
        logger.info(f"start notifying from {self.m.device.name}")
        # vibrate short
        await self.m.vibrate(mt.VibrationType.SHORT)
        # subscribe for notify/indicate
        if self.emg_mode in [mt.EMGMode.SEND_EMG, mt.EMGMode.SEND_RAW]:
            await self.m.client.start_notify(Handle.EMG0_DATA.value, self.notify_callback)
            await self.m.client.start_notify(Handle.EMG1_DATA.value, self.notify_callback)
            await self.m.client.start_notify(Handle.EMG2_DATA.value, self.notify_callback)
            await self.m.client.start_notify(Handle.EMG3_DATA.value, self.notify_callback)
        elif self.emg_mode == mt.EMGMode.SEND_FILT:
            await self.m.client.start_notify(Handle.FV_DATA.value, self.notify_callback)
        if self.imu_mode not in [mt.IMUMode.NONE, mt.IMUMode.SEND_EVENTS]:
            await self.m.client.start_notify(Handle.IMU_DATA.value, self.notify_callback)
        if self.imu_mode in [mt.IMUMode.SEND_EVENTS, mt.IMUMode.SEND_ALL]:
            await self.m.client.start_notify(mt.Handle.MOTION_EVENT.value, self.notify_callback)
        if self.classifier_mode == mt.ClassifierMode.ENABLED:
            await self.m.client.start_notify(mt.Handle.CLASSIFIER_EVENT.value, self.notify_callback)
        # led cyan
        await self.m.led([0, 255, 255], [0, 255, 255])

    async def stop(self):
        """
        stop notify/indicate
        """
        # vibrate short*2
        await self.m.vibrate(mt.VibrationType.SHORT)
        await self.m.vibrate(mt.VibrationType.SHORT)
        # unsubscribe from notify/indicate
        if self.emg_mode in [mt.EMGMode.SEND_EMG, mt.EMGMode.SEND_RAW]:
            await self.m.client.stop_notify(Handle.EMG0_DATA.value)
            await self.m.client.stop_notify(Handle.EMG1_DATA.value)
            await self.m.client.stop_notify(Handle.EMG2_DATA.value)
            await self.m.client.stop_notify(Handle.EMG3_DATA.value)
        elif self.emg_mode == mt.EMGMode.SEND_FILT:
            await self.m.client.stop_notify(Handle.FV_DATA.value)
        if self.imu_mode not in [mt.IMUMode.NONE, mt.IMUMode.SEND_EVENTS]:
            await self.m.client.stop_notify(Handle.IMU_DATA.value)
        if self.imu_mode in [mt.IMUMode.SEND_EVENTS, mt.IMUMode.SEND_ALL]:
            await self.m.client.stop_notify(Handle.MOTION_EVENT.value)
        if self.classifier_mode == mt.ClassifierMode.ENABLED:
            await self.m.client.stop_notify(Handle.CLASSIFIER_EVENT.value)
        # led green
        await self.m.led([0, 255, 0], [0, 255, 0])
        logger.info(f"stopped notification from {self.m.device.name}")
