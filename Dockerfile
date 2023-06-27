FROM ghcr.io/iomz/ros2-xarm:humble

WORKDIR /app
COPY src/ufactory_xarm_api /app/src/ufactory_xarm_api

RUN colcon build

RUN echo "source /app/install/setup.bash" | tee -a /root/.bashrc
