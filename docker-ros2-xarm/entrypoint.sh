#!/bin/bash
set -e

# setup ros2-xarm environment
source /app/install/setup.bash
exec "$@"
