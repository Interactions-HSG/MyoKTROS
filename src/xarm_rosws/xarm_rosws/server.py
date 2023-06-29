import argparse
import asyncio
import json
import logging

import rclpy
from websockets.server import serve

from .clean_gripper_error import CleanGripperErrorClient
from .close_lite6_gripper import CloseLite6GripperClient
from .get_servo_angle import GetServoAngleClient
from .motion_enable import MotionEnableClient
from .move_gohome import MoveGohomeClient
from .open_lite6_gripper import OpenLite6GripperClient
from .set_gripper_enable import SetGripperEnableClient
from .set_gripper_mode import SetGripperModeClient
from .set_gripper_position import SetGripperPositionClient
from .set_gripper_speed import SetGripperSpeedClient
from .set_mode import SetModeClient
from .set_position import SetPositionClient
from .set_servo_angle import SetServoAngleClient
from .set_state import SetStateClient
from .set_vacuum_gripper import SetVacuumGripperClient
from .stop_lite6_gripper import StopLite6GripperClient

CONNECTIONS = set()


class API:
    @classmethod
    def clean_gripper_error(cls, params={}):
        c = CleanGripperErrorClient()
        response = c.send_request()
        c.get_logger().info(f"xarm_rosws:/ufactory/clean_gripper_error: {response}")
        c.destroy_node()
        return response

    @classmethod
    def close_lite6_gripper(cls, params={}):
        c = CloseLite6GripperClient()
        response = c.send_request()
        c.get_logger().info(f"xarm_rosws:/ufactory/close_lite6_gripper: {response}")
        c.destroy_node()
        return response

    @classmethod
    def get_servo_angle(cls, params={}):
        c = GetServoAngleClient()
        response = c.send_request()
        c.get_logger().info(f"xarm_rosws:/ufactory/get_servo_angle: {response}")
        c.destroy_node()
        return response

    @classmethod
    def motion_enable(cls, params={}):
        id = 8 if "id" not in params else params["id"]
        data = 1 if "data" not in params else params["data"]
        c = MotionEnableClient()
        response = c.send_request(id, data)
        c.get_logger().info(f"xarm_rosws:/ufactory/motion_enable: {response}")
        c.destroy_node()
        return response

    @classmethod
    def move_gohome(cls, params={}):
        speed = 0.35 if "speed" not in params else params["speed"]
        acc = 10.0 if "acc" not in params else params["acc"]
        mvtime = 0.0 if "mvtime" not in params else params["mvtime"]
        c = MoveGohomeClient()
        response = c.send_request(speed, acc, mvtime)
        c.get_logger().info(f"xarm_rosws:/ufactory/move_gohome: {response}")
        c.destroy_node()
        return response

    @classmethod
    def open_lite6_gripper(cls, params={}):
        c = OpenLite6GripperClient()
        response = c.send_request()
        c.get_logger().info(f"xarm_rosws:/ufactory/open_lite6_gripper: {response}")
        c.destroy_node()
        return response

    @classmethod
    def set_gripper_enable(cls, params={}):
        data = 0 if "data" not in params else params["data"]
        c = SetGripperEnableClient()
        response = c.send_request(data)
        c.get_logger().info(f"xarm_rosws:/ufactory/set_gripper_enable: {response}")
        c.destroy_node()
        return response

    @classmethod
    def set_gripper_mode(cls, params={}):
        data = 0 if "data" not in params else params["data"]
        c = SetGripperModeClient()
        response = c.send_request(data)
        c.get_logger().info(f"xarm_rosws:/ufactory/set_gripper_mode: {response}")
        c.destroy_node()
        return response

    @classmethod
    def set_gripper_position(cls, params={}):
        pos = 0.0 if "pos" not in params else params["pos"]
        wait = False if "wait" not in params else params["wait"]
        timeout = 10 if "timeout" not in params else params["timeout"]
        c = SetGripperPositionClient()
        response = c.send_request(pos, wait, timeout)
        c.get_logger().info(f"xarm_rosws:/ufactory/set_gripper_position: {response}")
        c.destroy_node()
        return response

    @classmethod
    def set_gripper_speed(cls, params={}):
        data = 50.0 if "data" not in params else params["data"]
        c = SetGripperSpeedClient()
        response = c.send_request(data)
        c.get_logger().info(f"xarm_rosws:/ufactory/set_gripper_speed: {response}")
        c.destroy_node()
        return response

    @classmethod
    def set_mode(cls, params={}):
        data = 0 if "data" not in params else params["data"]
        c = SetModeClient()
        response = c.send_request(data)
        c.get_logger().info(f"xarm_rosws:/ufactory/set_mode: {response}")
        c.destroy_node()
        return response

    @classmethod
    def set_position(cls, params={}):
        pose = [250.0, 0.0, 250.0, 3.14, 0.0, 0.0] if "pose" not in params else params["pose"]
        speed = 50.0 if "speed" not in params else params["speed"]
        acc = 500.0 if "acc" not in params else params["acc"]
        mvtime = 0.0 if "mvtime" not in params else params["mvtime"]

        c = SetPositionClient()
        response = c.send_request(pose, speed, acc, mvtime)
        c.get_logger().info(f"xarm_rosws:/ufactory/set_position: {response}")
        c.destroy_node()
        return response

    @classmethod
    def set_servo_angle(cls, params={}):
        angles = [-0.58, 0.0, 0.0, 0.0, 0.0, 0.0] if "angles" not in params else params["angles"]
        speed = 0.35 if "speed" not in params else params["speed"]
        acc = 10.0 if "acc" not in params else params["acc"]
        mvtime = 0.0 if "mvtime" not in params else params["mvtime"]

        c = SetServoAngleClient()
        response = c.send_request(angles, speed, acc, mvtime)
        c.get_logger().info(f"xarm_rosws:/ufactory/set_servo_angle: {response}")
        c.destroy_node()
        return response

    @classmethod
    def set_state(cls, params={}):
        data = 0 if "data" not in params else params["data"]
        c = SetStateClient()
        response = c.send_request(data)
        c.get_logger().info(f"xarm_rosws:/ufactory/set_mode: {response}")
        c.destroy_node()
        return response

    @classmethod
    def set_vacuum_gripper(cls, params={}):
        on = True if "on" not in params else params["on"]
        wait = False if "wait" not in params else params["wait"]
        timeout = 3.0 if "timeout" not in params else params["timeout"]
        delay_sec = 0.0 if "delay_sec" not in params else params["delay_sec"]
        c = SetVacuumGripperClient()
        response = c.send_request(on, wait, timeout, delay_sec)
        c.get_logger().info(f"xarm_rosws:/ufactory/set_vacuum_gripper: {response}")
        c.destroy_node()
        return response

    @classmethod
    def stop_lite6_gripper(cls, params={}):
        c = StopLite6GripperClient()
        response = c.send_request()
        c.get_logger().info(f"xarm_rosws:/ufactory/stop_lite6_gripper: {response}")
        c.destroy_node()
        return response


async def register(websocket):
    global CONNECTIONS

    # only accept one client at a time
    if len(CONNECTIONS) > 0:
        return
    try:
        # Register the client
        CONNECTIONS.add(websocket)
        # Manage state changes
        async for message in websocket:
            payload = json.loads(message)
            service = payload["service"]
            if hasattr(API, service):
                call = getattr(API, service)
                logging.info(f"{service}, {payload}")
                response = call(payload["params"])
                if service == "get_servo_angle":
                    # for get_servo_angle, it returns 7 elements instead of 6
                    await websocket.send(json.dumps({"angles": list(response.datas)[:-1]}))
                else:
                    await websocket.send(str(response))
            else:
                await websocket.send(f"Unsupported payload: {payload}")
                logging.error(f"Unsupported payload: {payload}")
        await websocket.wait_closed()
    finally:
        # Unregister the client
        CONNECTIONS.remove(websocket)


async def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="xarm_rosws: ros2 xarm_api via websocket",
    )
    parser.add_argument(
        "--ip",
        help="IP address for websocket server",
        default="0.0.0.0",
    )
    parser.add_argument(
        "--port",
        help="port for websockert listener",
        default=8765,
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logging.info("starting xarm_rosws")

    # init rclpy
    rclpy.init()
    # setup the robot
    logging.info("xarm_rosws:/ufactory/enable_motion {'id': 8, 'data': 1}")
    API.motion_enable()
    logging.info("xarm_rosws:/ufactory/set_mode {'data': 0}")
    API.set_mode()
    logging.info("xarm_rosws:/ufactory/set_state {'data': 0}")
    API.set_state()

    async with serve(register, args.ip, args.port):
        await asyncio.Future()

    # shutdown rclpy
    rclpy.shutdown()


def run():
    asyncio.run(main())
