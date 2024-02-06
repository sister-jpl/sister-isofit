pge_dir=$(cd "$(dirname "$0")" ; pwd -P)
app_dir=$(dirname ${pge_dir})

#sudo apt update -y
#sudo apt install -y build-essential gfortran awscli
#sudo apt clean

conda create -y --name isofit python=3.8
source activate isofit
conda install -y gdal=3.6.2
conda install -y -c conda-forge gfortran=13.1.0 awscli=1.29.8
conda install -y -c anaconda make=4.2.1

cd $app_dir

#Install 6s
mkdir 6s
cd 6s
aws s3 cp s3://sister-ops-registry/packages/6S/6sV2.1.tar .
tar xvf 6sV2.1.tar
sed -i 's/FFLAGS=  $(EXTRA)/FFLAGS=  $(EXTRA) -std=legacy/' Makefile
make
export SIXS_DIR=${app_dir}/6s

cd $app_dir
#Download emulator
aws s3 cp s3://sister-ops-registry/packages/sRTMnet_v120.h5 .
aws s3 cp s3://sister-ops-registry/packages/sRTMnet_v120_aux.npz .
export EMULATOR_PATH=${app_dir}/sRTMnet_v120.h5

git clone https://github.com/isofit/isofit.git -b v2.9.8

cd isofit
pip install -e .
pip install hy_tools_lite==1.1.1
pip install Pillow==9.2.0
pip install ray==1.9.2
pip install pystac==1.8.4