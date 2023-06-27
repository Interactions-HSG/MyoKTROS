FROM ghcr.io/iomz/ros2-xarm:humble

WORKDIR /app

RUN source /build/xarm_ros2/install/setup.bash \
    && apt-get install -y python3-pip \
    && pip install setuptools==58.2.0 websockets

COPY . /app/src/xarm_ws/

RUN source /build/xarm_ros2/install/setup.bash \
    && rosdep install -i --from-path src --rosdistro humble -y \
    && colcon build

COPY entrypoint.sh entrypoint.sh

EXPOSE 8765

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/app/run"]
