# docker-ros2-xarm

All-in-one image for [xArm-Developer/xarm_ros2:humle](https://github.com/xArm-Developer/xarm_ros2/tree/humble).

## Build

```bash
docker build -t ros2-xarm -f Dockerfile .
```

## Run

```bash
docker run --rm -it ros2-xarm
> ros2 launch xarm_api xarm6_driver.launch.py robot_ip:=10.2.2.200
```
