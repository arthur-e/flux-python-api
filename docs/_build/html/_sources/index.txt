.. flux-python-api documentation master file, created by
   sphinx-quickstart on Thu Apr 24 13:54:13 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

**flux-python-api**
=============================================

Contents: Documentation on installing and using **flux-python-api**.

.. toctree::
   :maxdepth: 2

**Installation and Setup**
================================
Install Git, if need be::

	sudo apt-get install git
	
And download the package to your preferred installation directory::
	
	cd /where/my/repo/lives/
	git clone git@github.com:arthur-e/flux-python-api.git

Installing within a Python Virtual Environment (recommended)
-------------------------------------------------------------
If you do not already have **virtuelenv** installed, see `full installation instructions <http://www.virtualenv.org/en/latest/virtualenv.html#installation>`_.

Briefly, using `pip <http://www.pip-installer.org/en/latest/>`_::

	[sudo] pip install virtualenv

Then set up your **virtualenv**, e.g.::

	cd /where/my/virtualenvs/live/
	virtualenv my_new_virtualenv
	
	# ensure the virtualenv is accessible to non-root users
	sudo chmod -R 775 my_new_virtualenv

And activate::

	source my_new_virtualenv/bin/activate

While your shell is activated, run **setup.py** (do **NOT** run as **sudo**)::

	cd /where/my/repo/lives/flux-python-api
	python setup.py install

Finally, deactivate the virtual environment::

	deactivate

All done!

Installing without a Python Virtual Environment 
-------------------------------------------------
If not using a python virtual environment, simply run **setup.py** ::

	cd /where/my/repo/lives/flux-python-api
	sudo python setup.py install



**Loading data**
================================

Use the **load.py** utility to load flux data from files that are in Matlab (*\*.mat*) or HDF5 (*\*.h5* or *\*.mat*) format. A description of the required configuration file and examples are provided in the next sections. 

Usage::

	load.py -i <inputfile> [OPTIONAL ARGUMENTS]
    
	Required argument:
	    -i, --ifile          Input file in Matlab (*.mat) or HDF5 (*.h5 or *.mat) format 
	
	Optional arguments:
	    -c, --config_file    Specify location of json config file. By default, uses
	                         input file w/ .json extension.
	
	These optional args can be used to override specifications of the config file:
	    -n, --var_name       The name of the variable in the hierarchical file
	                         that stores the data
	    -t, --timestamp      An ISO 8601 timestamp for the first observation


The configuration file
----------------------

This utility requires that the input *\*.h5* or *\*.mat* file be accompanied by a JSON configuration file specifying required metadata parameters.
By default, the utility will look for a *\*.json* file with the same name as the data file, but you can specify an alternate location when using **load.py** by using the **-c** option.

Configuration file parameter schema::

    "columns": [String],        // Array of well-known column identifiers, in order
                                // e.g. "x", "y", "value", "error"

    "gridres": {
    	"units": String,        // Grid cell units 
    	"x": Number,            // Grid cell resolution in the x direction
    	"y": Number             // Grid cell resolution in the y direction
    },
    	
    "header": [String],         // Array of human-readable column headers, in order

    "parameters": [String],     // Array of well-known variable names e.g.
                                // "values", "value", "errors" or "error"

    "span": String,             // The length of time, as a Pandas "freq" code, 
                                // that an observation spans

    "step": Number,             // The length of time, in seconds, between each
                                // observation to be imported

    "timestamp": String,        // An ISO 8601 timestamp for the first observation

    "title": String,            // Human-readable "pretty" name for the data set 
    
    "units": [String],          // Array of units for each field, in order

    "var_name": String         	// The name of the variable in the hierarchical
                                // file which stores the data


Contents of an example configuration file are shown here::

	{
	    "columns": ["x","y"],       
	    "gridres": {
			"units": "degrees",
			"x": 1.0,
			"y": 1.0
		},
	    "header": ["lng","lat"],  
	    "parameters": ["value","error"],
	    "span": "",           
	    "step": 10800,
	    "timestamp": "2012-12-22T03:00:00",
	    "title": "Surface Carbon Flux",
	    "units": ["degrees","degrees"],
	    "var_name": "casa_gfed_2004"
	}


Example usage of **load.py**
-----------------------------

Most basic example; assumes a configuration file exists at *~/mydata/data_casa_gfed_3hrly.json*)::
	
	load.py -i ~/mydata/data_casa_gfed_3hrly.mat
		
Using command line arguments to override configuration file parameters *var_name* and *timestamp*::

    load.py -i ~/mydata/data_casa_gfed_3hrly.mat -t 2003-12-22T03:00:00 -n casa_gfed_2004
    
Specifying a configuration file at a non-default location::

	load.py -i ~/mydata/data_casa_gfed_3hrly.mat -c -i ~/mydata/my_config_file.json


    



