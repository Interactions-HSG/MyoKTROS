# -*- coding: utf-8 -*-
import logging

from .mode import Mode


# Global Variables to keep track of the gripper state,the robot mode, delete position and finish teaching
class RosObject:
    def __init__(self):
        # rospy.init_node('listener', anonymous=True)
        # rospy.set_param('/xarm/wait_for_finish', True)
        pass

    def clear(self):
        # rospy.wait_for_service('/xarm/clear_err')
        # err = rospy.ServiceProxy('/xarm/clear_err', ClearErr)
        # if err:
        #    logging.debug(err)
        pass


class XArm7(RosObject):
    def __init__(self):
        super().__init__()
        # TODO
        self.gripper = Gripper()
        self.gripper.set_load()
        self.gripper.set_speed(1500)
        self.current_mode = None
        self.set_mode(Mode.STANDARD_MODE)
        self.trajectory = []

    def set_mode(self, mode):
        """
        set_mode(mode: MODE)
        mode:
            - 0: STANDARD_MODE
            - 2: TEACH_MODE
        """
        self.current_mode = mode
        # TODO: convert to aac
        # playsound ('assets/standard_mode.mp3')
        # playsound('assets/teach_mode.mp3')

        # rospy.wait_for_service('/xarm/set_mode')

        # set_mode_client(2) ??

        # set_mode = rospy.ServiceProxy('/xarm/set_mode', SetInt16)

        # rospy.wait_for_service('/xarm/set_state')
        # set_state = rospy.ServiceProxy('/xarm/set_state', SetInt16)

        # set_mode(mode)
        # set_state(0)
        logging.info(f"{self.name} in {self.mode.name}")  # pyright: ignore

    def home(self):
        if self.current_mode != Mode.STANDARD_MODE:
            self.set_mode(Mode.STANDARD_MODE)

        # Modified home position for gripper
        # rospy.wait_for_service('/xarm/move_joint')
        # go_home = rospy.ServiceProxy('/xarm/move_joint', Move)

        # responseGoHome = go_home([0,0,0,0,0,-1.562,0], 0.7, 7, 0, 0)
        # responseGoHome()

    def joint(self, position):
        if self.current_mode != Mode.STANDARD_MODE:
            self.set_mode(Mode.STANDARD_MODE)

        # rospy.wait_for_service('/xarm/move_joint')
        # move_joint = rospy.ServiceProxy('/xarm/move_joint', Move)

        # responseMoveJoint = move_joint(position, 0.7, 7, 0, 0)
        # responseMoveJoint()

    def execute(self):
        self.home()
        # self.set_gripper(GripperState.HOME)

        # for j in range(3):
        #    for i in range(len(positions)):
        #        sleep(0.5)
        #        move_joints(positions[i])
        #        gripper_action(gripper_states[i])
        # sleep(0.5)
        # return_home()
        # home_gripper()

    # confirm Function and delete position
    def record(self):
        # statenow = rospy.wait_for_message("/xarm/xarm_states", RobotMsg)
        # state = statenow.angle
        # self.positions.append(state)
        # self.gripper_state.append(gripper_state)
        # feedback
        # print 'Position confirmed'
        # playsound('assets/position_confirmed.mp3')
        pass

    # delete the last confirmed position
    def undo(self):
        """
        if len(positions) > 0:
            del positions[-1]
            del gripper_states[-1]
            #feedback
            print "Position deleted"
            playsound('assets/position_deleted.mp3')
        """
        pass


class Gripper(RosObject):
    def __init__(self):
        pass

    def move(self, position):
        """
        move
        position:
            - 0: reset
            - 620: grab
            - 850: release
        """
        # rospy.wait_for_service('/xarm/gripper_move')
        # gripper_move = rospy.ServiceProxy('/xarm/gripper_move', GripperMove)
        # responseGripperMove = gripper_move(position)
        # responseGripperMove()
        pass

    def set_load(self):
        # rospy.wait_for_service('/xarm/set_load')
        # setload = rospy.ServiceProxy('/xarm/set_load', SetLoad)
        # responseSetLoad = setload(0.82,0,0,48)
        # responseSetLoad()
        pass

    def set_speed(self, speed):
        # rospy.wait_for_service('/xarm/gripper_config')
        # gripper_config = rospy.ServiceProxy('/xarm/gripper_config', GripperConfig)
        # responseGripperConfig = gripper_config(speed)
        # responseGripperConfig()
        pass

    def toggle(self):
        pass
