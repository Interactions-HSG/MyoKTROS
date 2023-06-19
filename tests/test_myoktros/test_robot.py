# -*- coding: utf-8 -*-
import asyncio

import pytest
from transitions.core import MachineError

from myoktros.robot import Mode, Robot


class TestRobot(Robot):
    def __init__(self):
        super().__init__()

    async def disable_free_drive(self):
        await self.speak("Disabling free drive.")

    async def enable_free_drive(self):
        await self.speak("Enabling free drive.")

    async def get_pose(self):
        await self.speak("Getting the current pose.")
        return 0.1

    async def move(self):
        await self.speak("Moving to the robot.")
        position = self.waypoints[self.current_step]
        await asyncio.sleep(position)

    async def speak(self, text):
        if text != "":
            # await asyncio.create_subprocess_exec("say", text)
            await asyncio.sleep(0.1)


# def test_robot_callbacks():
#    tr = TestRobot()


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
        Case(Mode.INIT, "setup", Mode.LOCKED),
        Case(Mode.LOCKED, "grabbed", Mode.TEACHING),
        Case(Mode.LOCKED, "delete", Mode.PENDING_DELETION),
        Case(Mode.TEACHING, "confirm", Mode.LOCKED),
        Case(Mode.ERROR, "reset", Mode.LOCKED),
        Case(Mode.PLAYING_ONCE, "error", Mode.ERROR),
        Case(Mode.PENDING_DELETION, "cancel", Mode.LOCKED),
        Case(Mode.PENDING_DELETION, "confirm", Mode.LOCKED),
        Case(Mode.PENDING_PLAY_ONCE, "confirm", Mode.PLAYING_ONCE),
        Case(Mode.PENDING_PLAY_REPEAT, "cancel", Mode.LOCKED),
        Case(Mode.PENDING_PLAY_REPEAT, "confirm", Mode.PLAYING_REPEAT),
        Case(Mode.PLAYING_REPEAT, "cancel", Mode.LOCKED),
        Case(Mode.INIT, "grabbed", Mode.INIT, False),
        Case(Mode.PLAYING_ONCE, "grabbed", Mode.PLAYING_ONCE, False),
        Case(Mode.TEACHING, "grabbed", Mode.TEACHING, False),
    ]

    return cases


@parametrize("case", load_transition_cases())
@pytest.mark.asyncio
async def test_robot_transitions(case):
    tr = TestRobot()
    tr.machine.set_state(case.src)
    if case.trigger == "delete" or case.trigger == "confirm":
        tr.waypoints[tr.current_step] = 0.1
    trigger = getattr(tr, case.trigger)
    if case.ok:
        await trigger()
    # elif case.trigger == "delete" and not case.ok:
    else:
        with pytest.raises(MachineError):
            await trigger()
    assert tr.state == case.dst
