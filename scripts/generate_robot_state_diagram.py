#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from transitions.extensions import GraphMachine

from myoktros.robot import Mode, Robot


class Model(Robot):
    def __init__(self):
        self.machine = GraphMachine(
            model=self,
            # show_auto_transitions=True,
            states=Mode,
            transitions=self.transitions,
            initial=Mode.INIT,
        )


out = Path(__file__).parent.parent / "assets" / "robot_state_diagram.png"
m = Model()
m.get_graph().draw(out.absolute(), prog='dot')
