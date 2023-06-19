# -*- coding: utf-8 -*-
import asyncio

import pytest
from transitions.core import MachineError

from myoktros.robot import Mode, Robot


class TestRobot(Robot):
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
        await asyncio.sleep(0.1)

    async def speak(self, text):
        if text != "":
            # await asyncio.create_subprocess_exec("say", text)
            await asyncio.sleep(0.1)


def parametrize(name, values):
    # function for readable description
    return pytest.mark.parametrize(name, values, ids=map(repr, values))


def load_transition_cases():
    class Case:
        def __init__(self, src, trigger, dst, ok=True):
            self.src = src
            self.trigger = trigger
            self.dst = dst
            self.ok = ok

        def __repr__(self):
            return f"{self.src}-{self.trigger}->{self.dst} ({'pass' if self.ok else 'fail'})"

    cases = [
        Case(Mode.INIT, 'setup', Mode.LOCKED),
        Case(Mode.LOCKED, 'grabbed', Mode.UNLOCKED),
        Case(Mode.LOCKED, 'delete', Mode.PENDING_DELETION),
        Case(Mode.UNLOCKED, 'confirm', Mode.LOCKED),
        Case(Mode.ERROR, 'reset', Mode.LOCKED),
        Case(Mode.PLAYING_ONCE, 'error', Mode.ERROR),
        Case(Mode.PENDING_DELETION, 'cancel', Mode.LOCKED),
        Case(Mode.PENDING_DELETION, 'confirm', Mode.LOCKED),
        Case(Mode.PENDING_PLAY_ONCE, 'confirm', Mode.PLAYING_ONCE),
        Case(Mode.PENDING_PLAY_REPEAT, 'cancel', Mode.LOCKED),
        Case(Mode.PENDING_PLAY_REPEAT, 'confirm', Mode.PLAYING_REPEAT),
        Case(Mode.PLAYING_REPEAT, 'cancel', Mode.LOCKED),
        Case(Mode.LOCKED, 'next', Mode.LOCKED),
        Case(Mode.LOCKED, 'previous', Mode.LOCKED),
        Case(Mode.INIT, 'grabbed', Mode.INIT, False),
        Case(Mode.PLAYING_ONCE, 'grabbed', Mode.PLAYING_ONCE, False),
        Case(Mode.UNLOCKED, 'grabbed', Mode.UNLOCKED, False),
    ]

    return cases


@parametrize("case", load_transition_cases())
@pytest.mark.asyncio
async def test_robot_transitions(case):
    tr = TestRobot()
    tr.machine.set_state(case.src)
    if case.trigger in ['confirm', 'delete', 'next', 'previous', 'play_once', 'play_repeat']:
        tr.waypoints = {
            0: 0.1,
            1: 0.1,
            2: 0.1,
        }
        tr.current_step = 1
    trigger = getattr(tr, case.trigger)
    if case.ok:
        await trigger()
    else:
        with pytest.raises(MachineError):
            await trigger()
    assert tr.state == case.dst
