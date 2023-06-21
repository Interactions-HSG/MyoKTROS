#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging
import time

from transitions_gui import WebMachine
from myoktros.robot import RobotModel, Mode, Transitions


async def server():
    logging.basicConfig(level=logging.INFO)
    robot = RobotModel()

    # initializing the machine will also start the server (default port is 8080)
    machine = WebMachine(
        robot,
        states=Mode,
        initial=Mode.INIT,
        transitions=Transitions,
        name="MyoKTROS",
        ignore_invalid_triggers=True,
        auto_transitions=False,
    )

    # try:
    #    await robot.setup()
    # except Exception:
    #    pass

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:  # Ctrl + C will shutdown the machine
        machine.stop_server()


if __name__ == '__main__':
    asyncio.run(server())
