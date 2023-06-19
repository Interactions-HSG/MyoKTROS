# -*- coding: utf-8 -*-
import logging

from enum import Enum
from transitions.extensions.asyncio import AsyncMachine

logger = logging.getLogger(__name__)


class Mode(Enum):
    INIT = 0
    LOCKED = 1
    UNLOCKED = 2
    PENDING_DELETION = 10
    PENDING_PLAY_ONCE = 11
    PENDING_PLAY_REPEAT = 12
    ADJUSTING = 20
    PLAYING_ONCE = 21
    PLAYING_REPEAT = 22
    ERROR = -1


class Robot:
    transitions = [
        {
            'trigger': 'cancel',
            'source': Mode.PENDING_DELETION,
            'dest': Mode.LOCKED,
            'before': '_report_cancel_deletion',
        },
        {
            'trigger': 'cancel',
            'source': [
                Mode.PENDING_PLAY_ONCE,
                Mode.PENDING_PLAY_REPEAT,
                Mode.PLAYING_ONCE,
                Mode.PLAYING_REPEAT,
            ],
            'dest': Mode.LOCKED,
            'before': '_report_cancel_playing',
        },
        {
            'trigger': 'cancel',
            'source': Mode.UNLOCKED,
            'dest': Mode.LOCKED,
            'before': '_report_cancel_teaching',
            'after': 'disable_free_drive',
        },
        {
            'trigger': 'confirm',
            'source': Mode.PENDING_DELETION,
            'dest': Mode.LOCKED,
            'conditions': '_has_current_step',
            'before': '_report_confirm_deletion',
            'after': '_delete_waypoint',
        },
        {
            'trigger': 'confirm',
            'source': Mode.PENDING_PLAY_ONCE,
            'dest': Mode.PLAYING_ONCE,
            'before': '_report_confirm_play_once',
        },
        {
            'trigger': 'confirm',
            'source': Mode.PENDING_PLAY_REPEAT,
            'dest': Mode.PLAYING_REPEAT,
            'before': '_report_confirm_play_repeat',
        },
        {
            'trigger': 'confirm',
            'source': Mode.UNLOCKED,
            'dest': Mode.LOCKED,
            'before': '_report_confirm_waypoint',
            'after': ['_save_waypoint', 'disable_free_drive'],
        },
        {
            'trigger': 'grabbed',
            'source': Mode.LOCKED,
            'dest': Mode.UNLOCKED,
            'before': '_report_unlocked',
            'after': 'enable_free_drive',
        },
        {
            'trigger': 'delete',
            'source': Mode.LOCKED,
            'dest': Mode.PENDING_DELETION,
            'conditions': '_has_current_step',
            'after': '_ask_deletion',
        },
        {
            'trigger': 'setup',
            'source': Mode.INIT,
            'dest': Mode.LOCKED,
            'before': '_setup',
            'after': '_report_setup_completed',
        },
        {
            'trigger': 'previous',
            'source': Mode.LOCKED,
            'dest': Mode.ADJUSTING,
            'conditions': '_has_previous_step',
            'before': '_report_move_to_previous',
            'after': '_move_to_previous',
        },
        {
            'trigger': 'next',
            'source': Mode.LOCKED,
            'dest': Mode.ADJUSTING,
            'conditions': '_has_next_step',
            'before': '_report_move_to_next',
            'after': '_move_to_next',
        },
        {
            'trigger': 'finish_adjusting',
            'source': Mode.ADJUSTING,
            'dest': Mode.LOCKED,
        },
        {
            'trigger': 'finish_playing_once',
            'source': Mode.PLAYING_ONCE,
            'dest': Mode.LOCKED,
            'after': '_report_playing_once_completed',
        },
        {
            'trigger': 'play_once',
            'source': Mode.LOCKED,
            'dest': Mode.PENDING_PLAY_ONCE,
            'after': '_ask_play_once',
        },
        {
            'trigger': 'play_repeat',
            'source': Mode.LOCKED,
            'dest': Mode.PENDING_PLAY_REPEAT,
            'after': '_ask_play_repeat',
        },
        {
            'trigger': 'reset',
            'source': Mode.ERROR,
            'dest': Mode.LOCKED,
            'before': '_setup',
            'after': '_report_reset_completed',
        },
        {
            'trigger': 'error',
            'source': [Mode.PLAYING_ONCE, Mode.PLAYING_REPEAT],
            'dest': Mode.ERROR,
            'after': '_report_error',
        },
    ]

    def __init__(self):
        self.machine = AsyncMachine(
            model=self,
            states=Mode,
            transitions=Robot.transitions,
            initial=Mode.INIT,
            queued=True,
        )
        # initialize the recorded waypoints
        self.waypoints = dict()
        # inititalize the current step index
        self.current_step = 0

    async def _ask_deletion(self):
        await self.speak("Do you want to delete the current step?")

    async def _ask_play_once(self):
        await self.speak("Do you want to play the recorded waypoints once?")

    async def _ask_play_repeat(self):
        await self.speak("Do you want to repeat playing the recorded waypoints?")

    def _delete_waypoint(self):
        self.waypoints.pop(self.current_step)

    def _has_current_step(self):
        return self.current_step in self.waypoints

    def _has_next_step(self):
        next_step = self.current_step + 1
        return next_step in self.waypoints and self.waypoints[next_step]

    def _has_previous_step(self):
        prev_step = self.current_step - 1
        return prev_step in self.waypoints and self.waypoints[prev_step]

    async def _move_to_next(self):
        self.current_step += 1
        await self.move()
        self.finish_adjusting()

    async def _move_to_previous(self):
        self.current_step -= 1
        await self.move()
        self.finish_adjusting()

    async def _report_cancel_deletion(self):
        await self.speak("Waypoint deletion cancelled.")

    async def _report_cancel_playing(self):
        await self.speak("Playing waypoints cancelled.")

    async def _report_cancel_teaching(self):
        await self.speak("Recording cancelled.")

    async def _report_confirm_deletion(self):
        await self.speak("Waypoint deleted.")

    async def _report_confirm_play_once(self):
        await self.speak("Playing waypoints once.")

    async def _report_confirm_play_repeat(self):
        await self.speak("Repeat playing waypoints.")

    async def _report_confirm_waypoint(self):
        await self.speak("Waipoint recorded.")

    async def _report_error(self):
        await self.speak("Error detected. Please reset.")

    async def _report_move_to_next(self):
        await self.speak("Moving to the next waypoint.")

    async def _report_move_to_previous(self):
        await self.speak("Moving to the previous waypoint.")

    async def _report_playing_once_completed(self):
        await self.speak("Finished playing waypoints.")

    async def _report_reset_completed(self):
        await self.speak("Reset completed.")

    async def _report_setup_completed(self):
        await self.speak("Setup completed.")

    async def _report_unlocked(self):
        await self.speak("Robot unlocked.")

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


class Lite6(Robot):
    def __init__(self):
        super().__init__()


class XArm7(Robot):
    def __init__(self):
        super().__init__()
        self.gripper = Gripper()
        self.current_mode = None


class Gripper(Robot):
    def __init__(self):
        super().__init__()
        # responseSetLoad = setload(0.82,0,0,48)
        self.load = 0.82
        # rospy.wait_for_service('/xarm/gripper_config')
        # gripper_config = rospy.ServiceProxy('/xarm/gripper_config', GripperConfig)
        # responseGripperConfig = gripper_config(speed)
        self.speed = 1500
        pass

    async def close(self):
        """
        move
        position:
            - 0: reset
            - 620: grab
            - 850: release
        """

    async def open(self):
        """
        move
        position:
            - 0: reset
            - 620: grab
            - 850: release
        """
