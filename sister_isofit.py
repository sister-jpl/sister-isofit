#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTER
Space-based Imaging Spectroscopy and Thermal PathfindER
Author: Winston Olson-Duvall
"""

import datetime as dt
import glob
import json
import os
import subprocess
import sys
import shutil

import numpy as np
import pystac
from spectral.io import envi

from PIL import Image

import hytools_lite as ht
from isofit.utils import surface_model
import time


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


def generate_metadata(run_config,json_path,new_metadata):

    metadata= run_config['metadata']
    for key,value in new_metadata.items():
        metadata[key] = value

    with open(json_path, 'w') as out_obj:
        json.dump(metadata,out_obj,indent=3)


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


def update_header_descriptions(hdr_path, description):
    hdr = envi.read_envi_header(hdr_path)
    hdr["description"] = description
    envi.write_envi_header(hdr_path, hdr)


def generate_stac_metadata(header_file):

    header = envi.read_envi_header(header_file)
    base_name = os.path.basename(header_file)[:-4]

    metadata = {}
    metadata['id'] = base_name
    metadata['start_datetime'] = dt.datetime.strptime(header['start acquisition time'], "%Y-%m-%dt%H:%M:%Sz")
    metadata['end_datetime'] = dt.datetime.strptime(header['end acquisition time'], "%Y-%m-%dt%H:%M:%Sz")
    # Split corner coordinates string into list
    coords = [float(x) for x in header['bounding box'].replace(']', '').replace('[', '').split(',')]
    geometry = [list(x) for x in zip(coords[::2], coords[1::2])]
    # Add first coord to the end of the list to close the polygon
    geometry.append(geometry[0])
    metadata['geometry'] = {
        "type": "Polygon",
        "coordinates": geometry
    }
    base_tokens = base_name.split('_')
    metadata['collection'] = f"SISTER_{base_tokens[1]}_{base_tokens[2]}_{base_tokens[3]}_{base_tokens[5]}"
    product = base_tokens[3]
    if "UNC" in base_name:
        product += "_UNC"
    metadata['properties'] = {
        'sensor': base_tokens[1],
        'description': header['description'],
        'product': product,
        'processing_level': base_tokens[2]
    }
    return metadata


def create_item(metadata, assets):
    item = pystac.Item(
        id=metadata['id'],
        datetime=metadata['start_datetime'],
        start_datetime=metadata['start_datetime'],
        end_datetime=metadata['end_datetime'],
        geometry=metadata['geometry'],
        collection=metadata['collection'],
        bbox=None,
        properties=metadata['properties']
    )
    # Add assets
    for key, href in assets.items():
        item.add_asset(key=key, asset=pystac.Asset(href=href))
    return item


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

    # Get experimental
    experimental = run_config['inputs']['experimental']
    if experimental:
        disclaimer = "(DISCLAIMER: THIS DATA IS EXPERIMENTAL AND NOT INTENDED FOR SCIENTIFIC USE) "
    else:
        disclaimer = ""

    # Make work dir
    print("Making work directory and symlinking input files")
    if not os.path.exists("work"):
        os.mkdir("work")

    # Define paths and variables
    sister_isofit_dir = os.path.abspath(os.path.dirname(__file__))
    isofit_dir = os.path.join(os.path.dirname(sister_isofit_dir), "isofit")

    rdn_path = run_config["inputs"]["radiance_dataset"]
    rdn_basename = os.path.basename(rdn_path)
    loc_path = run_config["inputs"]["location_dataset"]
    loc_basename = os.path.basename(loc_path)
    obs_path = run_config["inputs"]["observation_dataset"]
    obs_basename = os.path.basename(obs_path)

    rfl_basename = get_rfl_basename(rdn_basename, run_config["inputs"]["crid"])

    instrument = rfl_basename.split('_')[1]

    surface_config = 'work/surface_20221020.json'

    if instrument == "EMIT":
        sensor = 'emit'
        temp_basename = f'{sensor}{rdn_basename.split("_")[4]}'
        surface_config = "work/emit_surface_20221020.json"
    elif instrument == "AVNG":
        sensor = 'ang'
        temp_basename = f'{sensor}{rdn_basename.split("_")[4]}'
    elif instrument == "AVCL":
        sensor = 'avcl'
        temp_basename = f'f{rdn_basename.split("_")[4][2:8]}t00p00r00'
    else:
        sensor = f"NA-{rdn_basename.split('_')[4][:8]}"
        temp_basename = rdn_basename

    #Temporary input filenames without .bin extension
    rdn_img_path = f"work/{temp_basename}"
    rdn_hdr_path = f"work/{temp_basename}.hdr"
    loc_img_path = f"work/{temp_basename}_LOC"
    loc_hdr_path = f"work/{temp_basename}_LOC.hdr"
    obs_img_path = f"work/{temp_basename}_OBS"
    obs_hdr_path = f"work/{temp_basename}_OBS.hdr"

    # Copy the input files into the work directory (don't use .bin)
    shutil.copyfile(f"{rdn_path}/{rdn_basename}.bin" ,rdn_img_path)
    shutil.copyfile(f"{rdn_path}/{rdn_basename}.hdr" ,rdn_hdr_path)
    shutil.copyfile(f"{loc_path}/{loc_basename}.bin" ,loc_img_path)
    shutil.copyfile(f"{loc_path}/{loc_basename}.hdr" ,loc_hdr_path)
    shutil.copyfile(f"{obs_path}/{obs_basename}.bin" ,obs_img_path)
    shutil.copyfile(f"{obs_path}/{obs_basename}.hdr" ,obs_hdr_path)

    #Update radiance basename
    rdn_basename = os.path.basename(rdn_img_path)

    # Generate wavelengths file
    wavelengths_path = "work/wavelengths.txt"
    print(f"Generating wavelengths from radiance header path at {rdn_hdr_path} to {wavelengths_path}")
    generate_wavelengths(rdn_hdr_path, wavelengths_path)

    # Copy surface model files to input folder and generate surface model
    print("Generating surface model using work/surface.json config")
    subprocess.run(f"cp {sister_isofit_dir}/surface_model/* work/", shell=True)
    surface_model_path = "work/surface.mat"
    surface_model(surface_config)

    os.environ['SIXS_DIR'] = "/app/6s"

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
        "--analytical_line=0",
        "--empirical_line=1",
        "--emulator_base=/app/sRTMnet_v120.h5",
        f"--n_cores={run_config['inputs']['n_cores']}",
        f"--wavelength_path={wavelengths_path}",
        f"--surface_path={surface_model_path}",
        f"--segmentation_size={run_config['inputs']['segmentation_size']}",
        f"--log_file=work/{log_basename}"
    ]

    print("Running apply_oe command: " + " ".join(cmd))

    start_time = time.time()
    subprocess.run(" ".join(cmd), shell=True)
    end_time = time.time()

    # Make output dir
    if not os.path.exists("output"):
        os.mkdir("output")

    rfl_description = f"{disclaimer}Surface reflectance (unitless)"
    unc_description = f"{disclaimer}Surface reflectance uncertainties (unitless)"
    # atm_description ="Atmospheric state AOT550, Pressure Elevation, H2O"

    # Generate quicklook
    rfl_ql_path = f"output/{rfl_basename}.png"
    print(f"Generating quicklook to {rfl_ql_path}")
    generate_quicklook(f"work/output/{rdn_basename}_rfl", rfl_ql_path)

    # Move/rename outputs to output dir
    rfl_img_path = f"output/{rfl_basename}.bin"
    rfl_hdr_path = f"output/{rfl_basename}.hdr"
    unc_img_path = f"output/{rfl_basename}_UNC.bin"
    unc_hdr_path = f"output/{rfl_basename}_UNC.hdr"
    # atm_img_path = f"output/{rfl_basename}_ATM.bin"
    # atm_hdr_path = f"output/{rfl_basename}_ATM.hdr"

    shutil.copyfile(f"work/output/{rdn_basename}_rfl", rfl_img_path)
    shutil.copyfile(f"work/output/{rdn_basename}_rfl.hdr", rfl_hdr_path)
    shutil.copyfile(f"work/output/{rdn_basename}_uncert", unc_img_path)
    shutil.copyfile(f"work/output/{rdn_basename}_uncert.hdr", unc_hdr_path)

    # isofit_config_file = f"work/config/{rdn_basename}_modtran.json"
    # shutil.copyfile(isofit_config_file, f"output/{rfl_basename}_modtran.json")

    # Update descriptions in ENVI headers
    update_header_descriptions(rfl_hdr_path, rfl_description)
    update_header_descriptions(unc_hdr_path, unc_description)

    # Also move log file and runconfig
    shutil.copyfile(f"work/{log_basename}", f"output/{log_basename}")
    # shutil.copyfile("run.log", f"output/{rfl_basename}_run.log")
    shutil.copyfile("runconfig.json", f"output/{rfl_basename}.runconfig.json")
    # shutil.copyfile(f"work/config/{rdn_basename}_modtran.json",
    #                 f"output/{rfl_basename}_modtran.json")

    # If experimental, prefix filenames with "EXPERIMENTAL-"
    if experimental:
        for file in glob.glob(f"output/SISTER*"):
            shutil.move(file, f"output/EXPERIMENTAL-{os.path.basename(file)}")

    # Generate STAC
    rfl_file = glob.glob("output/*%s.bin" % run_config['inputs']['crid'])[0]
    rfl_basename = os.path.basename(rfl_file)[:-4]
    catalog = pystac.Catalog(id=rfl_basename,
                             description=f'{disclaimer}This catalog contains the output data products of the SISTER '
                                         f'ISOFIT reflectance PGE, including reflectance and reflectance uncertainty. '
                                         f'Execution artifacts including the runconfig file and execution log file are '
                                         f'included with the reflectance data.')

    # Add items for data products
    hdr_files = glob.glob("output/*SISTER*.hdr")
    hdr_files.sort()
    for hdr_file in hdr_files:
        metadata = generate_stac_metadata(hdr_file)
        assets = {
            "envi_binary": f"./{os.path.basename(hdr_file.replace('.hdr', '.bin'))}",
            "envi_header": f"./{os.path.basename(hdr_file)}"
        }
        # If it's the reflectance product, then add png, runconfig, and log
        if os.path.basename(hdr_file) == f"{rfl_basename}.hdr":
            png_file = hdr_file.replace(".hdr", ".png")
            assets["browse"] = f"./{os.path.basename(png_file)}"
            assets["runconfig"] = f"./{rfl_basename}.runconfig.json"
            if os.path.exists(f"output/{rfl_basename}.log"):
                assets["log"] = f"./{rfl_basename}.log"
        item = create_item(metadata, assets)
        catalog.add_item(item)

    # set catalog hrefs
    catalog.normalize_hrefs(f"./output/{rfl_basename}")

    # save the catalog
    catalog.describe()
    catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
    print("Catalog HREF: ", catalog.get_self_href())
    # print("Item HREF: ", item.get_self_href())

    # Move the assets from the output directory to the stac item directories and create empty .met.json
    for item in catalog.get_items():
        for asset in item.assets.values():
            fname = os.path.basename(asset.href)
            shutil.move(f"output/{fname}", f"output/{rfl_basename}/{item.id}/{fname}")
        with open(f"output/{rfl_basename}/{item.id}/{item.id}.met.json", mode="w"):
            pass


if __name__ == "__main__":
    main()
