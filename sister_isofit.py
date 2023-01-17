#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTER
Space-based Imaging Spectroscopy and Thermal PathfindER
Author: Winston Olson-Duvall
"""

import json
import os
import subprocess
import sys

import numpy as np
import spectral.io.envi as envi


def generate_wavelengths(rdn_hdr_path, output_path):
    # Read in header file and get list of wavelengths and fwhm
    hdr = envi.read_envi_header(rdn_hdr_path)
    wl = hdr["wavelength"]
    fwhm = hdr["fwhm"]

    # Need to offset fwhm if its length is not the same as the wavelengths' length.  This is a known bug in
    # the AVIRIS-NG data.
    fwhm_offset = 0 if len(wl) == len(fwhm) else 23
    wl_arr = []
    for i in range(len(wl)):
        wl_arr.append([i, wl[i], fwhm[i + fwhm_offset]])

    # Save file
    np.savetxt(output_path, np.array(wl_arr, dtype=np.float32))


def main():
    """
        This function takes as input the path to an inputs.json file and exports a run config json
        containing the arguments needed to run the SISTER ISOFIT PGE.

    """

    in_file = sys.argv[1]

    # Read in runconfig
    with open(in_file, "r") as f:
        run_config = json.load(f)

    # Define paths
    sister_isofit_dir = os.path.abspath(os.path.dirname(__file__))
    isofit_dir = os.path.join(os.path.dirname(sister_isofit_dir), "isofit")

    dataset = os.path.basename(run_config["inputs"]["file"][0]["l1_granule"])
    rdn_bin_path = f"input/{dataset}/{dataset}.bin"
    rdn_hdr_path = f"input/{dataset}/{dataset}.hdr"
    loc_bin_path = f"input/{dataset}/{dataset}_LOC.bin"
    loc_hdr_path = f"input/{dataset}/{dataset}_LOC.hdr"
    obs_bin_path = f"input/{dataset}/{dataset}_OBS.bin"
    obs_hdr_path = f"input/{dataset}/{dataset}_OBS.hdr"

    surface_json_path = os.path.join(sister_isofit_dir, "surface_model", "surface.json")
    surface_model_path = f"input/surface.mat"
    wavelengths_path = f"input/wavelengths.txt"

    # Make output dir
    subprocess.run("mkdir output", shell=True)

    # Generate wavelengths file
    generate_wavelengths(rdn_hdr_path, wavelengths_path)


if __name__ == "__main__":
    main()
