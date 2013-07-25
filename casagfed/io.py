import sys, site

############################
# Virtual environment setup
ALLDIRS = [
    '/usr/local/pythonenv/fluxvis-env/lib/python2.7/site-packages/'
    '../'
]

# Remember original sys.path
prev_sys_path = list(sys.path)

# Add each new site-packages directory
for directory in ALLDIRS:
    site.addsitedir(directory)

# Reorder sys.path so new directories are at the front
new_sys_path = []
for item in list(sys.path): 
    if item not in prev_sys_path: 
        new_sys_path.append(item) 
        sys.path.remove(item) 
sys.path[:0] = new_sys_path

# End setup
############

import datetime
from dateutil.relativedelta import *
import json, csv, pprint
import pandas as pd
import numpy as np
import scipy.io
import h5py

def hdf5_to_dataframe(path, var_name, limit=None, dt=None):
    '''
    Creates a DataFrame from an HDF5 file of CASA GFED surface fluxes. Will
    return a subset of the data frame, if desired, to <limit> number of columns.
    Assumes first two columns of input matrix are longitude and latitude,
    respectively.
    '''
    f = h5py.File(path)

    if dt is None:
        dt = datetime.datetime(2003, 12, 22, 3, 0, 0) # 2003-12-22 at 3 AM

    # Create column headers
    intervals = mat[var_name].shape[1] - 2 # Number of fluxes (Subtract 2 fields, lng and lat)
    cols = ['lng', 'lat']
    cols.extend([str(dt + relativedelta(hours=+(3*j))) for j in range(intervals)])

    # With pandas, make a DataFrame from the NumPy array
    df = pd.DataFrame(f.get(var_name)[:], columns=cols)

    if limit is not None:
        cols = cols[0:(limit + 2)]
        df = df.ix[:,cols]

    # Capture a new DataFrame with a MultiIndex
    return df.set_index(['lng', 'lat'])


def mat_to_dataframe(path, var_name, limit=None, dt=None):
    '''
    Creates a DataFrame from a Matlab file of CASA GFED surface fluxes. Will
    return a subset of the data frame, if desired, to <limit> number of columns.
    Assumes first two columns of input matrix are longitude and latitude,
    respectively.
    '''
    mat = scipy.io.loadmat(path)

    if dt is None:
        dt = datetime.datetime(2003, 12, 22, 3, 0, 0) # 2003-12-22 at 3 AM

    # Create column headers
    intervals = mat[var_name].shape[1] - 2 # Number of fluxes (Subtract 2 fields, lng and lat)
    cols = ['lng', 'lat']
    cols.extend([str(dt + relativedelta(hours=+(3*j))) for j in range(intervals)])

    # Create a data frame; in Vineet's surface flux example (CASA GFED 2004), there 2,635 index entries (grid cells) with 3010 columns (3008 time steps + 2 coordinates)
    df = pd.DataFrame(mat[var_name], columns=cols)

    if limit is not None:
        cols = cols[0:(limit + 2)]
        df = df.ix[:,cols]

    # Capture a new DataFrame with a MultiIndex
    dfm = df.set_index(['lng', 'lat'])

    # Created the following:
    #
    #    <class 'pandas.core.frame.DataFrame'>
    #    MultiIndex: 5 entries, (-166.5, 65.5) to (-164.5, 61.5)
    #    Columns: 3008 entries, 2003-12-22 03:00:00 to 2005-01-01 00:00:00
    #    dtypes: float64(3008)

    return dfm


def to_csv(dataframe, filename='casagfed_output_dataframe.csv'):
    '''
    Exports a CSV file from an input DataFrame of CASA GFED surface fluxes.
    '''
    dataframe.T.to_csv(filename, index=True) # Export the transpose


def to_json(dataframe, filename='casagfed_output_dataframe.json'):
    '''
    Exports a JSON file from an input DataFrame of CASA GFED surface fluxes.
    '''
    collection = []

    # Iterate over the transpose of the data frame
    for timestamp, series in dataframe.T.iterrows():
        features = []
        features.append([{
            'coordinates': kv[0],
            'flux': kv[1]
        } for kv in series.iterkv()])

        collection.append({
            'timestamp': timestamp,
            'features': features
        })

    with open(filename, 'wb') as stream:
        json.dump(collection, stream)


def to_geojson(dataframe, filename='casagfed_output_dataframe.json'):
    '''
    Exports a GeoJSON file from an input DataFrame of CASA GFED surface fluxes.
    '''
    features = []

    # Iterate over the transpose of the data frame
    for timestamp, series in dataframe.T.iterrows():
        features.append({
            'type': 'FeatureCollection',
            'properties': {
                'timestamp': timestamp
            },
            'features': [{
                    'type': 'Point',
                    'coordinates': kv[0],
                    'properties': {
                        'flux': kv[1]
                    }
            } for kv in series.iterkv()]
        })

    template = {
        'type': 'FeatureCollection',
        'features': features
    }

    with open(filename, 'wb') as stream:
        json.dump(template, stream)


if __name__ == '__main__':
    mat_to_csv('/gis_lab/project/NASA_ACOS_Visualization/Data/from_Vineet/data_casa_gfed_3hrly.mat', 'casa_gfed_2004')


