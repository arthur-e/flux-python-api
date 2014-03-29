USERNAME=kaendsle

echo "Installing system dependencies (HDF5, libxml)..."
sudo apt-get install python-dev
sudo apt-get install libfreetype6 libfreetype6-dev # Required for matplotlib
sudo apt-get install libpng12 libpng12-dev # Required for matplotlib
sudo apt-get install gfortran libopenblas-dev liblapack-dev # Required for scipy
sudo apt-get install libhdf5-dev
sudo apt-get install libxml2 libxml2-dev libxslt1 libxslt1-dev

echo "Installing MongoDB..."
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10
# Create a /etc/apt/sources.list.d/10gen.list file and include the following line for the 10gen repository.
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/10gen.list
sudo apt-get update && sudo apt-get install mongodb-10gen

echo "Setting up the Python virtual environment..."
sudo easy_install pip
sudo pip install virtualenv
sudo mkdir /usr/local/pythonenv
sudo chown $USERNAME /usr/local/pythonenv
virtualenv /usr/local/pythonenv/fluxvis-env

echo "Installing Python dependencies..."
source /usr/local/pythonenv/fluxvis-bin/env/activate
pip install -r /usr/local/project/flux-python-api/DEPENDENCIES.txt

echo "/usr/local/project/flux-python-api/" > /usr/local/pythonenv/fluxvis-env/lib/python2.7/site-packages/fluxpy.pth

deactivate
