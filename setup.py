import os
import platform
from setuptools import setup

# Utility function to read the README file, used for long_description (which is used for PyPI documentation)
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()        
 
# Check if Linux and run setup.sh if so
if 'Linux' in platform.platform():
    os.system('./setup.sh')

#print 'Installing numpy...'
#os.system('pip install numpy==1.7.0')
 
###############################
# Run setuptools setup
print 'Running python setup...'
 
# get list of python dependencies
with open('DEPENDENCIES.txt') as f:
    required = f.read().splitlines()
 
print required
 
setup(
      name='flux-python-api',
      version=0.01,
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