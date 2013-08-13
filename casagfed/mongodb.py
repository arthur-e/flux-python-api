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
from io import *
import json, csv, pprint
import pandas as pd
import numpy as np
import scipy.io
import h5py
from pymongo import MongoClient

client = MongoClient() # Defaults: MongoClient('localhost', 27017)
DB = 'fluxvis'
COLLECTION = 'test_new'
INDEX_COLLECTION = 'test_index'
PATH = '/gis_lab/project/NASA_ACOS_Visualization/Data/from_Vineet/data_casa_gfed_3hrly.mat'
#PATH = '/usr/local/dev/fluxvis/_data_/data_casa_gfed_3hrly.mat'

def insert_bulk(path, var_name='casa_gfed_2004', col_num=None, dt=None, precision=2):
    '''
    Inserts CASA GFED modeled surface flux documents (flux at different times)
    into a MongoDB database.
    '''
    def to_fixed(value):
        return round(value, 2)

    dfm = mat_to_dataframe(path, var_name, col_num, dt)

    if client[DB]['summary_stats'].find_one({'about_collection': COLLECTION}) is None:
        # Create summary statistics
        summary = stats(path)

        intervals = dfm.shape[1] - 2 # Number of fluxes (Subtract 2 fields, lng and lat)

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
            '_id': datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S'),
            'values': [ round(kv[1], precision) for kv in series.iterkv()]
        })
        #Insert the cell coord index once only
        if i == 1:
            j = client[DB][INDEX_COLLECTION].insert({'i':[kv[0] for kv in series.iterkv()]})

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
        insert_bulk(sys.argv[1], sys.argv[2], gzip=sys.argv[3])

    else:
        insert_bulk(PATH)


