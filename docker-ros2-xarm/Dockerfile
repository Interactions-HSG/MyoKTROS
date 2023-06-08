FROM ros:humble

ENV ROS_DISTRO=humble

# checkout
WORKDIR /app/src
RUN git clone https://github.com/xArm-Developer/xarm_ros2.git --recursive -b ${ROS_DISTRO}

# update
WORKDIR /app/src/xarm_ros2
RUN git submodule sync && git submodule update --init --remote

# install requirements
# https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html#setup-sources
RUN apt-get update \
    && apt-get install -y software-properties-common \
    && add-apt-repository universe \
    && apt-get update

# install moveit2
RUN apt-get install -y "ros-${ROS_DISTRO}-moveit"

# install gazebo
RUN curl -sSL http://get.gazebosim.org | sh

# install gazebo_ros_pkgs
RUN apt-get install -y "ros-${ROS_DISTRO}-gazebo-ros-pkgs"

# install ros dependencies
WORKDIR /app/src
RUN rosdep update
RUN rosdep install --from-paths . --ignore-src --rosdistro ${ROS_DISTRO} -y

# build
WORKDIR /app
SHELL ["/bin/bash", "-c"]
RUN source "/opt/ros/$ROS_DISTRO/setup.bash" && colcon build

COPY entrypoint.sh /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["bash"]
