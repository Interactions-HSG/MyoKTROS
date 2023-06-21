# -*- coding: utf-8 -*-
import asyncio

import pytest
from transitions.core import MachineError

from myoktros.robot import AsyncRobot, Mode


class TestRobot(AsyncRobot):
    __test__ = False

    async def disable_free_drive(self):
        await self.speak("Disabling free drive.")

    async def enable_free_drive(self):
        await self.speak("Enabling free drive.")

    async def get_pose(self):
        await self.speak("Getting the current pose.")
        return 0.1

    async def move(self):
        _ = self.waypoints[self.current_step]
        # do move
        await asyncio.sleep(1)

    async def speak(self, text):
        # await asyncio.create_subprocess_exec("say", text)
        await asyncio.sleep(0.1)


# def __repr__(self):
#    return f"{self.src}-{self.trigger}->{self.dst} ({'pass' if self.ok else 'fail'})"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "src,trigger,dst,ok",
    [
        (Mode.INIT, 'setup', Mode.LOCKED, True),
        (Mode.LOCKED, 'delete', Mode.PENDING_DELETION, True),
        (Mode.LOCKED, 'grabbed', Mode.UNLOCKED, True),
        (Mode.LOCKED, 'next', Mode.LOCKED, True),
        (Mode.LOCKED, 'play', Mode.PENDING_PLAYING, True),
        (Mode.LOCKED, 'previous', Mode.LOCKED, True),
        (Mode.UNLOCKED, 'cancel', Mode.LOCKED, True),
        (Mode.UNLOCKED, 'confirm', Mode.LOCKED, True),
        (Mode.PENDING_DELETION, 'cancel', Mode.LOCKED, True),
        (Mode.PENDING_DELETION, 'confirm', Mode.LOCKED, True),
        (Mode.ADJUSTING, 'cancel', Mode.LOCKED, True),
        (Mode.ADJUSTING, 'finish_adjusting', Mode.LOCKED, True),
        (Mode.PENDING_PLAYING, 'cancel', Mode.LOCKED, True),
        (Mode.PENDING_PLAYING, 'confirm', Mode.PLAYING, True),
        (Mode.PLAYING, 'cancel', Mode.LOCKED, True),
        (Mode.PLAYING, 'error', Mode.ERROR, True),
        (Mode.PLAYING, 'finish_playing', Mode.LOCKED, True),
        (Mode.PLAYING, 'play_next', Mode.PLAYING, True),
        (Mode.ERROR, 'reset', Mode.LOCKED, True),
        (Mode.INIT, 'grabbed', Mode.INIT, False),
        (Mode.PLAYING, 'grabbed', Mode.PLAYING, False),
        (Mode.UNLOCKED, 'grabbed', Mode.UNLOCKED, False),
    ],
)
async def test_transitions(src, trigger, dst, ok):
    tr = TestRobot()
    if trigger in ['confirm', 'delete', 'next', 'previous', 'play', 'play_next']:
        tr.waypoints = {
            0: 1,
            1: 2,
            2: 3,
        }
        tr.current_step = 1

    tr.machine.set_state(src)
    trigger = getattr(tr, trigger)
    if ok:
        await trigger()
    else:
        with pytest.raises(MachineError):
            await trigger()
    assert tr.state == dst


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "src,trigger,dst",
    [
        (Mode.LOCKED, 'delete', Mode.LOCKED),
        (Mode.LOCKED, 'next', Mode.LOCKED),
        (Mode.LOCKED, 'play', Mode.LOCKED),
        (Mode.LOCKED, 'previous', Mode.LOCKED),
    ],
)
async def test_invalid_conditions(src, trigger, dst):
    tr = TestRobot()
    tr.machine.set_state(src)
    trigger = getattr(tr, trigger)
    await trigger()
    assert tr.state == dst
