# -*- coding: utf-8 -*-
import asyncio
import logging

from enum import Enum
from transitions.extensions.asyncio import AsyncMachine

logger = logging.getLogger(__name__)


class Mode(Enum):
    INIT = 0
    LOCKED = 1
    UNLOCKED = 2
    PENDING_DELETION = 10
    PENDING_PLAYING = 11
    ADJUSTING = 20
    PLAYING = 21
    ERROR = -1


Transitions = [
    # source: INIT
    {
        'trigger': 'setup',
        'source': Mode.INIT,
        'dest': Mode.LOCKED,
        'before': '_setup',
        'after': '_report_setup_completed',
    },
    # source: LOCKED
    {
        'trigger': 'delete',
        'source': Mode.LOCKED,
        'dest': Mode.PENDING_DELETION,
        'conditions': '_has_previous_step',
        'after': '_ask_deletion',
    },
    {
        'trigger': 'grabbed',
        'source': Mode.LOCKED,
        'dest': Mode.UNLOCKED,
        'before': '_report_unlocked',
        'after': 'enable_free_drive',
    },
    {
        'trigger': 'next',
        'source': Mode.LOCKED,
        'dest': Mode.ADJUSTING,
        'conditions': '_has_next_step',
        'before': '_move_to_next',
        'after': '_report_adjusting_completed',
    },
    {
        'trigger': 'play',
        'source': Mode.LOCKED,
        'dest': Mode.PENDING_PLAYING,
        'conditions': '_has_valid_waypoints',
        'after': '_ask_playing',
    },
    {
        'trigger': 'previous',
        'source': Mode.LOCKED,
        'dest': Mode.ADJUSTING,
        'conditions': '_has_previous_step',
        'before': '_move_to_previous',
        'after': '_report_adjusting_completed',
    },
    # source: UNLOCKED
    {
        'trigger': 'cancel',
        'source': Mode.UNLOCKED,
        'dest': Mode.LOCKED,
        'before': '_report_cancel_teaching',
        'after': 'disable_free_drive',
    },
    {
        'trigger': 'confirm',
        'source': Mode.UNLOCKED,
        'dest': Mode.LOCKED,
        'before': '_report_confirm_waypoint',
        'after': ['_save_waypoint', 'disable_free_drive'],
    },
    # source: PENDING_DELETION
    {
        'trigger': 'cancel',
        'source': Mode.PENDING_DELETION,
        'dest': Mode.LOCKED,
        'after': '_report_cancel_deletion',
    },
    {
        'trigger': 'confirm',
        'source': Mode.PENDING_DELETION,
        'dest': Mode.LOCKED,
        'before': '_delete_waypoint',
        'after': '_report_confirm_deletion',
    },
    # source: ADJUSTING
    {
        'trigger': 'cancel',
        'source': Mode.ADJUSTING,
        'dest': Mode.LOCKED,
        'after': '_report_cancel_adjusting',
    },
    {
        'trigger': 'finish_adjusting',
        'source': Mode.ADJUSTING,
        'dest': Mode.LOCKED,
    },
    # source: PENDING_PLAYING
    {
        'trigger': 'cancel',
        'source': Mode.PENDING_PLAYING,
        'dest': Mode.LOCKED,
        'before': '_report_cancel_playing',
    },
    {
        'trigger': 'confirm',
        'source': Mode.PENDING_PLAYING,
        'dest': Mode.PLAYING,
        'before': '_play',
        'after': '_play_next',
    },
    # source: PLAYING
    {
        'trigger': 'cancel',
        'source': Mode.PLAYING,
        'dest': Mode.LOCKED,
        'before': '_report_cancel_playing',
    },
    {
        'trigger': 'finish_playing',
        'source': Mode.PLAYING,
        'dest': Mode.LOCKED,
        'after': '_report_playing_completed',
    },
    {
        'trigger': 'play_next',
        'source': Mode.PLAYING,
        'dest': '=',
        'after': '_play_next',
    },
    # source: error
    {
        'trigger': 'reset',
        'source': Mode.ERROR,
        'dest': Mode.LOCKED,
        'before': '_setup',
        'after': '_report_reset_completed',
    },
    # <> cancel playing
    # <> error
    {
        'trigger': 'error',
        'source': [Mode.ADJUSTING, Mode.PLAYING],
        'dest': Mode.ERROR,
        'after': '_report_error',
    },
]


class RobotModel:
    def __init__(self):
        # initialize the recorded waypoints
        self.waypoints = dict()
        # inititalize the current step index
        self.current_step = 0
        # store the trigger mapping
        self.trigger_map = dict()

    async def _ask_deletion(self):
        await self.speak(f"Confirm Deleting Step {self.current_step - 1}")

    async def _ask_playing(self):
        await self.speak(f"Confirm Playing {len(self.waypoints)} steps")

    def _delete_waypoint(self):
        self.current_step -= 1
        self.waypoints.pop(self.current_step)

    def _has_current_step(self):
        return self.current_step in self.waypoints

    def _has_next_step(self):
        next_step = self.current_step + 1
        return next_step in self.waypoints and self.waypoints[next_step]

    def _has_previous_step(self):
        prev = self.current_step - 1
        return prev >= 0 and prev in self.waypoints and self.waypoints[prev]

    def _has_valid_waypoints(self):
        return len(self.waypoints) > 0 and all(self.waypoints.values())

    async def _move_to_next(self):
        self.current_step += 1
        await self.move()

    async def _move_to_previous(self):
        self.current_step -= 1
        await self.move()

    async def _play_next(self):
        if self._has_next_step():
            await self._move_to_next()
        else:
            await self.finish_playing()

    async def _play(self):
        await self.speak("Playing waypoints")
        self.current_step = 0
        await self.move()

    async def _report_adjusting_completed(self):
        await self.speak("Adjusting completed")
        await self.finish_adjusting()

    async def _report_cancel_adjusting(self):
        await self.speak("Cancelled adjusting")

    async def _report_cancel_deletion(self):
        await self.speak("Cancelled deletion")

    async def _report_cancel_playing(self):
        await self.speak("Cancelled playing")

    async def _report_cancel_teaching(self):
        await self.speak("Cancelled teaching")

    async def _report_confirm_deletion(self):
        await self.speak("Deleted the Waypoint")

    async def _report_confirm_waypoint(self):
        await self.speak("Recorded the Waipoint")

    async def _report_error(self):
        await self.speak("Error detected. Please reset.")

    async def _report_playing_completed(self):
        await self.speak("Finished playing waypoints")

    async def _report_reset_completed(self):
        await self.speak("Reset Completed")

    async def _report_setup_completed(self):
        await self.speak("Setup Completed")

    async def _report_unlocked(self):
        await self.speak("Teaching Mode")

    async def _save_waypoint(self):
        self.waypoints[self.current_step] = await self.get_pose()
        self.current_step += 1

    async def _setup(self):
        self.__init__()

    async def disable_free_drive(self):
        """this method needs to be implemented per robot"""
        raise NotImplementedError()

    async def enable_free_drive(self):
        """this method needs to be implemented per robot"""
        raise NotImplementedError()

    async def get_pose(self):
        """this method needs to be implemented per robot"""
        raise NotImplementedError()

    async def move(self):
        """this method needs to be implemented per robot"""
        raise NotImplementedError()

    async def speak(self, text):
        """this method needs to be implemented per robot"""
        raise NotImplementedError()


class AsyncRobot(RobotModel):
    def __init__(self):
        super().__init__()
        self.machine = AsyncMachine(
            model=self,
            states=Mode,
            transitions=Transitions,
            initial=Mode.INIT,
            queued=True,
        )


class TalkingRobot(AsyncRobot):
    def __init__(self):
        super().__init__()

    async def disable_free_drive(self):
        await asyncio.sleep(0.1)

    async def enable_free_drive(self):
        await asyncio.sleep(0.1)

    async def get_pose(self):
        await asyncio.sleep(0.1)
        return 1

    async def move(self):
        await asyncio.sleep(0.5)

    async def speak(self, text):
        if text != "":
            await asyncio.create_subprocess_exec("say", text)


class Lite6(AsyncRobot):
    def __init__(self):
        pass


class XArm7(AsyncRobot):
    def __init__(self, ee=None):
        self.end_effector = ee
        if self.end_effector:
            # self.machine.add_transition("open", ...)
            pass


class Gripper(AsyncRobot):
    def __init__(self):
        # rospy.wait_for_service("/xarm/set_load")
        # setload = rospy.ServiceProxy("/xarm/set_load", SetLoad)
        # responseSetLoad = setload(0.82,0,0,48)
        self.load = (0.82, 0, 0, 48)
        # rospy.wait_for_service("/xarm/gripper_config")
        # gripper_config = rospy.ServiceProxy("/xarm/gripper_config", GripperConfig)
        # responseGripperConfig = gripper_config(speed)
        self.speed = 1500
        pass

    async def move(self):
        """
        move
        position:
            - 0: close
            - 620: grab
            - 850: open
        """
        # rospy.wait_for_service("/xarm/gripper_move")
        # gripper_move = rospy.ServiceProxy("/xarm/gripper_move", GripperMove)
        # responseGripperMove = gripper_move(position)
