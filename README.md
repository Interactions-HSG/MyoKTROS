# MyoKTROS

[![build](https://github.com/Interactions-HSG/MyoKTROS/workflows/build/badge.svg)](https://github.com/Interactions-HSG/MyoKTROS/actions?query=workflow%3Abuild)
[![codecov](https://codecov.io/gh/Interactions-HSG/MyoKTROS/branch/main/graph/badge.svg?token=H8OT1FM4SG)](https://codecov.io/gh/Interactions-HSG/MyoKTROS)
[![python versions](https://img.shields.io/pypi/pyversions/myoktros.svg)](https://pypi.python.org/pypi/myoktros)
[![pypi version](https://img.shields.io/pypi/v/myoktros.svg)](https://pypi.python.org/pypi/myoktros)
[![license](https://img.shields.io/pypi/l/myoktros.svg)](https://pypi.python.org/pypi/myoktros)

Myo EMG-based KT system for ROS.

<!-- vim-markdown-toc GFM -->

- [Installation](#installation)
  - [PIP](#pip)
  - [Build with Poetry](#build-with-poetry)
- [Usage](#usage)
  - [`keras` Mode Preparation](#keras-mode-preparation)
  - [`knn` Mode Preparation](#knn-mode-preparation)
  - [Visualizing the State Machine](#visualizing-the-state-machine)
    - [WebMachine](#webmachine)
    - [GraphMachine](#graphmachine)
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
❯ myoktros -h
usage: myoktros [-h] [--mode {keras,knn}] [-a ADDRESS] [-d] [-m MAC] [--knn_samples KNN_SAMPLES] [--knn_periods KNN_PERIODS] [-p PORT]

Myo EMG-based KT system for ROS

options:
  -h, --help            show this help message and exit
  --mode {keras,knn}
                        mode to select (default: keras)
  -a ADDRESS, --address ADDRESS
                        the IP address for the ROS server (default: 127.0.0.1)
  -d, --debug           sets the log level to debug (default: False)
  -m MAC, --mac MAC     specify the mac address for Myo (default: None)
  --knn_samples KNN_SAMPLES
                        number of samples for the knn classifier (default: 3)
  --knn_periods KNN_PERIODS
                        number of sampling periods for the knn classifier (default: 10)
  -p PORT, --port PORT  the port for the ROS server (default: 8765)
```

### `keras` Mode Preparation

Use a keras.Sequential model with sampling normalization to detect gestures.

You need to collect EMG data for gesutures and train a gesture model.

1. `scripts/record_myo_data.py` records EMG streams for _one gesture_ to a CSV file in `/assets`. Repeat this step for [_N_ gestures](https://github.com/Interactions-HSG/MyoKTROS/blob/main/src/myoktros/gesture.py#L15-L20).

```console
❯ poetry run scripts/record_myo_data.py -h
usage: record_myo_data.py [-h] [--emg_mode {1,2,3}] [--mac MAC] [--seconds SECONDS] N

Record train data from EMG data stream via Myo

positional arguments:
  N                   the gesture to record (the enum value of myoktros.Gesture)

options:
  -h, --help          show this help message and exit
  --emg_mode {1,2,3}  set the myo.EMGMode (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified) (default: 1)
  --mac MAC           the mac address for Myo (default: None)
  --seconds SECONDS   the duration to record in seconds (default: 30)
```

for example, to record EMG data for gesture _3_:

```console
❯ poetry run scripts/record_myo_data.py 3
2023-06-14 21:08:42,227 __main__ INFO: scanning for a Myo device...
2023-06-14 21:08:45,104 myoktros.myo_client INFO: connected to Myonnaise
2023-06-14 21:08:45,104 __main__ INFO: connected to a Myo
2023-06-14 21:08:45,108 myoktros.myo_client INFO: setting up the myo: Myonnaise
2023-06-14 21:08:45,133 myoktros.myo_client INFO: remaining battery: 91 %
2023-06-14 21:08:45,343 __main__ INFO: start recording BEND_WRIST data with SEND_FILT for 30 seconds
2023-06-14 21:08:47,345 myoktros.myo_client INFO: start notifying from Myonnaise
2023-06-14 21:09:17,545 myoktros.myo_client INFO: stopped notification from Myonnaise
2023-06-14 21:09:17,546 myoktros.myo_client INFO: sleep Myonnaise
2023-06-14 21:09:18,115 __main__ INFO: saved the recorded data to /Users/iomz/ghq/github.com/Interactions-HSG/MyoKTROS/data/SEND_FILT-BEND_WRIST-20230614210845.csv
```

2. `scripts/build_keras_model.py` builds a Keras.Sequential model based on the CSV files from 1.

```bash
❯ poetry run scripts/build_keras_model.py
WARNING:absl:At this time, the v2.11+ optimizer `tf.keras.optimizers.Adam` runs slowly on M1/M2 Macs, please use the legacy Keras optimizer instead, located at `tf.keras.optimizers.legacy.Adam`.
WARNING:absl:There is a known slowdown when using v2.11+ Keras optimizers on M1/M2 Macs. Falling back to the legacy Keras optimizer, i.e., `tf.keras.optimizers.legacy.Adam`.
Epoch 1/20
282/282 [==============================] - 0s 495us/step - loss: 0.3811
Epoch 2/20
282/282 [==============================] - 0s 495us/step - loss: 0.1141
Epoch 3/20
282/282 [==============================] - 0s 493us/step - loss: 0.0830
Epoch 4/20
282/282 [==============================] - 0s 484us/step - loss: 0.0630
Epoch 5/20
282/282 [==============================] - 0s 488us/step - loss: 0.0524
Epoch 6/20
282/282 [==============================] - 0s 483us/step - loss: 0.0459
Epoch 7/20
282/282 [==============================] - 0s 488us/step - loss: 0.0425
Epoch 8/20
282/282 [==============================] - 0s 486us/step - loss: 0.0380
Epoch 9/20
282/282 [==============================] - 0s 487us/step - loss: 0.0357
Epoch 10/20
282/282 [==============================] - 0s 497us/step - loss: 0.0336
Epoch 11/20
282/282 [==============================] - 0s 491us/step - loss: 0.0335
Epoch 12/20
282/282 [==============================] - 0s 491us/step - loss: 0.0310
Epoch 13/20
282/282 [==============================] - 0s 488us/step - loss: 0.0308
Epoch 14/20
282/282 [==============================] - 0s 491us/step - loss: 0.0279
Epoch 15/20
282/282 [==============================] - 0s 487us/step - loss: 0.0262
Epoch 16/20
282/282 [==============================] - 0s 494us/step - loss: 0.0259
Epoch 17/20
282/282 [==============================] - 0s 489us/step - loss: 0.0255
Epoch 18/20
282/282 [==============================] - 0s 489us/step - loss: 0.0243
Epoch 19/20
282/282 [==============================] - 0s 489us/step - loss: 0.0250
Epoch 20/20
282/282 [==============================] - 0s 483us/step - loss: 0.0234
poetry run scripts/build_keras_model.py  9.09s user 3.66s system 143% cpu 8.885 total
```

### `knn` Mode Preparation

Use the k-NN classifier with sampling normalization to detect gestures.

First generate the classifier

```bash
poetry run scripts/build_knn_classifier.py
```

then run with `--mode knn`

```bash
poetry run myoktros --mode knn
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

## Myo

Myo Armbands are capable of streaming data as follows.

|            | EMGData  | FVData  | IMUData |
| ---------- | -------- | ------- | ------- |
| Throughput | ~200 S/s | ~50 S/s | ~50 S/s |

Use `scripts/speedometer.py` to see it yourself.

```console
❯ poetry run scripts/speedometer.py -h
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
