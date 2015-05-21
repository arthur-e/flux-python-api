import os
import platform
from setuptools import setup

# Utility function to read the README file, used for long_description (which is used for PyPI documentation)
def read(fname):
    return open(fname).read()        

current_dir = os.path.dirname(os.path.abspath(__file__))

# Check if Linux and run setup.sh if so
if 'Linux' in platform.platform():
    os.system(os.path.join(current_dir,'setup.sh'))
 
###############################
# Run setuptools setup
print 'Running python setup...'
 
# get list of python dependencies
with open(os.path.join(current_dir,'DEPENDENCIES.txt')) as f:
    required = f.read().splitlines()

# Due to a few bugs having to do with installing numpy via setuptools within a
# virtual environment and h5py dependencies not installing correctly
# (https://github.com/h5py/h5py/issues/535), for now we remove a few
# from the list and instead install them separately ahead of time.
for r in required[:]:
    if 'numpy' in r:
        numpy_req = r
        required.remove(r)
    if 'Cython' in r:
        cython_req = r
        required.remove(r)
    if 'h5py' in r:
        h5py_req = r
        required.remove(r)
    if 'Shapely' in r:
        shapely_req = r
        required.remove(r)
        
os.system('pip install ' + numpy_req)
os.system('pip install ' + cython_req)
os.system('pip install ' + h5py_req)
os.system('pip install ' + shapely_req)

os.chdir(current_dir)

setup(
      name='flux-python-api',
      version=0.22,
      author='K. Arthur Endsley',
      author_email='kaendsle@mtu.edu',
      description='Tools for loading Matlab/HDF5 data to Mongo DB',
      long_description=read('docs/index.rst'),
      url='https://github.com/arthur-e/flux-python-api',
      license='No license/not allowed to use',
      packages=['fluxpy'], # modules are specified by module name, not filename
      package_data={'fluxpy' : ['tests/*.mat']},
      classifiers=[
        'Programming Language :: Python',
        'License :: Other/Proprietary License',
        'Operating System :: Linux BSD',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        ],
      install_requires=required,
      )