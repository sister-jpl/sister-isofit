imgspec_dir=$(cd "$(dirname "$0")" ; pwd -P)
pge_dir=$(dirname ${imgspec_dir})
app_dir=$(dirname ${pge_dir})

cd $app_dir
git clone https://github.com/isofit/isofit.git -b v2.9.2
cd isofit
pip install -e .
pip install hy_tools_lite==1.1.1
pip install Pillow==9.2.0
