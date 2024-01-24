#!/bin/bash

# description:
#
# The top-level run script to execute the ISOFIT atmospheric correction PGE on SISTER (Space-based Imaging Spectroscopy
# and Thermal PathfindER).
#
# File inputs:
#
# Config inputs:
#
# Positional inputs:
#

# Use isofit conda env from docker image
source activate isofit
mkdir -p output

# Get repository directory
REPO_DIR=$(cd "$(dirname "$0")"; pwd -P)

# Generate runconfig
python ${REPO_DIR}/generate_runconfig.py "${@:1}"

# Execute isofit
python ${REPO_DIR}/sister_isofit.py output/runconfig.json
