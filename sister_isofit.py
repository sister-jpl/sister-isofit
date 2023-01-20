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

from PIL import Image

import hytools_lite as ht
from isofit.utils import surface_model


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


def generate_metadata(run_config, output_path):
    # Create .met.json file from runconfig
    metadata = run_config["metadata"]
    metadata["product"] = "RFL"
    metadata["processing_level"] = "L2A"
    with open(output_path, "w") as f:
        json.dump(metadata, indent=4)


def generate_quicklook(rfl_img_path, output_path):
    # Generate a quicklook browse image
    img = ht.HyTools()
    img.read_file(rfl_img_path)

    if 'DESIS' in img.base_name:
        band3 = img.get_wave(560)
        band2 = img.get_wave(850)
        band1 = img.get_wave(660)
    else:
        band3 = img.get_wave(560)
        band2 = img.get_wave(850)
        band1 = img.get_wave(1660)

    rgb =  np.stack([band1, band2, band3])
    rgb[rgb == img.no_data] = np.nan

    rgb = np.moveaxis(rgb,0,-1).astype(float)
    bottom = np.nanpercentile(rgb, 5, axis=(0, 1))
    top = np.nanpercentile(rgb, 95, axis=(0, 1))
    rgb = np.clip(rgb, bottom, top)
    rgb = (rgb - np.nanmin(rgb, axis=(0, 1))) / (np.nanmax(rgb, axis=(0, 1)) - np.nanmin(rgb, axis=(0, 1)))
    rgb = (rgb * 255).astype(np.uint8)

    im = Image.fromarray(rgb)
    im.save(output_path)


def main():
    """
        This function takes as input the path to an inputs.json file and exports a run config json
        containing the arguments needed to run the SISTER ISOFIT PGE.

    """
    in_file = sys.argv[1]

    # Read in runconfig
    with open(in_file, "r") as f:
        run_config = json.load(f)

    # Define paths and variables
    sister_isofit_dir = os.path.abspath(os.path.dirname(__file__))
    isofit_dir = os.path.join(os.path.dirname(sister_isofit_dir), "isofit")

    rdn_basename = os.path.basename(run_config["inputs"]["file"][0]["l1_granule"])
    rfl_basename = rdn_basename.replace("L1B_RDN", "L2A_RFL")
    rdn_img_path = f"input/{rdn_basename}/{rdn_basename}"
    rdn_hdr_path = f"input/{rdn_basename}/{rdn_basename}.hdr"
    loc_img_path = f"input/{rdn_basename}/{rdn_basename}_LOC"
    loc_hdr_path = f"input/{rdn_basename}/{rdn_basename}_LOC.hdr"
    obs_img_path = f"input/{rdn_basename}/{rdn_basename}_OBS"
    obs_hdr_path = f"input/{rdn_basename}/{rdn_basename}_OBS.hdr"

    # Rename and remove ".bin" from ENVI binary files for isofit compatibility
    subprocess.run(f"mv {rdn_img_path}.bin {rdn_img_path}", shell=True)
    subprocess.run(f"mv {loc_img_path}.bin {loc_img_path}", shell=True)
    subprocess.run(f"mv {obs_img_path}.bin {obs_img_path}", shell=True)

    # sensor is NA-YYYYMMDD
    sensor = f"NA-{rdn_basename.split('_')[4][:8]}"

    surface_json_path = os.path.join(sister_isofit_dir, "surface_model", "surface.json")
    surface_model_path = f"input/surface.mat"
    wavelengths_path = f"input/wavelengths.txt"

    apply_oe_exe = f"{isofit_dir}/isofit/utils/apply_oe.py"

    # Make output dir
    if not os.path.exists("output"):
        subprocess.run("mkdir output", shell=True)

    # Generate wavelengths file
    generate_wavelengths(rdn_hdr_path, wavelengths_path)

    # Copy surface model files to input folder and generate surface model
    subprocess.run(f"cp {sister_isofit_dir}/surface_model/* input/", shell=True)
    surface_model("input/surface.json")

    # Run isofit
    cmd = [
        "python",
        apply_oe_exe,
        rdn_img_path,
        loc_img_path,
        obs_img_path,
        "output",
        sensor,
        "--presolve=1",
        "--empirical_line=1",
        f"--emulator_base={os.environ.get('EMULATOR_DIR')}",
        f"--n_cores={run_config['inputs']['config']['n_cores']}",
        "--wavelength_path=input/wavelengths.txt",
        "--surface_path=input/surface.mat",
        f"--segmentation_size={run_config['inputs']['config']['segmentation_size']}",
        f"--log_file=output/{rfl_basename}.log"
    ]
    print(" ".join(cmd))
    subprocess.run(" ".join(cmd), shell=True)

    # Generate metadata in .met.json file
    met_json_path = f"output/{rfl_basename}.met.json"
    generate_metadata(run_config, met_json_path)

    # Rename outputs
    rfl_img_path = f"output/{rfl_basename}.bin"

    # Generate quicklook
    rfl_ql_path = f"output/{rfl_basename}.png"
    generate_quicklook(rfl_img_path, rfl_ql_path)


if __name__ == "__main__":
    main()
