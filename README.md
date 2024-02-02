# SISTER ISOFIT PGE Documentation

## Description

The sister-isofit repository is a wrapper for the L2A atmospheric correction repository called 
[ISOFIT](https://github.com/isofit/isofit).  ISOFIT contains a set of routines and utilities for fitting surface, 
atmosphere and instrument models to imaging spectrometer data.

## PGE Arguments

The sister-isofit PGE takes the following arguments:


| Argument            | Description                                      | Default |
|---------------------|--------------------------------------------------|---------|
| radiance_dataset    | Radiance dataset folder                          | -       |
| location_dataset    | Location dataset folder                          | -       |
| observation_dataset | Observation dataset folder                       | -       |
| segmentation_size   | Size of segments to construct for empirical line | 50      |
| n_cores             | Number of cores for parallelization              | 32      |
| crid                | Composite Release ID to tag file names           | 000     |
| experimental        | Designates outputs as "experimental"             | 'True'  |

## Outputs

The L2A atmospheric correction PGE outputs ENVI formatted binary data cubes along with associated header files. The 
outputs of the PGE use the following naming convention:

    (EXPERIMENTAL-)SISTER_INSTRUMENT_LEVEL_PRODUCT_YYYYMMDDTHHMMSS_CRID(_ANCILLARY).EXTENSION

where `(_ANCILLARY)` is optional and is used to identify ancillary products and `(EXPERIMENTAL-)` is also optional and 
is only added when the "experimental" flag is set to True.

The following data products are produced:

| Product                                                | Format, Units        | Example filename                                       |
|--------------------------------------------------------|----------------------|--------------------------------------------------------|
| Reflectance binary file                                | ENVI, Unitless (0-1) | SISTER_AVCL_L2A_RFL_20110513T175417_000.bin            |
| Reflectance header file                                | ASCII text           | SISTER_AVCL_L2A_RFL_20110513T175417_000.hdr            |
| Reflectance metadata file (STAC formatted)             | JSON                 | SISTER_AVCL_L2A_RFL_20110513T175417_000.json           |
| Reflectance browse image                               | PNG                  | SISTER_AVCL_L2A_RFL_20110513T175417_000.png            |
| Reflectance uncertainty binary file                    | ENVI, Unitless (0-1) | SISTER_AVCL_L2A_RFL_20110513T175417_000_UNC.bin        |
| Reflectance uncertainty header file                    | Text                 | SISTER_AVCL_L2A_RFL_20110513T175417_000_UNC.hdr        |
| Reflectance uncertainty metadata file (STAC formatted) | JSON                 | SISTER_AVCL_L2A_RFL_20110513T175417_000_UNC.json       |
| PGE log file                                           | Text                 | SISTER_AVCL_L2A_RFL_20110513T175417_000.log            |
| PGE run config                                         | JSON                 | SISTER_AVCL_L2A_RFL_20110513T175417_000.runconfig.json |

Metadata files are [STAC formatted](https://stacspec.org/en) and compatible with tools in the [STAC ecosystem](https://stacindex.org/ecosystem).

## Executing the Algorithm

This algorithm requires [Anaconda Python](https://www.anaconda.com/download)

To install and run the code, first clone the repository and execute the install script:

    git clone https://github.com/sister-jpl/sister-isofit.git
    cd sister-isofit
    ./install.sh
    cd ..

Then, create a working directory and enter it:

    mkdir WORK_DIR
    cd WORK_DIR

Copy input files to the work directory. For each "dataset" input, create a folder with the dataset name, then download 
the data file(s) and STAC JSON file into the folder.  For example, the radiance dataset input would look like this:

    WORK_DIR/SISTER_AVCL_L1B_RDN_20110513T175417_000/SISTER_AVCL_L1B_RDN_20110513T175417_000.bin
    WORK_DIR/SISTER_AVCL_L1B_RDN_20110513T175417_000/SISTER_AVCL_L1B_RDN_20110513T175417_000.hdr
    WORK_DIR/SISTER_AVCL_L1B_RDN_20110513T175417_000/SISTER_AVCL_L1B_RDN_20110513T175417_000.json

Finally, run the code 

    ../sister-isofit/run.sh --radiance_dataset SISTER_AVCL_L1B_RDN_20110513T175417_000 --location_dataset SISTER_AVCL_L1B_RDN_20110513T175417_000_LOC --observation_dataset SISTER_AVCL_L1B_RDN_20110513T175417_000_OBS
