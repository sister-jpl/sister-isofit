# SISTER ISOFIT PGE Documentation

## Description

The sister-isofit repository is a wrapper for the L2A reflectance repository called 
[ISOFIT](https://github.com/isofit/isofit).  ISOFIT contains a set of routines and utilities for fitting surface, 
atmosphere and instrument models to imaging spectrometer data.

## Dependencies

This repository is built to run on SISTER (Space-based Imaging Spectroscopy and Thermal pathfindER), a data 
processing back-end that allows for the registration of algorithms as executable containers and execution of those 
containers at scale.  The manifest file that configures this repository for registration and describes all of its 
necessary dependencies is called `.imgspec/algorithm_config.yaml`.  In this file you will find:

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


| Argument                             | Type        | Description                                      | Default |
|--------------------------------------|-------------|--------------------------------------------------|---------|
| l1_granule                           | file        | URL to the L1 file                               | -       |
| surface_reflectance_spectra          | posititonal | Surface model input spectra (other)              | -       |
| vegetation_reflectance_spectra       | posititonal | Surface model input spectra (vegetation)         | -       |
| water_reflectance_spectra            | posititonal | Surface model input spectra (water)              | -       |
| snow_and_liquids_reflectance_spectra | posititonal | Surface model input spectra (snow)               | -       |
| segmentation_size                    | posititonal | Size of segments to construct for empirical line | 50      |
| n_cores                              | posititonal | Number of cores for parallelization              | 32      |


## Outputs

The L2A reflectance correction PGE outputs ENVI formatted binary data cubes along with associated header files. The 
outputs of the PGE use the following naming convention:

    SISTER_INSTRUMENT_YYYYMMDDTHHMMSS_L2A_SUBPRODUCT_VERSION

| Subproduct | Description                                | Units          | Example filename                                  |
|------------|--------------------------------------------|----------------|---------------------------------------------------|
| RFL        | ENVI reflectance binary file               | Unitless (0-1) | SISTER_AVNG\_20220502T180901\_L2A\_RFL\_001       |
|            | ENVI reflectance header file               | -              | SISTER_AVNG\_20220502T180901\_L2A\_RFL\_001.hdr   |
| UNC        | ENVI reflectance uncertainties binary file | Unitless (0-1) | SISTER_AVNG\_20220502T180901\_L2A\_UNC\_001       |
|            | ENVI reflectance uncertainties header file | -              | SISTER_AVNG\_20220502T180901\_L2A\_UNC\_001.hdr   |
| STATE      | ENVI state vector binary file              | Various        | SISTER_AVNG\_20220502T180901\_L2A\_STATE\_001     |
|            | ENVI state vector header file              | -              | SISTER_AVNG\_20220502T180901\_L2A\_STATE\_001.hdr |
| SEG        | ENVI super-pixel segments binary file      | Unitless       | SISTER_AVNG\_20220502T180901\_L2A\_SEG\_001       |
|            | ENVI super-pixel segments header file      | -              | SISTER_AVNG\_20220502T180901\_L2A\_SEG\_001.hdr   |


All outputs of the L2A reflectance correction are compressed into a single tar.gz file using the following naming structure:

    SISTER_INSTRUMENT_YYYYMMDDTHHMMSS_L2A_RFL_VERSION.tar.gz

example:

    SISTER_AVNG_20220502T180901_L2A_CORFL_001.tar.gz

In addition, a log file and a quicklook image are generated for each product with the naming conventions:

 	SISTER_INSTRUMENT_YYYYMMDDTHHMMSS_L2A_RFL_VERSION.log 	
    SISTER_INSTRUMENT_YYYYMMDDTHHMMSS_L2A_RFL_VERSION.png

## Registering the Repository with SISTER

    from maap.maap import MAAP
    
    maap = MAAP(maap_host="34.216.77.111")
    
    # Set up the configuration for the algorithm to register
    isofit_alg = {
        "script_command": "sister-isofit/.imgspec/imgspec_run.sh",
        "repo_url": "https://gitlab.com/geospec/sister-isofit.git",
        "algorithm_name": "sister-isofit",
        "code_version": "1.0.0",
        "algorithm_description": "The SISTER wrapper for ISOFIT. ISOFIT (Imaging Spectrometer Optimal FITting) contains a set of routines and utilities for fitting surface, atmosphere and instrument models to imaging spectrometer data.",
        "environment_name":"ubuntu",
        "disk_space": "70GB",
        "queue": "sister-job_worker-32gb",
        "build_command": "sister-isofit/.imgspec/install.sh",
        "docker_container_url": "localhost:5050/base_images/isofit:1.0",
        "algorithm_params": [
            {
                "field": "l1_granule",
                "type": "file"
            },
            {
                "field": "surface_reflectance_spectra",
                "type": "positional"
            },
            {
                "field": "vegetation_reflectance_spectra",
                "type": "positional"
            },
            {
                "field": "water_reflectance_spectra",
                "type": "positional"
            },
            {
                "field": "snow_and_liquids_reflectance_spectra",
                "type": "positional"
            },
            {
                "field": "segmentation_size",
                "type": "positional",
                "default": "50"
            },
            {
                "field": "n_cores",
                "type": "positional",
                "default": "32"
            }
        ]
    }
    
    # Make the request and print the results
    response = maap.registerAlgorithm(isofit_alg)
    print(response.text)

## Submitting a Job on SISTER

    from maap.maap import MAAP
    
    maap = MAAP(maap_host="34.216.77.111")
    
    isofit_job_response = maap.submitJob(
        algo_id="sister-isofit_ubuntu",
        version="1.0.0",
        l1_granule="http://sister-ops-workspace.s3.us-west-2.amazonaws.com/null/dps_output/sister-preprocess_ubuntu/sister-dev/2022/10/05/15/01/31/456920/SISTER_DESIS_20220606t114731_L1B_RDN_000.tar.gz",
        surface_reflectance_spectra="https://ecosis.org/api/package/emit-manually-adjusted-surface-reflectance-spectra/export",
        vegetation_reflectance_spectra="https://ecosis.org/api/package/emit-manually-adjusted-vegetation-reflectance-spectra/export",
        water_reflectance_spectra="https://ecosis.org/api/package/emit-manually-adjusted-water-reflectance-spectra/export",
        snow_and_liquids_reflectance_spectra="https://ecosis.org/api/package/emit-manually-adjusted-snow-and-liquids-reflectance-spectra/export",
        segmentation_size=50,
        n_cores=32,
        publish_to_cmr=False,
        cmr_metadata={},
        queue="sister-job_worker-32gb",
        identifier="SISTER_DESIS_20220606t114731_L1B_RDN_000")
    
    print(isofit_job_response.id, isofit_job_response.status)
