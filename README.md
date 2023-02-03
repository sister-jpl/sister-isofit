# SISTER ISOFIT PGE Documentation

## Description

The sister-isofit repository is a wrapper for the L2A atmospheric correction repository called 
[ISOFIT](https://github.com/isofit/isofit).  ISOFIT contains a set of routines and utilities for fitting surface, 
atmosphere and instrument models to imaging spectrometer data.

## Dependencies

This repository is built to run on SISTER (Space-based Imaging Spectroscopy and Thermal pathfindER), a data 
processing back-end that allows for the registration of algorithms as executable containers and execution of those 
containers at scale.  The manifest file that configures this repository for registration and describes all of its 
necessary dependencies is called `algorithm_config.yaml`.  In this file you will find:

* The repository URL and version to register
* The base Docker image which this repository gets installed into, and a reference to its Dockerfile
* The build script which is used to install this repository into the base Docker image

Specific dependencies for executing the code in this repository can be found in both the Dockerfile and the build 
script.

In addition to the above dependencies, you will need access to the MAAP API via the maap-py library in order to 
register algorithms and submit jobs.  maap-py can be obtained by running:

    git clone --single-branch --branch system-test-8 https://gitlab.com/geospec/maap-py.git

## PGE Arguments

The sister-isofit PGE takes the following arguments:


| Argument            | Type   | Description                                      | Default |
|---------------------|--------|--------------------------------------------------|---------|
| radiance_dataset    | file   | S3 URL to the radiance dataset folder            | -       |
| location_dataset    | file   | S3 URL to the location dataset folder            | -       |
| observation_dataset | file   | S3 URL to the radiance dataset folder            | -       |
| segmentation_size   | config | Size of segments to construct for empirical line | 50      |
| n_cores             | config | Number of cores for parallelization              | 32      |
| crid                | config | Composite Release ID to tag file names           | 000     |
| _force_ingest       | config | Flag that allows overwriting existing files      | True    |

## Outputs

The L2A atmospheric correction PGE outputs ENVI formatted binary data cubes along with associated header files. The 
outputs of the PGE use the following naming convention:

    SISTER_INSTRUMENT_LEVEL_PRODUCT_YYYYMMDDTHHMMSS_CRID(_ANCILLARY).EXTENSION

where `(_ANCILLARY)` is optional and is used to identify ancillary products.

| Product                                    | Format, Units        | Example filename                                       |
|--------------------------------------------|----------------------|--------------------------------------------------------|
| Reflectance binary file                    | ENVI, Unitless (0-1) | SISTER_AVNG_L2A_RFL_20220814T183137_000.bin            |
| Reflectance header file                    | ASCII text           | SISTER_AVNG_L2A_RFL_20220814T183137_000.hdr            |
| Reflectance metadata file                  | JSON                 | SISTER_AVNG_L2A_RFL_20220814T183137_000.met.json       |
| Reflectance browse image                   | PNG                  | SISTER_AVNG_L2A_RFL_20220814T183137_000.png            |
| Reflectance uncertainty binary file        | ENVI, Unitless (0-1) | SISTER_AVNG_L2A_RFL_20220814T183137_000_UNC.bin        |
| Reflectance uncertainty header file        | Text                 | SISTER_AVNG_L2A_RFL_20220814T183137_000_UNC.hdr        |
| Reflectance uncertainty metadata file      | JSON                 | SISTER_AVNG_L2A_RFL_20220814T183137_000_UNC.met.json   |
| PGE log file                               | Text                 | SISTER_AVNG_L2A_RFL_20220814T183137_000.log            |
| PGE run config                             | JSON                 | SISTER_AVNG_L2A_RFL_20220814T183137_000.runconfig.json |

## Registering the Repository with SISTER

    from maap.maap import MAAP
    
    maap = MAAP(maap_host="34.216.77.111")
    
    algo_config_path = "sister-isofit/algorithm_config.yaml"
    response = maap.register_algorithm_from_yaml_file(file_path=algo_config_path)
    print(response.text)

## Submitting a Job on SISTER

    from maap.maap import MAAP
    
    maap = MAAP(maap_host="34.216.77.111")
    
    isofit_job_response = maap.submitJob(
        algo_id="sister-isofit",
        version="1.0.0",
        radiance_dataset="s3://s3.us-west-2.amazonaws.com:80/sister-ops-workspace/LOM/PRODUCTS/AVNG/L1B_RDN/2022/08/14/SISTER_AVNG_L1B_RDN_20220814T183137_000",
        location_dataset="s3://s3.us-west-2.amazonaws.com:80/sister-ops-workspace/LOM/PRODUCTS/AVNG/L1B_RDN/2022/08/14/SISTER_AVNG_L1B_RDN_20220814T183137_000_LOC",
        observation_dataset="s3://s3.us-west-2.amazonaws.com:80/sister-ops-workspace/LOM/PRODUCTS/AVNG/L1B_RDN/2022/08/14/SISTER_AVNG_L1B_RDN_20220814T183137_000_OBS",
        segmentation_size=50,
        n_cores=32,
        crid="000",
        publish_to_cmr=False,
        cmr_metadata={},
        queue="sister-job_worker-32gb",
        identifier="SISTER_AVNG_L2A_RFL_20220814T183137_000")
    
    print(isofit_job_response.id, isofit_job_response.status)
