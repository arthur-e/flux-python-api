echo "Linux OS detected; installing system dependencies (HDF5, libxml)..."
sudo apt-get install python-dev libhdf5-serial-dev libxml2 libxml2-dev libxslt1-dev
sudo apt-get install gfortran libopenblas-dev liblapack-dev # Required for scipy

# For Ubuntu 12.04 (precise) only
echo "Installing geospatial system dependencies (GEOS)..."
sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable
sudo apt-get update
sudo apt-get install libgeos-3.3.8 libgeos-c1

echo "Installing MongoDB..."
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10
# Create a /etc/apt/sources.list.d/10gen.list file and include the following line for the 10gen repository.
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/10gen.list
sudo apt-get update && sudo apt-get install mongodb-10gen
