##########################
# Installation and Setup #
##########################

    cat > /usr/local/pythonenv/fluxvis-env/lib/python2.7/site-packages/fluxpy.pth
    # Write in: /usr/local/project/flux-python-api/

####################################
# Working with CASA-GFED Flux Data #
####################################

The `casagfed2mongo` module contains a number of functions for working with CASA-GFED modeled surface fluxes.

## Importing from Matlab/HDF5 Files

You can import directly from an older Matlab file using `scipy.io`:

    mat = scipy.io.loadmat('/path/to/file.mat')

    # Variables are indexed by their names:
    my_variable = mat['my_variable']

Tools are available for a importing both Matlab and HDF5 model data in a more manageable (transposed) format, where the model windows (in time) are rows of the table and model cells are the columns:

    from casagfed.io import mat_to_dataframe, hdf5_to_dataframe

    # Get a pandas Data Frame in return; skips the first 2 columns (e.g. latitude and longitude)
    df = mat_to_dataframe('/path/to/file.mat', variable_name)

    # Same procedure for HDF5 files
    df = hdf5_to_dataframe('/path/to/file.mat', variable_name)

The `variable_name` is the Matlab variable name of the matrix for which you want to get a CSV.

## Exporting to CSV

For older Matlab files:

    mat = scipy.io.loadmat('/path/to/file.mat')
    df = pd.DataFrame(mat[variable_name])
    df.to_csv('output_filename.csv')

For HDF5 files, again generating a transposed matrix from the original:

    from casagfed.io import hdf5_to_dataframe, to_csv

    # Writes a CSV file in the current directory; skips the first 2 columns (e.g. latitude and longitude)
    to_csv(hdf5_to_dataframe('path_to_file.mat', variable_name)

In each case, the `variable_name` is the Matlab variable name of the matrix for which you want to get a CSV.

##########################
# MongoDB Administration #
##########################

## Insertion

Tools are avaialble for performing a bulk insert into MongoDB; here we assume a non-HDF5 Matlab file:

    from casagfed.mongodb import insert_bulk

    # The starting date and time need to be provided as a datetime.datetime instance
    insert_bulk('/path/to/file.mat', variable_name, dt=datetime.datetime(2004, 1, 1))
