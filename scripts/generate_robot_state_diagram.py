#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from pathlib import Path
from transitions.extensions import GraphMachine

from myoktros.robot import Mode, Robot, Transitions


class Model(Robot):
    def __init__(self):
        self.machine = GraphMachine(
            model=self,
            states=Mode,
            transitions=Transitions,
            initial=Mode.INIT,
            # title="MyoKTROS Robot State Machine",
            title="",
            # show_auto_transitions=True,
            show_conditions=True,
            show_state_attributes=True,
        )


async def main():
    out = Path(__file__).parent.parent / "assets" / "robot_state_diagram.png"
    model = Model()
    try:
        model.setup()
    except RuntimeWarning:
        pass
    model.get_graph().draw(out.absolute(), prog="dot")


asyncio.run(main())
