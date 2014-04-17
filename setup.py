import os
from setuptools import setup

# Insert OS check?


# Utility for installing a list of packages via command line apt-get call
def aptget(packages):
    os.system('sudo apt-get install {0}'.format(' '.join(packages)))

# Utility function to read the README file, used for long_description (which is used for PyPI documentation)
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

# Install system dependencies
print 'Installing system dependencies (HDF5, libxml)...'
system_dependencies = ['python-dev',
                       'python-numpy',
                       'python-matplotlib',
                       'libfreetype6', # matplotlib requirement
                       'libfreetype6-dev', # matplotlib requirement
                       'libpng12', # matplotlib requirement
                       'libpng12-dev', # matplotlib requirement
                       'gfortran', # scipy requirement
                       'libopenblas-dev', # scipy requirement
                       'liblapack-dev', # scipy requirement
                       'libhdf5-dev',
                       'libxml2',
                       'libxml2-dev',
                       'libxslt1',
                       'libxslt1-dev']

aptget(system_dependencies)

# System dependencies specific to Ubuntu 12.04... should we account for different flavors? and how?
print 'Installing geospatial system dependencies (GEOS)...'
os.system('sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable')
os.system('sudo apt-get update')
system_dependencies_12p04 = ['libgeos-3.3.8',
                             'libgeos-c1']

aptget(system_dependencies_12p04)

print 'Installing MongoDB...'
os.system('sudo apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10')
# Create a /etc/apt/sources.list.d/10gen.list file and include the following line for the 10gen repository.
os.system("echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/10gen.list")
os.system('sudo apt-get update && sudo apt-get install mongodb-10gen')

# Run setuptools setup
print 'Running python setup...'

# get list of dependencies
with open('DEPENDENCIES.txt') as f:
    required = f.read().splitlines()

print required

setup(
      name='flux-python-api',
      version=0.1,
      author='K. Arthur Endsley',
      author_email='kaendsle@mtu.edu',
      description='Tools for loading Matlab/HDF5 data to Mongo DB',
      long_description=read('README.md'),
      url='https://github.com/arthur-e/flux-python-api',
      license='BSD', # check?
      packages=['fluxpy','fluxpy.legacy'], # modules are specified by module name, not filename (the same will hold true for packages and extensions)
      package_data={'fluxpy' : ['tests/*.mat']}, # do we need to include these?
      classifiers=[
        'Programming Language :: Python',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Linux BSD',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Software Development :: Libraries :: Python Modules'
        ],
      install_requires=required,
      )