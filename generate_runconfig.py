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
    parser.add_argument('--crid', dest='crid', help='crid value', default="000")
    parser.add_argument('--n_cores', dest='n_cores', type=int, help='number of cores', default=32)
    parser.add_argument('--segmentation_size', dest='segmentation_size', type=int, help='segmentation size', default=50)
    parser.add_argument('--observation_dataset', dest='observation_dataset', help='observation dataset directory with full path')
    parser.add_argument('--location_dataset', dest='location_dataset', help='location dataset directory with full path')
    parser.add_argument('--radiance_dataset', dest='radiance_dataset', help='radiance dataset directory with full path')
    parser.add_argument('--experimental', help='If true then designates data as experiemntal', default="True")

    args = parser.parse_args()

    run_config = {
        "inputs": {
            "radiance_dataset": args.radiance_dataset,
            "observation_dataset": args.observation_dataset,
            "location_dataset": args.location_dataset,
            "n_cores": args.n_cores,
            "segmentation_size": args.segmentation_size,
            "crid": args.crid,
        }
    }
    run_config["inputs"]["experimental"] = True if args.experimental.lower() == "true" else False

    # Write out runconfig.json
    config_file = "runconfig.json"
    with open(config_file, "w") as outfile:
        json.dump(run_config, outfile, indent=4)


if __name__ == "__main__":
    main()
