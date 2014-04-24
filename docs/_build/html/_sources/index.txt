.. flux-python-api documentation master file, created by
   sphinx-quickstart on Thu Apr 24 13:54:13 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to **flux-python-api** documentation!
=============================================

Contents: buncha stuff!

.. toctree::
   :maxdepth: 2



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


Installation and Setup
================================

	Just, like, ask the IT guy.


Loading Data To/From MongoDB with Mediators
===========================================

Given the examples of gridded (kriged) and not-gridded XCO2 data, here is the
process for loading these data into the MongoDB database::

    from fluxpy.mediators import Grid3DMediator
    from fluxpy.models import XCO2Matrix
    
    # The mediator understands how 3D gridded data should be stored
    mediator = Grid3DMediator()
    
    # Create an instance of the XCO2Matrix data model; parameters are loaded
    #   from a parameter file with the same name (e.g. xco2_data.json) if it
    #   exists but otherwise are set as optional keyword arguments
    xco2 = KrigedXCO2Matrix('xco2_data.mat', timestamp='2009-06-15')
    
    # Add the instance to our mediator and save it to the database using
    #   the collection name provided
    mediator.add(xco2).save_to_db('my_xco2_data')


Working with CASA-GFED Flux Data
================================


Importing from Matlab/HDF5 Files
--------------------------------

You can import directly from an older Matlab file using `scipy.io`::

    mat = scipy.io.loadmat('/path/to/file.mat')

    # Variables are indexed by their names:
    my_variable = mat['my_variable']

Tools are available for a importing both Matlab and HDF5 model data in a more manageable (transposed) format, where the model windows (in time) are rows of the table and model cells are the columns::

    from casagfed.io import mat_to_dataframe, hdf5_to_dataframe

    # Get a pandas Data Frame in return; skips the first 2 columns (e.g. latitude and longitude)
    df = mat_to_dataframe('/path/to/file.mat', variable_name)

    # Same procedure for HDF5 files
    df = hdf5_to_dataframe('/path/to/file.mat', variable_name)

The `variable_name` is the Matlab variable name of the matrix for which you want to get a CSV.


Exporting to CSV
----------------

For older Matlab files::

    mat = scipy.io.loadmat('/path/to/file.mat')
    df = pd.DataFrame(mat[variable_name])
    df.to_csv('output_filename.csv')

For HDF5 files, again generating a transposed matrix from the original::

    from casagfed.io import hdf5_to_dataframe, to_csv

    # Writes a CSV file in the current directory; skips the first 2 columns (e.g. latitude and longitude)
    to_csv(hdf5_to_dataframe('path_to_file.mat', variable_name)

In each case, the `variable_name` is the Matlab variable name of the matrix for which you want to get a CSV.


MongoDB Administration
======================

Insertion
---------

Tools are available for performing a bulk insert into MongoDB; here we assume a non-HDF5 Matlab file::

    from casagfed.mongodb import insert_bulk

    # The starting date and time need to be provided as a datetime.datetime instance
    insert_bulk('/path/to/file.mat', variable_name, dt=datetime.datetime(2004, 1, 1))
    



