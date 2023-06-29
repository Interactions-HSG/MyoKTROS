#!/usr/bin/env python3
"""dl-myo example ws_client.py"""

import argparse
import asyncio
import json
import readline  # noqa

import websockets


async def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="xarm_ros2 websocket client",
    )
    parser.add_argument(
        "service",
        help="the service to call",
        type=str,
    )
    parser.add_argument(
        "--ip",
        help="the host IP address for websocket server",
        default="127.0.0.1",
    )
    parser.add_argument(
        "--port",
        help="the port for websocket server",
        default=8765,
    )

    args = parser.parse_args()

    uri = f"ws://{args.ip}:{args.port}"
    async with websockets.connect(uri) as websocket:
        service = args.service
        if service == "quit":
            return
        elif service == "vacuum_on":
            payload = json.dumps({"service": "set_vacuum_gripper", "params": {"on": True}})
            await websocket.send(payload)
            response = await websocket.recv()
            print(response)
        elif service == "vacuum_off":
            payload = json.dumps({"service": "set_vacuum_gripper", "params": {"on": False}})
            await websocket.send(payload)
            response = await websocket.recv()
            print(response)
        elif service == "teach_mode":
            payload = json.dumps({"service": "set_mode", "params": {"data": 2}})
            await websocket.send(payload)
            response = await websocket.recv()
            print(response)
            payload = json.dumps({"service": "set_state", "params": {"data": 0}})
            await websocket.send(payload)
            response = await websocket.recv()
            print(response)
        elif service == "lock_mode":
            payload = json.dumps({"service": "set_mode", "params": {"data": 0}})
            await websocket.send(payload)
            response = await websocket.recv()
            print(response)
            payload = json.dumps({"service": "set_mode", "params": {"data": 0}})
            await websocket.send(payload)
            response = await websocket.recv()
            print(response)
        else:
            payload = json.dumps({"service": service, "params": {}})
            print(f"<<< {payload}")
            await websocket.send(payload)
            response = await websocket.recv()
            print(response)


if __name__ == "__main__":
    asyncio.run(main())
