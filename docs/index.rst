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
If you're using flux-python-api as part of the **Carbon Data Explorer**
package, you can ignore these installation steps; the **Carbon Data Explorer**
setup script will take care of installation.

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
	
	VENV_DIR=/usr/local/pythonenv
        virtualenv $VENV_DIR/flux-python-api-env
        source $VENV_DIR/flux-python-api-env/bin/activate
        python setup.py install
	
	
	# ensure the virtualenv is accessible to non-root users
	sudo chmod -R 775 $VENV_DIR/flux-python-api-env

And activate::

	source $VENV_DIR/flux-python-api-env/bin/activate

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


Adding "fluxpy" to the Python Path
----------------------------------

    echo "/where/my/repo/lives/flux-python-api/" > my_new_virtualenv/lib/python2.7/site-packages/fluxpy.pth


**Loading data**
================================

Use the **manage.py load** utility to load flux data from files that are in Matlab (*\*.mat*) or HDF5 (*\*.h5* or *\*.mat*) format. A description of the required configuration file and examples are provided in the next sections. 

Loading with **manage.py load**::

    Usage:
        manage.py load -p <filepath> -m <model> -n <collection_name> [OPTIONAL ARGS]
        
    Required arguments:
    
        -p, --path               Directory path of input file in Matlab (*.mat)
                                 or HDF5 (*.h5 or *.mat) format 
                                 
        -n, --collection_name    Provide a unique name for the dataset by which
                                 it will be identified in the MongoDB
        
        -m, --model              fluxpy/models.py model associated with the
                                 input dataset  
    
    Optional arguments:
    
        -c, --config_file        Specify location of json config file. By
                                 default, seeks input file w/ .json extension.
    
        -o, --options            Use to override specifications in the config file.
                                 Syntax: -o "parameter1=value1;parameter2=value2;parameter3=value3"
                                 e.g.: -o "title=MyData;gridres={'units':'degrees,'x':1.0,'y':1.0}"


The configuration file
----------------------

This utility requires that the input *\*.h5* or *\*.mat* file be accompanied by a JSON configuration file specifying required metadata parameters.
By default, the utility will look for a *\*.json* file with the same name as the data file, but you can specify an alternate location by using the **-c** option.

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
    
    "units": Object,          	// The measurement units, per parameter

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
	    "header": [
	        "lng",
	        "lat"
	    ],
	    "parameters": ["values"],
	    "steps": [10800],
	    "timestamp": "2012-12-22T03:00:00",
	    "title": "Surface Carbon Flux",
	    "units": {
	        "x": "degrees",
	        "y": "degrees",
	        "values": "&mu;mol/m&sup2;"
	    },
	    "var_name": "casa_gfed_2004"
	}



*manage.py load* examples
-----------------------------------

Most basic example; assumes a configuration file exists at *./mydata/data_casa_gfed_3hrly.json*::
	
	$ python manage.py load -p ./data_casa_gfed.mat -m SpatioTemporalMatrix -n casa_gfed_2004

Specify an alternate config file to use::

	$ python manage.py load -p ./data_casa_gfed.mat -m SpatioTemporalMatrix -n casa_gfed_2004 -c ./config/casa_gfed.json

In the following example, the loader will look for a config file at ./data_casa_gfed.json and overwrite the *timestamp* and *var_name* parameters in that file with those provided as command line args::
    
    $ python manage.py load -p ./data_casa_gfed.mat -m SpatioTemporalMatrix -n casa_gfed_2004 -o "timestamp=2003-12-22T03:00:00;var_name=casa_gfed_2004"



**Removing data**
================================
    
Use the **manage.py remove** utility to remove datasets from the database.

::

    $ manage.py remove -n <collection_name>
        
    Required argument:
        -n, --collection_name    Collection name to be removed (MongoDB identifier)

*manage.py remove* example
-----------------------------------
   
::

	$ python manage.py remove -n casa_gfed_2004
	

**Renaming datasets**
================================
    
Use the **manage.py rename** utility to rename datasets in the database.

.. WARNING::
	It is important to use this utility for renaming rather than manually renaming datasets by interfacing directly with MongoDB because several metadata tables require corresponding updates.

::

    $ manage.py rename -n <collection_name> -r <new_name>
        
    Required arguments:
        -n, --collection_name    Name of the dataset name to be modified (MongoDB identifier)
        -r, --new_name           New name for the collection       

*manage.py rename* example
-----------------------------------
   
::

	$ python manage.py rename -n casa_gfed_2004 -r casa_2004


**Database diagnostics**
================================
Use the **manage.py db** utility to get diagnostic information on database contents::

    $ manage.py db [OPTIONAL ARGUMENTS]
    
    Requires one of the following flags:
    
        -l, --list_ids           Lists collection names in the database.
        
             Optional args with -l flag:
                 collections :   lists collections
                 metadata:       lists the collections w/ metadata entries
                 coord_index:    lists the collections w/ coord_index entries
                                     
        -n, --collection_name    Collection name for which to shows metadata
        
        -a, --audit              No argument required. Performs audit of the
                                 database, reporting any collections that are
                                 missing corresponding metadata/coord_index
                                 entries and any stale metadata/coord_index
                                 entries without corresponding collections
    
    Optional argument:
    
        -x, --include_counts     Include count of records within each listed
                                 collection. Valid only with a corresponding
                                 "-l collections" flag; ignored otherwise

*manage.py db* examples
-----------------------------------
        
List all collections and their number of records::

	$ python manage.py db -l collections -x


List all the collections with metadata entries::

    $ python manage.py db -l metadata


Show metadata for the collection with id "casa_gfed_2004"::

    $ python manage.py db -n casa_gfed_2004 


Audit the database::

    $ python manage.py db -a
    

**Module documentation**
=============================================
fluxpy.models
-------------
.. automodule:: fluxpy.models  
	:members:
	:show-inheritance:
	
fluxpy.mediators
----------------
.. automodule:: fluxpy.mediators  
	:members:
	:show-inheritance:

