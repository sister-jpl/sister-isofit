#!/bin/bash

# Description:
#
# The top-level run script to execute ISOFIT on ImgSPEC. This script accepts the inputs described in the
# algorithm_config.yaml file and pre-processes them as needed to pass into isofit/util/apply_oe.py.  This script
# is currently compatible with AVIRIS Classic, AVIRIS-NG, and PRISMA data.
#
# Inputs:
#
# $1: EcoSIS URL of surface_reflectance_spectra
# $2: EcoSIS URL of vegetation_reflectance_spectra
# $3: EcoSIS URL of water_reflectance_spectra
# $4: EcoSIS URL of snow_and_liquids_reflectance_spectra
# $5: ISOFIT apply_oe.py segmentation_size argument
# $6: ISOFIT apply_oe.py n_cores argument
#
# In addition to the positional arguments, this script expects a downloaded radiance granule to be present in a folder
# called "input".

# Use isofit conda env from docker image
source activate isofit

# Get directories and paths for scripts
imgspec_dir=$( cd "$(dirname "$0")" ; pwd -P )
sister_isofit_dir=$(dirname $imgspec_dir)
apps_dir=$(dirname $sister_isofit_dir)
isofit_dir="${apps_dir}/isofit"

echo "imgspec_dir is $imgspec_dir"
echo "sister_isofit_dir is $sister_isofit_dir"
echo "isofit_dir is $isofit_dir"

# input/output dirs
input="input"
mkdir -p output temp

# .imgspec paths
wavelength_file_exe="$imgspec_dir/wavelength_file.py"
covnert_csv_to_envi_exe="$imgspec_dir/convert_csv_to_envi.py"
surface_json_path="$imgspec_dir/surface.json"

# utils paths
surface_model_exe="$isofit_dir/isofit/utils/surface_model.py"
apply_oe_exe="$isofit_dir/isofit/utils/apply_oe.py"

# ecosis input spectra paths
filtered_other_csv_path="$input/surface-reflectance-spectra.csv"
filtered_veg_csv_path="$input/vegetation_reflectance_spectra.csv"
filtered_ocean_csv_path="$input/water_reflectance_spectra.csv"
surface_liquids_csv_path="$input/snow_and_liquids_reflectance_spectra.csv"

# Process positional args to get EcoSIS CSV files
curl --retry 10 --output $filtered_other_csv_path $1
curl --retry 10 --output $filtered_veg_csv_path $2
curl --retry 10 --output $filtered_ocean_csv_path $3
curl --retry 10 --output $surface_liquids_csv_path $4

# Converted spectra ENVI paths
filtered_other_img_path=${filtered_other_csv_path/.csv/}
filtered_veg_img_path=${filtered_veg_csv_path/.csv/}
filtered_ocean_img_path=${filtered_ocean_csv_path/.csv/}
surface_liquids_img_path=${surface_liquids_csv_path/.csv/}

# Extract L1B dataset
tar -xzvf input/*.tar.gz -C input

# Get input paths

rdn_path=$(ls input/*/*RDN* | grep -v '.hdr')
loc_path=$(ls input/*/*LOC* | grep -v '.hdr')
obs_path=$(ls input/*/*OBS* | grep -v '.hdr')

echo "Found input RDN file: $rdn_path"
echo "Found input LOC file: $loc_path"
echo "Found input OBS file: $obs_path"

rdn_name=$(basename $rdn_path)
output_base_name=$(echo "${rdn_name/L1B_RDN/"L2A_RFL"}")

# Get instrument type

if [[ $rdn_name == *AVCL* ]] || [[ $rdn_name == *AVNG* ]]; then
    instrument=NA-$(echo $rdn_name | cut -c13-20)
elif [[ $rdn_name == *DESIS* ]]; then
    instrument=NA-$(echo $rdn_name | cut -c14-21)
elif [[ $rdn_name == *PRISMA* ]]; then
    instrument=NA-$(echo $rdn_name | cut -c15-22)
fi

echo "Instrument is $instrument"
echo "Output prefix is $output_base_name"

# Create wavelength file
wavelength_file_cmd="python $wavelength_file_exe $rdn_path.hdr $input/wavelengths.txt"
echo "Executing command: $wavelength_file_cmd"
$wavelength_file_cmd

# Build surface model based on surface.json template and input spectra CSV
# First convert CSV to ENVI for 3 spectra files
convert_csv_to_envi_cmd="python $covnert_csv_to_envi_exe $filtered_other_csv_path"
echo "Executing command: convert_csv_to_envi_cmd on $filtered_other_csv_path"
$convert_csv_to_envi_cmd

convert_csv_to_envi_cmd="python $covnert_csv_to_envi_exe $filtered_veg_csv_path"
echo "Executing command: convert_csv_to_envi_cmd on $filtered_veg_csv_path"
$convert_csv_to_envi_cmd

convert_csv_to_envi_cmd="python $covnert_csv_to_envi_exe $filtered_ocean_csv_path"
echo "Executing command: convert_csv_to_envi_cmd on $filtered_ocean_csv_path"
$convert_csv_to_envi_cmd

convert_csv_to_envi_cmd="python $covnert_csv_to_envi_exe $surface_liquids_csv_path"
echo "Executing command: convert_csv_to_envi_cmd on $surface_liquids_csv_path"
$convert_csv_to_envi_cmd

sed -e "s|\${output_model_file}|\./surface.mat|g" \
    -e "s|\${wavelength_file}|\./wavelengths.txt|g" \
    -e "s|\${input_spectrum_filtered_other}|${filtered_other_img_path/input/\.}|g" \
    -e "s|\${input_spectrum_filtered_veg}|${filtered_veg_img_path/input/\.}|g" \
    -e "s|\${input_spectrum_filtered_ocean}|${filtered_ocean_img_path/input/\.}|g" \
    -e "s|\${input_spectrum_surface_liquids}|${surface_liquids_img_path/input/\.}|g" \
    $surface_json_path > $input/surface.json
echo "Building surface model using config file $input/surface.json"
python -c "from isofit.utils import surface_model; surface_model('$input/surface.json')"

# Run isofit
isofit_cmd=""

isofit_cmd="""python $apply_oe_exe $rdn_path $loc_path $obs_path ./temp $instrument --presolve=1 \
--empirical_line=1 --emulator_base=$EMULATOR_DIR --n_cores $6 --wavelength_path $input/wavelengths.txt \
--segmentation_size $5 --surface_path $input/surface.mat \
--log_file output/$output_base_name.log"""

echo "Executing command: $isofit_cmd"
$isofit_cmd

# Make folder to hold output files
mkdir output/$output_base_name

#Rename files
mv temp/output/*subs_state output/$output_base_name/$(echo "${rdn_name/L1B_RDN/"L2A_STATE"}")
mv temp/output/*subs_state.hdr output/$output_base_name/$(echo "${rdn_name/L1B_RDN/"L2A_STATE"}").hdr

rm temp/output/*subs*

mv temp/output/*rfl output/$output_base_name/$(echo "${rdn_name/L1B_RDN/"L2A_RFL"}")
mv temp/output/*rfl.hdr output/$output_base_name/$(echo "${rdn_name/L1B_RDN/"L2A_RFL"}").hdr

mv temp/output/*uncert output/$output_base_name/$(echo "${rdn_name/L1B_RDN/"L2A_UNC"}")
mv temp/output/*uncert.hdr output/$output_base_name/$(echo "${rdn_name/L1B_RDN/"L2A_UNC"}").hdr

mv temp/output/*lbl output/$output_base_name/$(echo "${rdn_name/L1B_RDN/"L2A_SEG"}")
mv temp/output/*lbl.hdr output/$output_base_name/$(echo "${rdn_name/L1B_RDN/"L2A_SEG"}").hdr


cd output
mv *.log $output_base_name

#Generate metadata
python ${imgspec_dir}/generate_metadata.py */*RFL*.hdr .

# Create quicklook
python ${imgspec_dir}/generate_quicklook.py $(ls */*RFL* | grep -v '.hdr\|.log') .

#Compress output files
tar czvf ${output_base_name}.tar.gz $output_base_name

rm -r $output_base_name

cp ../run.log ${output_base_name}.log
