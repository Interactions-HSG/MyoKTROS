#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from pathlib import Path
from transitions.extensions import GraphMachine

from myoktros.robot import Mode, RobotModel, Transitions


async def main():
    out = Path(__file__).parent.parent / "assets" / "robot_state_diagram.png"
    robot = RobotModel()
    machine = GraphMachine(
        model=robot,
        states=Mode,
        transitions=Transitions,
        initial=Mode.INIT,
        # title="MyoKTROS Robot State Machine",
        title="",
        # show_auto_transitions=True,
        show_conditions=True,
        show_state_attributes=True,
    )

    try:
        robot.setup()
    except RuntimeWarning:
        pass
    machine.get_graph().draw(out.absolute(), prog="dot")


if __name__ == '__main__':
    asyncio.run(main())
