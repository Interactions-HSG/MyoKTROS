# MyoKTROS

[![build](https://github.com/Interactions-HSG/MyoKTROS/workflows/build/badge.svg)](https://github.com/Interactions-HSG/MyoKTROS/actions?query=workflow%3Abuild)
[![codecov](https://codecov.io/gh/Interactions-HSG/MyoKTROS/branch/main/graph/badge.svg?token=H8OT1FM4SG)](https://codecov.io/gh/Interactions-HSG/MyoKTROS)
[![python versions](https://img.shields.io/pypi/pyversions/myoktros.svg)](https://pypi.python.org/pypi/myoktros)
[![pypi version](https://img.shields.io/pypi/v/myoktros.svg)](https://pypi.python.org/pypi/myoktros)
[![license](https://img.shields.io/pypi/l/myoktros.svg)](https://pypi.python.org/pypi/myoktros)

Myo EMG-based KT system with, but not limited to, ROS.

MyoKTROS directly communicates with a Myo Armband via [dl-myo](https://github.com/iomz/dl-myo).

<!-- vim-markdown-toc GFM -->

- [Installation](#installation)
  - [PIP](#pip)
  - [Build and install with Poetry](#build-and-install-with-poetry)
- [Usage](#usage)
  - [Configuration](#configuration)
  - [Gesture Model Calibration](#gesture-model-calibration)
  - [Connecting MyoKTROS to a robot](#connecting-myoktros-to-a-robot)
    - [UFACTORY](#ufactory)
      - [xarm_ros2](#xarm_ros2)
      - [WebSocket API](#websocket-api)
- [Visualizing the State Machine](#visualizing-the-state-machine)
  - [WebMachine](#webmachine)
  - [GraphMachine](#graphmachine)
- [Gestures](#gestures)
  - [REST](#rest)
  - [GRAB](#grab)
  - [STRETCH_FINGERS](#stretch_fingers)
  - [EXTENSION](#extension)
  - [FLEXION](#flexion)
  - [HORN](#horn)
  - [FLEMING](#fleming)
  - [THUMBS_UP](#thumbs_up)
  - [SHOOT](#shoot)
  - [TENNET](#tennet)
- [Myo](#myo)
- [Authors](#authors)

<!-- vim-markdown-toc -->

## Installation

### PIP

```bash
pip install -U myoktros
```

### Build and install with Poetry

Install [Poetry](https://python-poetry.org/docs/#installation) first.

```bash
git clone https://github.com/Interactions-HSG/MyoKTROS.git && cd MyoKTROS
poetry install
poetry build
```

## Usage

```console
❯ myoktros -h
usage: myoktros [-h] [-c CONFIG] {run,calibrate,test} ...

Myo EMG-based KT system for ROS

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        path to the config file (config.ini)

commands:
  {run,calibrate,test}
```

### Configuration

The `config.ini` should be configured. Find the file in this repository for an actual example.

MyoKTROS initializes the avaialble gestures by reading this config file.

```ini
[myoktros]
gestures = # list of gestures

[myoktros.trigger_map]
# mapping of the gestures to the `RobotModel` transitions triggers

[myoktros.robot]
driver = # driver to connect to the robot

[myoktros.robot.xarm_rosws]
# driver-specific configurations
```

### Gesture Model Calibration

You need to record EMG data for training a gesture model (`keras`, `knn`, or `svm`).

The `myoktros calibrate` command lets you record the EMG data and save them as CSV files, and then train a model (default: `tensorflow.keras.Sequential`).

There are model-specific parameters prefixed by the `model-type`, and the parameters not meant for the chosen model are ignored.

If the model-specific parameters are configured for training, they also need to be passed to the `myoktros run` and `myoktros test` commands in order to load the trained model.

Otherwise, the model trained by the default parameters is loaded.

```console
❯ myoktros calibrate -h
usage: myoktros calibrate [-h] [--arm-dominance {left,right}] [--data DATA] [--duration DURATION] [--emg-mode EMG_MODE] [-g GESTURE]
                          [--knn-algorithm {auto,brute,ball_tree,kd_tree}] [--knn-k KNN_K] [--knn-metric {minkowski,euclidean,manhattan}] [--mac MAC]
                          [--model-type {keras,knn,svm}] [--n-samples N_SAMPLES] [--svm-c SVM_C] [--svm-degree SVM_DEGREE] [--svm-gamma {scale,auto}]
                          [--svm-kernel {linear,poly,rbf,sigmoid}] [-v] [--only-record | --only-train]

Calibrate the gesture model by recoding the user's EMG

options:
  -h, --help            show this help message and exit
  --arm-dominance {left,right}
                        left/right arm wearing the Myo (default: right)
  --data DATA           path to the data directory to save recorded data (default: /Users/iomz/ghq/github.com/Interactions-HSG/MyoKTROS/data)
  --duration DURATION   seconds to record each gesture for recoding (default: 30)
  --emg-mode EMG_MODE   set the myo.types.EMGMode to calibrate with (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified) (default: 1)
  -g GESTURE, --gesture GESTURE
                        if specified, only record a specific gesture (default: all)
  --knn-algorithm {auto,brute,ball_tree,kd_tree}
                        algorithm for fitting the knn model (default: auto)
  --knn-k KNN_K         k for fitting the knn model (default: 5)
  --knn-metric {minkowski,euclidean,manhattan}
                        distance metric for fitting the knn model (default: minkowski)
  --mac MAC             specify the mac address for Myo (default: None)
  --model-type {keras,knn,svm}
                        model type to calibrate (default: keras)
  --n-samples N_SAMPLES
                        number of samples to detect a gesture (default: 50)
  --svm-c SVM_C         regularization parameter C for fitting the svm model (must be strictly positive) (default: 1.0)
  --svm-degree SVM_DEGREE
                        degree of polynomial function for fitting the svm model with 'poly' kernel (default: 3)
  --svm-gamma {scale,auto}
                        kernel coefficient for fitting the svm model (default: scale)
  --svm-kernel {linear,poly,rbf,sigmoid}
                        kernel type for fitting the svm model (default: poly)
  -v, --verbose         sets the log level to debug (default: False)
  --only-record         only record EMG data without training a model (default: False)
  --only-train          only train a model without recording EMG data (default: False)
```

### Connecting MyoKTROS to a robot

MyoKTROS currently supports the following robots.

#### UFACTORY

- xArm series: https://www.ufactory.cc/xarm-collaborative-robot/
- LITE 6: https://www.ufactory.cc/lite-6-collaborative-robot/

##### xarm_ros2

[xarm_ros2](https://github.com/xArm-Developer/xarm_ros2/tree/humble) includes the ROS2 packages for xArm/Lite6 robot series.

The ROS nodes to communicate with xArm/Lite6 robots can be deployed by the included `docker-compose.yml`.
MyoKTROS invokes the xarm_api services via internal WebSocket messages whose payloads are analogous to the [SRV files](https://github.com/xArm-Developer/xarm_ros2/tree/humble/xarm_msgs/srv) for the corresponding services.

Note that, the `ros2-xarm` container attempts to connect to the robot accessible at the IP address specified by the environmental variable `ROBOT_IP`.

Depending on the model, you need to modify the launch command. For example:

- for Lite6 robots

```yml
ros2 launch xarm_api lite6_driver.launch.py robot_ip:="${ROBOT_IP}"
```

- for xArm7 robots

```yml
ros2 launch xarm_api xarm7_driver.launch.py robot_ip:="${ROBOT_IP}"
```

Finally, set `myoktros.robot.driver` to `xarm_rosws` and configure the parameters.

```ini
[myoktros.robot.xarm_rosws]
model = lite6 # the robot model
ip = 127.0.0.1 # the IP address for the ROS service client
port = 8765 # the port that the ROS service client's websocket interface is listening at
```

##### WebSocket API

UFACTORY's proprietary WebSocket API: https://github.com/xArm-Developer/ufactory_docs/blob/main/websocketapi/websocketapi.md

With this API driver, MyoKTROS can operate without ROS.

Set `myoktros.robot.driver` to `ufactory_ws` and configure the parameters.

```ini
[myoktros.robot.ufactory_ws]
model = lite6 # the robot model
ip = 10.0.0.6 # the IP address for the robot controller
```

## Visualizing the State Machine

`myoktros.Robot` is the base robot class for Robots to be intereacted with, and a default finite-state machine is implemented with [transitions](https://github.com/pytransitions/transitions).

transitions provides two methods to draw the diagram for the state machines.

### WebMachine

[transitions-gui](https://github.com/pytransitions/transitions-gui) implements `WebMachine` to produce a neat graph as a simple web service.

Run `scripts/robot_web_machine.py` (startup may take a few momemnt) and access [http://localhost:8080?details=true](http://localhost:8080?details=true) on your browser.

You may need additional dependencies if not with poetry:

```bash
pip install transitions-gui tornado
```

![robot_web_machine](https://github.com/Interactions-HSG/MyoKTROS/assets/26181/bb2a8bbb-04bd-4f59-a98f-70d5b5531392)

### GraphMachine

The state machine diagram can also be drawn using Graphviz with the [dot layout engine](https://graphviz.org/docs/layouts/dot/) by `scripts/robot_graph_machine.py`.

NOTE: [pygraphviz cannot be installed straight for macOS](https://github.com/pygraphviz/pygraphviz/issues/398#issuecomment-1038476921), so not included in the poetry dependencies.

1. Install Graphviz: see [here](https://github.com/pytransitions/transitions#-diagrams)
2. Install python packages
   - for macOS
     ```bash
     pip install \
        --global-option=build_ext \
        --global-option="-I$(brew --prefix graphviz)/include/" \
        --global-option="-L$(brew --prefix graphviz)/lib/" \
        pygraphviz
     pip install graphviz
     ```
   - Otherwise
     ```bash
     pip install "transitions[diagrams]"
     ```
3. Generate the diagram (gets saved in `assets/robot_state_diagram.png`)

```bash
./scripts/assets/generate_robot_state_diagram.py
```

![robot_graph_machine](https://github.com/Interactions-HSG/MyoKTROS/assets/26181/50dd10ce-2d8c-464e-89db-3b735cf4a48a)

## Gestures

Any gestures can be registered in `config.ini`, but these are some common examples.

### REST

<img width="30%" alt="REST-01" src="https://i.imgur.com/VOiCR2l.jpg">

### GRAB

<img width="30%" alt="GRAB-01" src="https://i.imgur.com/N4Wjt7C.jpg">
<img width="30%" alt="GRAB-02" src="https://i.imgur.com/7yMGchm.jpg">

### STRETCH_FINGERS

<img width="30%" alt="STRETCH_FINGERS-01" src="https://i.imgur.com/kaEhnDJ.jpg">
<img width="30%" alt="STRETCH_FINGERS-02" src="https://i.imgur.com/OOUIN9O.jpg">

### EXTENSION

<img width="30%" alt="EXTENSION-01" src="https://i.imgur.com/YtN5A5u.jpg">

### FLEXION

<img width="30%" alt="FLEXION-01" src="https://i.imgur.com/ncUiF1V.jpg">

### HORN

<img width="30%" alt="HORN-01" src="https://i.imgur.com/aFCt5jB.jpg">
<img width="30%" alt="HORN-02" src="https://i.imgur.com/SJc8kEg.jpg">

### FLEMING

<img width="30%" alt="FLEMING-01" src="https://i.imgur.com/8Nl8DJO.jpg">
<img width="30%" alt="FLEMING-02" src="https://i.imgur.com/6jTQYQp.jpg">

### THUMBS_UP

<img width="30%" alt="THUMBS_UP-01" src="https://i.imgur.com/MvhaSyZ.jpg">

### SHOOT

<img width="30%" alt="SHOOT-01" src="https://i.imgur.com/6xTSv5n.jpg">
<img width="30%" alt="SHOOT-02" src="https://i.imgur.com/jguueyE.jpg">

### TENNET

<img width="30%" alt="TENNET-01" src="https://i.imgur.com/MNbdTz4.jpg">

## Myo

Myo Armbands are capable of streaming data as follows.

|            | EMGData  | FVData  | IMUData |
| ---------- | -------- | ------- | ------- |
| Throughput | ~200 S/s | ~50 S/s | ~50 S/s |

Use `scripts/speedometer.py` to see it yourself.

```console
❯ ./scripts/speedometer.py -h
usage: speedometer.py [-h] [--emg-mode {0,1,2,3}] [--imu-mode {0,1,2,3}] [--mac MAC] [--seconds SECONDS]

Measure the data stream throughput from Myo

options:
  -h, --help            show this help message and exit
  --emg-mode {0,1,2,3}  set the myo.types.EMGMode (0: disabled, 1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified) (default: 1)
  --imu-mode {0,1,2,3}  set the myo.types.IMUMode (0: disabled, 1: data, 2: event, 3: all) (default: 0)
  --mac MAC             the mac address for Myo (default: None)
  --seconds SECONDS     the duration to record in seconds (default: 10)
```

## Authors

- Iori Mizutani ([@iomz](https://github.com/iomz))
- Felix Wohlgemuth
