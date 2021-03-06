Carbon Data Explorer Python API
===============================

The **Carbon Data Explorer**'s Python API for MongoDB ("flux-python-api").
The Carbon Data Explorer has been tested with MongoDB versions 1.4.9, 2.4.14, and 3.0.2; it should be compatiable with all 1.x, 2.x, and 3.x versions of MongoDB.

* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

Installation and Setup
======================

Installation of the Python dependencies is simple with `pip`:

    $ python setup.py install


The dependencies this covers includes:

* `libopenblas-dev`
* `liblapack-dev`
* `libxml2` and `libxml2-dev`
* `libhdf5-serial-dev`
* `libxslt1-dev`
* `libgeos` (Tested with version 3.4.2)
* MongoDB (Tested with version 1.4.9)

Installing within a Python Virtual Environment (recommended)
-------------------------------------------------------------

If you do not already have `virtuelenv` installed, see [full installation instructions](http://www.virtualenv.org/en/latest/virtualenv.html#installation).

Briefly, using [pip](http://www.pip-installer.org/en/latest/):

    $ [sudo] pip install virtualenv

The recommended location for your Python virtual environments is:

    /usr/local/pythonenv

But if you choose to put them elsewhere, just modify the variable on the first line of this next part:

    $ VENV_DIR=/usr/local/pythonenv
    $ virtualenv $VENV_DIR/flux-python-api-env
    $ source $VENV_DIR/flux-python-api-env/bin/activate
    $ python setup.py install

Ensure the virtualenv is accessible to non-root users:

    $ sudo chmod -R 775 $VENV_DIR/flux-python-api-env

And activate:

    $ source $VENV_DIR/flux-python-api-env/bin/activate

While your shell is activated, run `setup.py` (do **NOT** run as `sudo`):

    $ cd /where/my/repo/lives/flux-python-api
    $ python setup.py install

Finally, deactivate the virtual environment:

    $ deactivate

All done!

Installing without a Python Virtual Environment
-------------------------------------------------

If not using a python virtual environment, simply run `setup.py`:

    $ cd /where/my/repo/lives/flux-python-api
    $ sudo python setup.py install


Adding "fluxpy" to the Python Path
----------------------------------

    $ echo "/usr/local/project/flux-python-api/" > /usr/local/pythonenv/flux-python-api-env/lib/python2.7/site-packages/fluxpy.pth


* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

Manage.py Quick Reference
=========================

Use the `manage.py` utility to interact with the `Carbon Data Explorer` MongoDB via command line. The utility can be used to load data, rename existing datasets, remove data, and get diagnostics on database contents.

Note: **MongoDB** uses the term *collections* to refer to what most other databases usually call *tables*; hence the references to "collections" in the following documentation.

Loading Data
------------

Use the `manage.py load` utility to load geospatial data from files that are in **Matlab** (`*.mat`) or **HDF5** (`*.h5` or `*.mat`) format. A description of the required configuration file and examples are provided in the next sections.

Loading with `manage.py load`:

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


### The Configuration File

This utility requires that the input `*.h5` or `*.mat` file be accompanied by a **JSON configuration file** specifying required metadata parameters.
By default, the utility will look for a `*.json` file with the same name as the data file, but you can specify an alternate location by using the `-c` option.

Configuration file parameter schema:

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

    "units": Object,            // The measurement units, per parameter

    "var_name": String          // The name of the variable in the hierarchical
                                // file which stores the data


The contents of an **example configuration file** are shown here:

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



### `manage.py load` Examples

This is the most basic example; it assumes a configuration file exists at `./mydata/data_casa_gfed_3hrly.json`:

    $ python manage.py load -p ./data_casa_gfed.mat -m SpatioTemporalMatrix -n casa_gfed_2004

Specify an alternate config file to use:

    $ python manage.py load -p ./data_casa_gfed.mat -m SpatioTemporalMatrix -n casa_gfed_2004 -c ./config/casa_gfed.json

In the following example, the loader will look for a config file at `./data_casa_gfed.json` and overwrite the `timestamp` and `var_name` parameters in that file with those provided as command line args:

    $ python manage.py load -p ./data_casa_gfed.mat -m SpatioTemporalMatrix -n casa_gfed_2004 -o "timestamp=2003-12-22T03:00:00;var_name=casa_gfed_2004"


Removing Datasets
-----------------

Use the `manage.py remove` utility to remove datasets from the database.

    $ manage.py remove -n <collection_name>

    Required argument:
        -n, --collection_name    Name of the dataset to be removed (MongoDB identifier)

### `manage.py remove` example

    $ python manage.py remove -n casa_gfed_2004


Renaming Datasets
-----------------

Use the `manage.py rename` utility to rename datasets in the database.

.. WARNING::
    It is very important to use this utility for renaming datasets rather than manually renaming datasets by interfacing directly with MongoDB because several metadata tables require corresponding updates.

    $ manage.py rename -n <collection_name> -r <new_name>

    Required arguments:
        -n, --collection_name    Name of the dataset to be modified  (MongoDB identifier)
        -r, --new_name           New name for the dataset

### `manage.py rename` example

    $ python manage.py rename -n casa_gfed_2004 -r casa_2004


Database Diagnostics
--------------------

Use the `manage.py db` utility to get diagnostic information on database contents:

    $ manage.py db [OPTIONAL ARGUMENTS]

    Requires one of the following flags:

        -l, --list_ids           Lists dataset names in the database.

            Optional args with -l flag:
                collections :   lists datasets
                metadata:       lists the datasets having metadata entries
                coord_index:    lists the datasets having coord_index entries

        -n, --collection_name   Name of the dataset for which to show metadata

        -a, --audit             No argument required. Performs audit of the
                                database, reporting any datasets that are
                                missing corresponding metadata/coord_index
                                entries and any stale metadata/coord_index
                                entries without corresponding datasets

    Optional argument:

        -x, --include_counts    Include count of records within each listed
                                dataset. Valid only with a corresponding
                                "-l collections" flag; ignored otherwise

### `manage.py db` Examples

List all datasets and their number of records:

    $ python manage.py db -l collections -x


List all the datasets with metadata entries:

    $ python manage.py db -l metadata


Show metadata for the dataset with id "casa_gfed_2004":

    $ python manage.py db -n casa_gfed_2004


Audit the database:

    $ python manage.py db -a


* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

API Quick Reference
===================

This sections describes methods for loading data using the API directly rather than through `manage.py` utility.

Loading Data with Mediators
----------------------------

Given the examples of gridded (kriged) carbon concentration data (XCO2) in a Matlab file,
here is the process for loading these data into the MongoDB database.

    from fluxpy.mediators import Grid3DMediator
    from fluxpy.models import XCO2Matrix

    # The mediator understands how 3D gridded data should be stored
    mediator = Grid3DMediator()

    # Create an instance of the XCO2Matrix data model; parameters are loaded
    #   from a parameter file with the same name (e.g. xco2_data.json) if it
    #   exsists but otherwise are set as optional keyword arguments
    xco2 = KrigedXCO2Matrix('xco2_data.mat', timestamp='2009-06-15')

    # Save it to the database using the collection name provided
    mediator.save('test_r2_xco2', xco2)


Loading Data with a Suite
-------------------------

Sometimes, a dataset is more complicated than currently defined Models and Mediators are designed to handle.
For complicated use cases or bulk imports, a `Suite` class is available as a demonstration in the `utils` module.
The `Suite` class has helpful methods like `get_listing()` which returns a file listing for files of a certain type in a certain location (useful for iterating over files in bulk).
`Suite` should be extended for your use case (see `workflow.py`), but each `Suite` instance or subclass instance should have a `main()` function that is called to load data into MongoDB.
**The `main()` function is where your special needs are defined.**
For example, if you need to calculate something based on all of the files before loading them in one by one, use `main()` to preempt the call to your Mediator's `save()` method with whatever you need to do e.g.:

    def main(self):
        files_to_be_imported = self.get_listing()

        for each in files_to_be_imported:
            self.do_something(each)

        result = self.get_result()

        for each in files_to_be_imported:
            instance = self.model(each)
            self.mediator.save(collection_name, each, bulk_property=result)

* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

API Documentation
=================

The transformation of data from binary or hierarchical flat files to a database representation is facilitated by two Python classes, Models and Mediators, which are loosely based on the Transformation Interface described by Andy Bulka (2001).
The Model (`TransformationInterface`) class is a data model that describes what a scientific dataset looks like; whether it is a time series of gridded maps or a covariance matrix, for instance.
The Mediator class describes how a given Model should be read from and the data it contains translated to a database representation.
Some basic Mediator and Model classes are already provided in `mediators.py` and `models.py`, respectively.
If the included classes do not fit your needs (do not fit the format of your data), you can create Mediator and Model subclasses.
This is described below.

Creating a Custom Data Model (Transformation Interface Subclass)
----------------------------------------------------------------

A `TransformationInterface` subclass should provide the following methods (if they differ in function from the default behavior).
Some of these methods are (implied to be) private, however, you may need to override them for special file types.
Private methods include:

* `__init__`: The only thing the subclass' init method should do is set default metadata values, e.g.:

    self.precision = 2
    self.columns = ['x', 'y']
    self.formats = {
        'x': '%.5f',
        'y': '%.5f'
    }

* `__open__`: A method which takes a file path and an optional variable name (if the file works like a key-value store, as HDF and Matlab files do). This method should set the `file` and `file_handler` instance attributes; `file` should be a reference to the opened file (by calling the `file_handler` method).

The only two public methods that are required are `describe()` and `extract()`:

* `describe()`: A method which generates metadata for a given file. This method should set and return the instance `__metadata__` attribute.
* `extract()`: A method which "extracts" data from the file; it should return a pandas data frame of the data in a tabular format that is expected by the `Mediator` instance you intend to give it to (the `Mediator` instance takes your `TransformationInterface` instance (or subclass instance) and sticks the data it contains in the database).

Creating a Custom Mediator (Mediator Subclass)
----------------------------------------------

A `Mediator` subclass is more complicated.
It can provide, but is not required to provide, methods for reading data from the database and creating a `TransformationInterface` class or subclass instance that contains the data.
Normally, it is used to read such an instance and put the data in the database.
Public methods should include:

* `load()`: If you wish to be able to read data from the database and create a `TransformationInterface` class or subclass instance (one step towards writing a file from the database), you will need to provide this method, which reads out data from the database.
* `copy_grid_geometry()`: For gridded data only: Inserts the grid geometry into the database.
* `generate_metadata()`: Creates an entry in the metadata collection for this instance of data; updates the summary statistics of that entry if it already exists.
* `save()`: Creates new records in the database for the data contained in a provided `TransformationInterface` instance or subclass instance.
* `summarize()`: Generates summary statistics by parameter over the data in a collection; updates these summary statistics when new records are added to an existing dataset (scenario).
