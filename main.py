#!/usr/bin/env python

#Modules for ROS
import rospy, rosservice
from xarm_msgs.srv import SetInt16, Move, GripperConfig, GripperMove, SetLoad, ClearErr
from xarm_msgs.msg import RobotMsg
from time import sleep

#Modules for Classifier
import joblib
import numpy as np

#Modules for Socket connection
from socket import socket, timeout, AF_INET, SOCK_STREAM
from sys import stdout

#for input
import keyboard
from playsound import playsound


#Global Variables to keep track of the gripper state,the robot mode, delete position and finish teaching
gripper_state=1
robot_mode = 0
delete_position = 0
finish = 0

#Clear Error on the xArm
def clear_error():
    rospy.wait_for_service('/xarm/clear_err')
    clear_err = rospy.ServiceProxy('/xarm/clear_err', ClearErr)

    print clear_err()

#xArm Mode and State Functions

def standard_mode():
    set_mode_client(0)
    global robot_mode
    robot_mode = 0
    #feedack
    print 'Xarm in Standard Mode'
    playsound ('assets/standard_mode.mp3')


def teach_mode():
    set_mode_client(2)
    global robot_mode
    robot_mode = 1
    #feedback
    print 'Xarm in Teach Mode'
    playsound('assets/teach_mode.mp3')


def set_mode_client(new_mode):
    rospy.wait_for_service('/xarm/set_mode')
    set_mode = rospy.ServiceProxy('/xarm/set_mode', SetInt16)

    rospy.wait_for_service('/xarm/set_state')
    set_state = rospy.ServiceProxy('/xarm/set_state', SetInt16)

    print set_mode(new_mode)
    print set_state(0)

#xArm move Functions
def return_home():

    global robot_mode
    if robot_mode != 0:
        standard_mode()
    #Modified home position for gripper
    rospy.wait_for_service('/xarm/move_joint')
    go_home = rospy.ServiceProxy('/xarm/move_joint', Move)

    responseGoHome = go_home([0,0,0,0,0,-1.562,0], 0.7, 7, 0, 0)
    print responseGoHome


def move_joints(position):

    global robot_mode
    if robot_mode != 0:
        standard_mode()
    rospy.wait_for_service('/xarm/move_joint')
    move_joint = rospy.ServiceProxy('/xarm/move_joint', Move)

    responseMoveJoint = move_joint(position, 0.7, 7, 0, 0)
    print responseMoveJoint

def move_sequence(positions):
    return_home()
    home_gripper()

    for j in range(3):
        for i in range(len(positions)):
            sleep(0.5)
            move_joints(positions[i])
            gripper_action(gripper_states[i])
    sleep(0.5)
    return_home()
    home_gripper()

#Confirm Function and delete position
def confirm_pos():
    statenow = rospy.wait_for_message("/xarm/xarm_states", RobotMsg)
    state = statenow.angle
    positions.append(state)
    global gripper_state
    gripper_states.append(gripper_state)
    #feedback
    print 'Position confirmed'
    playsound('assets/position_confirmed.mp3')

#delete the last confirmed position
def delete_pos():
    if len(positions) > 0:
        del positions[-1]
        del gripper_states[-1]
        #feedback
        print "Position deleted"
        playsound('assets/position_deleted.mp3')

#recognize keyboard input to delete a position or to break the loop and finish training
def key_input(key):
    print key.name
    if key.name == 'shift':
        global delete_position
        delete_position = 1
    if key.name == 'enter':
        global finish
        finish = 1

#Gripper Functions

def set_load():
    rospy.wait_for_service('/xarm/set_load')
    setload = rospy.ServiceProxy('/xarm/set_load', SetLoad)
    responseSetLoad = setload(0.82,0,0,48)
    print responseSetLoad

def config_gripper(speed):
    rospy.wait_for_service('/xarm/gripper_config')
    gripper_config = rospy.ServiceProxy('/xarm/gripper_config', GripperConfig)
    responseGripperConfig = gripper_config(speed)
    print responseGripperConfig

def move_gripper(position):
    rospy.wait_for_service('/xarm/gripper_move')
    gripper_move = rospy.ServiceProxy('/xarm/gripper_move', GripperMove)
    responseGripperMove = gripper_move(position)
    print responseGripperMove

def open_gripper():
    move_gripper(850)
    global gripper_state
    gripper_state = 0

def close_gripper():
    move_gripper(620)
    global gripper_state
    gripper_state = 1

def home_gripper():
    move_gripper(0)

def gripper_action(x):
    if (x == 0):
        open_gripper()
    elif (x == 1):
        close_gripper()


#Function to receive EMG Signals (by Iori)
def receive_emg_data(sock):
    data = bytes()
    try:
        while b"\r\n" not in data:
            chunk = sock.recv(1) # receive byte-by-byte
            if not chunk:
                break
            else:
                data += chunk
    except timeout:
        pass
    d = data.split()
    if len(d) == 18:
        d1 = " ".join([str(int(i)) for i in d[1:17]])
        arr = [int(s) for s in d1.split(' ')]
    return arr



if __name__ == '__main__':

    #Set up connection to Myo EMG Stream
    MYO_APP_IP = '10.2.1.31'
    MYO_APP_PORT = 5678
    s = socket(AF_INET, SOCK_STREAM)
    s.connect((MYO_APP_IP, MYO_APP_PORT))

    #Load the classifier
    knn = joblib.load('Classifier.pkl')

    #Initialize ROS node and set params
    rospy.init_node('listener', anonymous=True)
    rospy.set_param('/xarm/wait_for_finish', True)

    #Clear Errors
    clear_error()

    #Empty lists to save the positions and gripper states in
    positions = []
    gripper_states = []
    #Control variable so that a function is not executed twice in a row
    cont = 0
    #Control variables so that a position can only be confirmed if position or gripper state has been changed
    taught = 0
    gripped = 0

    #Set TCP Payload for the Gripper
    set_load()

    #Enable amd configurate Gripper
    config_gripper(1500)


    #Set robot to standard mode
    standard_mode()

    #3 consecutive predictions (for teach and standard mode onlz 2/3 have to be correct)
    pred = [0,0,0]

    #activate keyboard input
    keyboard.on_press(key_input)

    #This is the main loop features are received and classified
    while True:

        for j in range(3):
            arr = receive_emg_data(s)
            datanew = np.array(arr)
            data = datanew.reshape(1, -1)
            pred[j] = knn.predict(data)[0]



        #Standard Mode
        if (pred[0] == 0 and (pred[0]==pred[1] or pred[0]==pred[2]) and robot_mode != 0):
            cont = 0
            standard_mode()

        #Teach mode
        elif (pred[0] == 1 and (pred[0]==pred[1] or pred[0]==pred[2]) and robot_mode != 1):
            cont = 1
            taught = 1
            teach_mode()

       #Confirm Position
        elif (pred[0] == 2 and pred[0]==pred[1]==pred[2] and pred[0] != cont and robot_mode == 0 and (taught == 1 or gripped == 1)):
            cont = 2
            taught = 0
            gripped = 0
            confirm_pos()
            #I had this in there to disable two sequential confirmations, but it is redundant now, and taking it out would prob. improve the response time
            sleep(1)

        #Open or Close Gripper
        elif (pred[0] == 3 and pred[0]==pred[1]==pred[2] and pred[0] != cont and robot_mode == 0):
            cont = 3
            gripped = 1
            if (gripper_state == 1):
                open_gripper()
            elif (gripper_state == 0):
                close_gripper()

        #Delete the last confirmed position
        elif (delete_position == 1):
            delete_pos()
            delete_position = 0


        #Finish Teaching
        elif (finish == 1):
            break

        else:
            pass

    print "Sequence will now be executed"
    move_sequence(positions)

