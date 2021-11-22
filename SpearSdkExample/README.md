# Setup Instructions for SpearSdkExample Desktop Application

## Install Miniconda:

### On Linux Mint 20.1:

- Open a Terminal window
```bash
$ wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
$ bash Miniconda3-latest-Linux-x86_64.sh
```
- Press Enter until Do you accept the license terms? [yes|no]
- Enter yes
- Press ENTER to confirm the location
- Enter yes to Do you wish the installer to initialize Miniconda3 by running conda init? [yes|no]
- Close Terminal window
- Open a new Terminal window
```bash
$ conda config --set auto_activate_base false
```
- Close Terminal window

## Setup Python Environment:

### On Linux Mint 20.1:

- Open a Terminal window
```bash
$ sudo apt install libportaudio2
$ conda create -n SpearSdkExample python=3.7
$ conda activate SpearSdkExample
$ conda install numpy
$ conda install pyqt
$ pip install sounddevice
```
## Run SpearSdkExample Application:

### On Linux Mint 20.1:

- Change directory to SpearSdkExample diretory
```bash
$ export LD_LIBRARY_PATH=$PWD/libs/:$LD_LIBRARY_PATH
$ export PYTHONPATH=$PWD/libs/:$PYTHONPATH
$ python SpearSdkExample.py
```

## Directory Structure:

- assets - SPEAR-Language-Pack
- commands - SpearSDKExample CommandList module
- libs - SPEAR-SDK compiled library files
- spear - SPEAR-SDK SWIG generated Python bindings
- utils - SpearSDK ModifyConfig module
