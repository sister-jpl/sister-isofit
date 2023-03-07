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


def get_rfl_basename(rdn_basename, crid):
    # Replace product type
    tmp_basename = rdn_basename.replace("L1B_RDN", "L2A_RFL")
    # Split, remove old CRID, and add new one
    tokens = tmp_basename.split("_")[:-1] + [str(crid)]
    return "_".join(tokens)


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


def generate_metadata(run_config, rfl_met_json_path, unc_met_json_path):
    # Create .met.json file from runconfig for reflectance
    metadata = run_config["metadata"]
    metadata["product"] = "RFL"
    metadata["processing_level"] = "L2A"
    metadata["description"] = "Surface reflectance (unitless)"
    with open(rfl_met_json_path, "w") as f:
        json.dump(metadata, f, indent=4)

    # Now for uncertainty .met.json file
    metadata["product"] = "RFL_UNC"
    metadata["processing_level"] = "L2A"
    metadata["description"] = "Surface reflectance uncertainties (unitless)"
    with open(unc_met_json_path, "w") as f:
        json.dump(metadata, f, indent=4)


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

    rgb = np.stack([band1, band2, band3])
    rgb[rgb == img.no_data] = np.nan

    rgb = np.moveaxis(rgb,0,-1).astype(float)
    bottom = np.nanpercentile(rgb, 5, axis=(0, 1))
    top = np.nanpercentile(rgb, 95, axis=(0, 1))
    rgb = np.clip(rgb, bottom, top)
    rgb = (rgb - np.nanmin(rgb, axis=(0, 1))) / (np.nanmax(rgb, axis=(0, 1)) - np.nanmin(rgb, axis=(0, 1)))
    rgb = (rgb * 255).astype(np.uint8)

    im = Image.fromarray(rgb)
    im.save(output_path)


def update_header_descriptions(rfl_hdr_path, unc_hdr_path):
    # Update reflectance header
    hdr = envi.read_envi_header(rfl_hdr_path)
    hdr["description"] = "Surface reflectance (unitless)"
    envi.write_envi_header(rfl_hdr_path, hdr)
    # Update uncertainty header
    hdr = envi.read_envi_header(unc_hdr_path)
    hdr["description"] = "Surface reflectance uncertainties (unitless)"
    envi.write_envi_header(unc_hdr_path, hdr)


def main():
    """
        This function takes as input the path to an inputs.json file and exports a run config json
        containing the arguments needed to run the SISTER ISOFIT PGE.

    """
    in_file = sys.argv[1]

    # Read in runconfig
    print("Reading in runconfig")
    with open(in_file, "r") as f:
        run_config = json.load(f)

    # Make work dir
    print("Making work directory and symlinking input files")
    if not os.path.exists("work"):
        subprocess.run("mkdir work", shell=True)

    # Define paths and variables
    sister_isofit_dir = os.path.abspath(os.path.dirname(__file__))
    isofit_dir = os.path.join(os.path.dirname(sister_isofit_dir), "isofit")

    rdn_basename = None
    for file in run_config["inputs"]["file"]:
        if "radiance_dataset" in file:
            rdn_basename = os.path.basename(file["radiance_dataset"])

    loc_basename = f"{rdn_basename}_LOC"
    obs_basename = f"{rdn_basename}_OBS"
    rfl_basename = get_rfl_basename(rdn_basename, run_config["inputs"]["config"]["crid"])
    rdn_img_path = f"work/{rdn_basename}"
    rdn_hdr_path = f"work/{rdn_basename}.hdr"
    loc_img_path = f"work/{loc_basename}"
    loc_hdr_path = f"work/{loc_basename}.hdr"
    obs_img_path = f"work/{obs_basename}"
    obs_hdr_path = f"work/{obs_basename}.hdr"

    # Copy the input files into the work directory (don't use .bin)
    subprocess.run(f"cp input/{rdn_basename}/{rdn_basename}.bin {rdn_img_path}", shell=True)
    subprocess.run(f"cp input/{rdn_basename}/{rdn_basename}.hdr {rdn_hdr_path}", shell=True)
    subprocess.run(f"cp input/{loc_basename}/{loc_basename}.bin {loc_img_path}", shell=True)
    subprocess.run(f"cp input/{loc_basename}/{loc_basename}.hdr {loc_hdr_path}", shell=True)
    subprocess.run(f"cp input/{obs_basename}/{obs_basename}.bin {obs_img_path}", shell=True)
    subprocess.run(f"cp input/{obs_basename}/{obs_basename}.hdr {obs_hdr_path}", shell=True)

    # sensor is NA-YYYYMMDD
    sensor = f"NA-{rdn_basename.split('_')[4][:8]}"

    # Generate wavelengths file
    wavelengths_path = f"work/wavelengths.txt"
    print(f"Generating wavelengths from radiance header path at {rdn_hdr_path} to {wavelengths_path}")
    generate_wavelengths(rdn_hdr_path, wavelengths_path)

    # Copy surface model files to input folder and generate surface model
    print(f"Generating surface model using work/surface.json config")
    subprocess.run(f"cp {sister_isofit_dir}/surface_model/* work/", shell=True)
    surface_model_path = f"work/surface.mat"
    surface_model("work/surface.json")

    # Run isofit
    apply_oe_exe = f"{isofit_dir}/isofit/utils/apply_oe.py"
    log_basename = f"{rfl_basename}.log"
    cmd = [
        "python",
        apply_oe_exe,
        rdn_img_path,
        loc_img_path,
        obs_img_path,
        "work",
        sensor,
        "--presolve=1",
        "--analytical_line=1",
        f"--emulator_base={os.environ.get('EMULATOR_PATH')}",
        f"--n_cores={run_config['inputs']['config']['n_cores']}",
        f"--wavelength_path={wavelengths_path}",
        f"--surface_path={surface_model_path}",
        f"--segmentation_size={run_config['inputs']['config']['segmentation_size']}",
        f"--log_file=work/{log_basename}",
        "-pressure_elevation"
    ]
    print("Running apply_oe command: " + " ".join(cmd))
    subprocess.run(" ".join(cmd), shell=True)

    # Make output dir
    if not os.path.exists("output"):
        subprocess.run("mkdir output", shell=True)

    # Generate metadata in .met.json file for each product type
    rfl_met_json_path = f"output/{rfl_basename}.met.json"
    unc_met_json_path = f"output/{rfl_basename}_UNC.met.json"
    print(f"Generating metadata from runconfig to {rfl_met_json_path} and {unc_met_json_path}")
    generate_metadata(run_config, rfl_met_json_path, unc_met_json_path)

    # Generate quicklook
    rfl_ql_path = f"output/{rfl_basename}.png"
    print(f"Generating quicklook to {rfl_ql_path}")
    generate_quicklook(f"work/output/{rdn_basename}_rfl", rfl_ql_path)

    # Move/rename outputs to output dir
    rfl_img_path = f"output/{rfl_basename}.bin"
    rfl_hdr_path = f"output/{rfl_basename}.hdr"
    unc_img_path = f"output/{rfl_basename}_UNC.bin"
    unc_hdr_path = f"output/{rfl_basename}_UNC.hdr"
    subprocess.run(f"mv work/output/{rdn_basename}_rfl {rfl_img_path}", shell=True)
    subprocess.run(f"mv work/output/{rdn_basename}_rfl.hdr {rfl_hdr_path}", shell=True)
    subprocess.run(f"mv work/output/{rdn_basename}_uncert {unc_img_path}", shell=True)
    subprocess.run(f"mv work/output/{rdn_basename}_uncert.hdr {unc_hdr_path}", shell=True)

    # Update descriptions in reflectance and uncertainty ENVI headers
    update_header_descriptions(rfl_hdr_path, unc_hdr_path)

    # Also move log file and runconfig
    subprocess.run(f"mv work/{log_basename} output/{log_basename}", shell=True)
    subprocess.run(f"mv runconfig.json output/{rfl_basename}.runconfig.json", shell=True)


if __name__ == "__main__":
    main()
