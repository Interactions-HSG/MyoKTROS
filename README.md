# MyoKTROS

[![Build Status](https://github.com/Interactions-HSG/MyoKTROS/workflows/build/badge.svg)](https://github.com/Interactions-HSG/MyoKTROS/actions?query=workflow%3Abuild)
[![Python Versions](https://img.shields.io/pypi/pyversions/myoktros.svg)](https://pypi.python.org/pypi/myoktros)
[![PyPI Version](https://img.shields.io/pypi/v/myoktros.svg)](https://pypi.python.org/pypi/myoktros)
[![License](https://img.shields.io/pypi/l/myoktros.svg)](https://pypi.python.org/pypi/myoktros)

Myo EMG-based KT system for ROS.

## Installation

### PIP

```bash
pip install -U myoktros
```

### [Poetry](https://python-poetry.org/)

```bash
git clone https://github.com/Interactions-HSG/MyoKTROS.git && cd MyoKTROS
poetry install
poetry run myoktros
```

## Usage

```console
% myoktros -h
usage: myoktros [-h] [--mode {keras,legacy}] [-a ADDRESS] [-d] [-m MAC] [--legacy_n_samples LEGACY_N_SAMPLES] [--legacy_n_periods LEGACY_N_PERIODS] [-p PORT]

Myo EMG-based KT system for ROS

options:
  -h, --help            show this help message and exit
  --mode {keras,legacy}
                        mode to select (default: keras)
  -a ADDRESS, --address ADDRESS
                        the IP address for the ROS server (default: 127.0.0.1)
  -d, --debug           sets the log level to debug (default: False)
  -m MAC, --mac MAC     specify the Myo's mac address (default: None)
  --legacy_n_samples LEGACY_N_SAMPLES
                        number of samples for the legacy classifier (default: 3)
  --legacy_n_periods LEGACY_N_PERIODS
                        number of sampling periods for the legacy classifier (default: 10)
  -p PORT, --port PORT  the port for the ROS server (default: 8765)
```

### Legacy Mode

Use with the legacy k-NN classifier with sampling normalization.

First generate the classifier

```bash
poetry run scripts/train_legacy_classifier.py
```

then run with `--mode legacy`

```bash
poetry run myoktros --mode legacy
```

## Train the gesture classifier model

1. `scripts/record_myo_data.py` records the EMG stream to a CSV file in `/assets`.

```console
% poetry run scripts/record_myo_data.py -h
usage: record_myo_data.py [-h] [--emg_mode {1,2,3}] [--mac MAC] [--seconds SECONDS] N

Record train data from Myo's data stream

positional arguments:
  N                   the gesture to record (the enum value of myoktros.Gesture)

options:
  -h, --help          show this help message and exit
  --emg_mode {1,2,3}  set the myo.EMGMode (1: filtered/rectified, 2: filtered/unrectified, 3: unfiltered/unrectified) (default: 1)
  --mac MAC           the Myo's mac address (default: None)
  --seconds SECONDS   the duration to record in seconds (default: 30)
```

for example,

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

2. `scripts/` builds a Keras.Sequential model based on the CSV files from 1.

## Authors

- Iori Mizutani ([@iomz](https://github.com/iomz))
- Felix Wohlgemuth
