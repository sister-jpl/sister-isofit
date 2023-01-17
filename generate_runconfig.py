#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTER
Space-based Imaging Spectroscopy and Thermal PathfindER
Author: Adam Chlus
"""

import json
import os
import sys


def main():
    """
        This function takes as input the path to a inputs.json file and exports a run config json
        containing the arguments need to run the SISTER ISOFIT PGE.

    """

    inputs_json = sys.argv[1]

    # Add inputs to runconfig
    with open(inputs_json, "r") as in_file:
        inputs = json.load(in_file)
    run_config = {"inputs": inputs}

    # Add metadata to runconfig
    dataset = os.path.basename(inputs["file"][0]["l1_granule"])
    met_json_path = os.path.join("input", dataset, f"{dataset}.met.json")
    with open(met_json_path, "r") as f:
        metadata = json.load(f)
    run_config["metadata"] = metadata

    # Write out runconfig.json
    config_file = "runconfig.json"
    with open(config_file, "w") as outfile:
        json.dump(run_config, outfile, indent=4)


if __name__ == "__main__":
    main()