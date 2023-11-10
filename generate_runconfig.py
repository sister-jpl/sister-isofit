#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTER
Space-based Imaging Spectroscopy and Thermal PathfindER
Author: Adam Chlus, Winston Olson-Duvall
"""

import json
import os
import sys
import argparse


def main():
    """
        This function takes as input the path to an inputs.json file and exports a run config json
        containing the arguments needed to run the SISTER ISOFIT PGE.

    """

    parser = argparse.ArgumentParser(description='parse inputs to create inputs.json.')
    parser.add_argument('--crid', dest='crid', help='crid value')
    parser.add_argument('--n_cores', dest='n_cores', type=int, help='number of cores')
    parser.add_argument('--segmentation_size', dest='segmentation_size', type=int, help='segmentation size')
    parser.add_argument('--observation_dataset', dest='observation_dataset', help='observation dataset directory with full path')
    parser.add_argument('--location_dataset', dest='location_dataset', help='location dataset directory with full path')
    parser.add_argument('--radiance_dataset', dest='radiance_dataset', help='radiance dataset directory with full path')
    parser.add_argument('--experimental', help='If true then designates data as experiemntal')

    args = parser.parse_args()

    inputs = dict()
    inputs["positional"] = []

    files = []
    files.append({"observation_dataset": args.observation_dataset})
    files.append({"location_dataset": args.location_dataset})
    files.append({"radiance_dataset": args.radiance_dataset})

    config = dict()
    config["crid"] = args.crid
    config["n_cores"] = args.n_cores
    config["segmentation_size"] = args.segmentation_size
    config["experimental"] = True if args.experimental.lower() == "true" else False

    inputs["file"] = files
    inputs["config"] = config

    # Add inputs to runconfig
    run_config = {"inputs": inputs}

    # Add metadata to runconfig
    rdn_basename = None
    for file in run_config["inputs"]["file"]:
        if "radiance_dataset" in file:
            rdn_basename = os.path.basename(file["radiance_dataset"])

    met_json_path = os.path.join(file["radiance_dataset"], f"{rdn_basename}.met.json")
    with open(met_json_path, "r") as f:
        metadata = json.load(f)
    run_config["metadata"] = metadata

    # Write out runconfig.json
    config_file = "output/runconfig.json"
    with open(config_file, "w") as outfile:
        json.dump(run_config, outfile, indent=4)


if __name__ == "__main__":
    main()
