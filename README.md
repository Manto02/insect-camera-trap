# insect-camera-trap
## short guide on how to setup the environment
for setup the environment install anaconda on your machine and next use this command to install all the dependencies needed
'''bash
conda env create -f environment_cpu.yml
# or if you have a nvidia gpu
conda env create -f environment_gpu.yml
'''

after the installation you have to activate the environment
'''bash
conda activate prog-cpu #or prog-gpu if you installed the other version
'''
