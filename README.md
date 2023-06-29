# MyoKTROS

[![build](https://github.com/Interactions-HSG/MyoKTROS/workflows/build/badge.svg)](https://github.com/Interactions-HSG/MyoKTROS/actions?query=workflow%3Abuild)
[![codecov](https://codecov.io/gh/Interactions-HSG/MyoKTROS/branch/main/graph/badge.svg?token=H8OT1FM4SG)](https://codecov.io/gh/Interactions-HSG/MyoKTROS)
[![python versions](https://img.shields.io/pypi/pyversions/myoktros.svg)](https://pypi.python.org/pypi/myoktros)
[![pypi version](https://img.shields.io/pypi/v/myoktros.svg)](https://pypi.python.org/pypi/myoktros)
[![license](https://img.shields.io/pypi/l/myoktros.svg)](https://pypi.python.org/pypi/myoktros)

Myo EMG-based KT system using, but not limited to, ROS.

<!-- vim-markdown-toc GFM -->

- [Installation](#installation)
  - [PIP](#pip)
  - [Build with Poetry](#build-with-poetry)
- [Usage](#usage)
  - [Connecting MyoKTROS to a robot](#connecting-myoktros-to-a-robot)
    - [UFACTORY](#ufactory)
  - [Gesture Model Calibration](#gesture-model-calibration)
  - [Visualizing the State Machine](#visualizing-the-state-machine)
    - [WebMachine](#webmachine)
    - [GraphMachine](#graphmachine)
- [Gestures](#gestures)
  - [0. REST](#0-rest)
  - [1. GRAB](#1-grab)
  - [2. STRETCH_FINGERS](#2-stretch_fingers)
  - [3. EXTENSION](#3-extension)
  - [4. HORN](#4-horn)
  - [5. FLEMING](#5-fleming)
  - [6. THUMBS_UP](#6-thumbs_up)
  - [7. FLEXION](#7-flexion)
  - [8. SHOOT](#8-shoot)
  - [9. TENNET](#9-tennet)
- [Myo](#myo)
- [Authors](#authors)

<!-- vim-markdown-toc -->

## Installation

### PIP

```bash
pip install -U myoktros
```

### Build with Poetry

Install [Poetry](https://python-poetry.org/docs/#installation) first.

```bash
git clone https://github.com/Interactions-HSG/MyoKTROS.git && cd MyoKTROS
poetry install
poetry run myoktros
```

## Usage

```console
❯ run myoktros run -h
usage: myoktros run [-h] [--arm-dominance {left,right}] [--emg-mode EMG_MODE] [--ip IP] [--mac MAC] [--model-type {keras,knn}] [--n-samples N_SAMPLES] [--port PORT]
                    [-v]

Run MyoKTROS

options:
  -h, --help            show this help message and exit
  --arm-dominance {left,right}
                        left/right arm wearing the Myo (default: right)
  --emg-mode EMG_MODE   set the myo.types.EMGMode to use (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified) (default: 1)
  --ip IP               IP address for the ROS server (default: 127.0.0.1)
  --mac MAC             specify the mac address for Myo (default: None)
  --model-type {keras,knn}
                        model type to detect the gestures (default: keras)
  --n-samples N_SAMPLES
                        number of samples to detect a gesture (default: 50)
  --port PORT           port for the ROS server (default: 8765)
  -v, --verbose         sets the log level to debug (default: False)
```

### Connecting MyoKTROS to a robot

MyoKTROS currently supports the following robot vendors.

#### UFACTORY

- [xarm_ros2](https://github.com/xArm-Developer/xarm_ros2/tree/humble)
- [WebSocket API](https://github.com/xArm-Developer/ufactory_docs/blob/main/websocketapi/websocketapi.md)

### Gesture Model Calibration

You need to record EMG data for training a gesture model.

The `myoktros calibrate` commands lets you record the EMG data and save them as CSV files, and then train a model (default: `tensorflow.keras.Sequential`).

```console
❯ myoktros calibrate -h
usage: myoktros calibrate [-h] [--arm-dominance {left,right}] [--data DATA] [--duration DURATION] [--emg-mode EMG_MODE] [-g GESTURE] [--k K] [--mac MAC]
                          [--model-type {keras,knn}] [--n-samples N_SAMPLES] [-v] [--only-record | --only-train]

Calibrate the gesture model by recoding the user's EMG

options:
  -h, --help            show this help message and exit
  --arm-dominance {left,right}
                        left/right arm wearing the Myo (default: right)
  --data DATA           path to the data directory to save recorded data (default: /Users/iomz/ghq/github.com/Interactions-HSG/MyoKTROS/data)
  --duration DURATION   seconds to record each gesture for recoding (default: 30)
  --emg-mode EMG_MODE   set the myo.types.EMGMode to calibrate with (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified) (default: 1)
  -g GESTURE, --gesture GESTURE
                        if specified, only record a specific gesture ['REST', 'GRAB', 'STRETCH_FINGERS', 'EXTENSION', 'HORN', 'FLEMING'] (default: all)
  --k K                 k for fitting the knn model (default: 15)
  --mac MAC             specify the mac address for Myo (default: None)
  --model-type {keras,knn}
                        model type to calibrate (default: keras)
  --n-samples N_SAMPLES
                        number of samples to detect a gesture (default: 50)
  -v, --verbose         sets the log level to debug (default: False)
  --only-record         only record EMG data without training a model (default: False)
  --only-train          only train a model without recording EMG data (default: False)
```

### Visualizing the State Machine

`myoktros.Robot` is the base robot class for Robots to be intereacted with, and a default finite-state machine is implemented with [transitions](https://github.com/pytransitions/transitions).

transitions provides two methods to draw the diagram for the state machines.

#### WebMachine

[transitions-gui](https://github.com/pytransitions/transitions-gui) implements `WebMachine` to produce a neat graph as a simple web service.

Run `scripts/robot_web_machine.py` (startup may take a few momemnt) and access [http://localhost:8080?details=true](http://localhost:8080?details=true) on your browser.

You may need additional dependencies if not with poetry:

```bash
pip install transitions-gui tornado
```

![robot_web_machine](https://github.com/Interactions-HSG/MyoKTROS/assets/26181/bb2a8bbb-04bd-4f59-a98f-70d5b5531392)

#### GraphMachine

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

### 0. REST

<img width="30%" alt="REST-01" src="https://i.imgur.com/VOiCR2l.jpg">

### 1. GRAB

<img width="30%" alt="GRAB-01" src="https://i.imgur.com/N4Wjt7C.jpg">
<img width="30%" alt="GRAB-02" src="https://i.imgur.com/7yMGchm.jpg">

### 2. STRETCH_FINGERS

<img width="30%" alt="STRETCH_FINGERS-01" src="https://i.imgur.com/kaEhnDJ.jpg">
<img width="30%" alt="STRETCH_FINGERS-02" src="https://i.imgur.com/OOUIN9O.jpg">

### 3. EXTENSION

<img width="30%" alt="EXTENSION-01" src="https://i.imgur.com/YtN5A5u.jpg">

### 4. HORN

<img width="30%" alt="HORN-01" src="https://i.imgur.com/aFCt5jB.jpg">
<img width="30%" alt="HORN-02" src="https://i.imgur.com/SJc8kEg.jpg">

### 5. FLEMING

<img width="30%" alt="FLEMING-01" src="https://i.imgur.com/8Nl8DJO.jpg">
<img width="30%" alt="FLEMING-02" src="https://i.imgur.com/6jTQYQp.jpg">

### 6. THUMBS_UP

<img width="30%" alt="THUMBS_UP-01" src="https://i.imgur.com/MvhaSyZ.jpg">

### 7. FLEXION

<img width="30%" alt="FLEXION-01" src="https://i.imgur.com/ncUiF1V.jpg">

### 8. SHOOT

<img width="30%" alt="SHOOT-01" src="https://i.imgur.com/6xTSv5n.jpg">
<img width="30%" alt="SHOOT-02" src="https://i.imgur.com/jguueyE.jpg">

### 9. TENNET

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
