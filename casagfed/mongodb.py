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

import os, datetime, re
# http://labix.org/python-dateutil or http://labix.org/download/python-dateutil/python-dateutil-1.5.tar.gz
from dateutil.relativedelta import *
from casagfed.io import *
import json, csv, pprint
import pandas as pd
import numpy as np
import scipy.io
import h5py
from pymongo import MongoClient

client = MongoClient() # Defaults: MongoClient('localhost', 27017)
DB = 'fluxvis'
COLLECTION = 'casa_gfed_3hrly'
# PATH = '/gis_lab/project/NASA_ACOS_Visualization/Data/from_Vineet/data_casa_gfed_3hrly.mat'
PATH = '/usr/local/dev/fluxvis/_data_/data_casa_gfed_3hrly.mat'

def from_hdf5(path, var_name='Month_Uncert'):
    '''
    Creates a pandas DataFrame from an HDF5 (or new Matlab) file.
    '''
    # e.g. '/ws4/idata/fluxvis/casa_gfed_inversion_results/1.zerofull_casa_1pm_10twr/Month_Uncert1.mat'
    f = h5py.File(path)

    # With pandas, make a DataFrame from the NumPy array
    return pd.DataFrame(f.get(var_name)[:])


def bulk_hdf5_to_csv(dir_path, regex='^Month_Uncert[\.\w\-\d_]+.mat'):
    '''
    Generates many CSV files from a directory of HDF5 files.
    '''
    regex = re.compile(regex)
    ls = os.listdir(dir_path)

    for filename in ls:
        if regex.match(filename) is None:
            continue # Skip this file

        df = from_hdf5(os.path.join(dir_path, filename))
        df.to_csv('1.zerofull_casa_1pm_10twr_' + filename.rstrip('.mat') + '.csv')


def insert_bulk(path, var_name='casa_gfed_2004', col_num=None, dt=None):
    '''
    path        <str>               Path to a *.mat file to import
    var_name    <str>               The name of the Matlab variable that describes the matrix to be imported
    dt          <datetime.datetime> Defaults to 2003-12-22 at 3 AM
    '''
    dfm = mat_to_dataframe(path, var_name, col_num, dt)

    # Create summary statistics
    summary = stats(path)
    # summary['tags'] = ['casa', 'gfed', 'surface', 'flux', '3hourly']
    summary['about_collection'] = COLLECTION
    summary['timestamp_start'] = datetime.datetime.strptime(dfm.columns.values[0], '%Y-%m-%d %H:%M:%S')
    summary['timestamp_end'] = datetime.datetime.strptime(dfm.columns.values[intervals - 1], '%Y-%m-%d %H:%M:%S')

    # Insert summary statistics
    i = client[DB]['summary_stats'].insert(summary)

    # Iterate over the transpose of the data frame
    i = 1
    for timestamp, series in dfm.T.iterrows():
        # Grab the unique identifier returned from an insert operation
        j = client[DB][COLLECTION].insert({
            '_id': i,
            'tags': ['surface', 'flux'],
            'timestamp': datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S'),
            'features': [{
                'coordinates': kv[0],
                'flux': kv[1]
            } for kv in series.iterkv()]
        })

        i += 1


def stats(path, var_name='casa_gfed_2004'):
    '''
    Calculates and returns summary statistics from CASA GFED surface fluxes.
    '''
    mat = scipy.io.loadmat(path)    
    intervals = mat[var_name].shape[1] - 2 # Number of fluxes (Subtract 2 fields, lng and lat)

    # Create a data frame; in Vineet's surface flux example (CASA GFED 2004), there 2,635 index entries (grid cells) with 3010 columns (3008 time steps + 2 coordinates)
    df = pd.DataFrame(mat[var_name])

    # Axis 0 is the "row-wise" axis, which doesn't make sense but gets the job done
    stats = {
        'mean': df.mean(0)[2:].mean(),
        'min': df.min(0)[2:].min(),
        'max': df.max(0)[2:].max(),
        'std': df.std(0)[2:].std(),
        'median': df.median(0)[2:].median()
    }

    stats['median_values_1std'] = [
        stats['median'] - stats['std'],
        stats['median'] + stats['std']
    ]

    stats['median_values_2std'] = [
        stats['median'] - (2 * stats['std']),
        stats['median'] + (2 * stats['std'])
    ]

    stats['mean_values_1std'] = [
        stats['mean'] - stats['std'],
        stats['mean'] + stats['std']
    ]

    stats['mean_values_2std'] = [
        stats['mean'] - (2 * stats['std']),
        stats['mean'] + (2 * stats['std'])
    ]

    return stats;


if __name__ == '__main__':
    if len(sys.argv) > 1:
        insert_bulk(sys.argv[1])

    else:
        insert_bulk(PATH)


