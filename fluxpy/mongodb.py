from __future__ import division
import os, sys, datetime, re, argparse
# http://labix.org/python-dateutil or http://labix.org/download/python-dateutil/python-dateutil-1.5.tar.gz
from dateutil.relativedelta import *
from fluxpy.transform import *
import json, csv, pprint
import pandas as pd
import numpy as np
import scipy.io
import h5py
from pymongo import MongoClient

client = MongoClient() # Defaults: MongoClient('localhost', 27017)
DB = 'fluxvis'
COLLECTION = 'casa_gfed_3hrly'
INDEX_COLLECTION = 'coord_index'
PATH = '/gis_lab/project/NASA_ACOS_Visualization/Data/from_Vineet/data_casa_gfed_3hrly.mat'
SCN_PATH = '/usr/local/dev/data/casa_gfed_inversion_results'

def insert_bulk(path, var_name='casa_gfed_2004', col_num=None, dt=None, precision=2):
    '''
    Inserts CASA GFED modeled surface flux documents (flux at different times)
    into a MongoDB database.
    '''
    def to_fixed(value):
        return round(value, 2)

    dfm = mat_to_dataframe(path, var_name, col_num, dt)

    # Drop the old collection. It will be recreated when inserting.
    r = client[DB].drop_collection(COLLECTION)

    if client[DB]['summary_stats'].find_one({'about_collection': COLLECTION}) is None:
        # Create summary statistics
        summary = stats(path)

        intervals = dfm.shape[1] - 2 # Number of fluxes (Subtract 2 fields, lng and lat)

        # summary['tags'] = ['casa', 'gfed', 'surface', 'flux', '3hourly']
        summary['about_collection'] = COLLECTION
        summary['timestamp_start'] = datetime.datetime.strptime(dfm.columns.values[0], '%Y-%m-%dT%H:%M:%S')
        summary['timestamp_end'] = datetime.datetime.strptime(dfm.columns.values[intervals - 1], '%Y-%m-%dT%H:%M:%S')

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
        # Insert the cell coord index once only
        if i == 1:
            j = client[DB][INDEX_COLLECTION].insert({'i':[kv[0] for kv in series.iterkv()]})

        i += 1
        update_progress(dfm.shape[1],i,"CASA-GFED Flux",False)
    update_progress(dfm.shape[1],i,"CASA-GFED Flux",True)


def insert_covariance(scn, scn_path, col_num=None, dt=None, precision=5):
    '''
    Inserts covariance data. 
    '''
    def to_fixed(value):
        return round(value, 5)

    # Each scenario has one annual uncertainty file and twelve monthly uncertainty files
    #   so we need to fetch all of them. 
    p = '/'.join([scn_path, scn])
    
    # Split the scenario id and the scenario name. Might want to use the scenario id later.
    sid,scn = scn.split('.')

    # Drop the old collection. It will be recreated when insert.
    r = client[DB].drop_collection(scn)

    # Start with annual uncertainty
    df = h5py.File(p + '/Ann_Uncert.mat')
    data = df.get('Ann_Uncert')[:]
    df.close()
    ann = {
        '_id':'annual',
        'v':[]
    }

    # Iterate over the data
    i = 0
    for cov in data:
        cov_limited = []
        for val in cov:
            cov_limited.append(to_fixed(val))

        # collection name? scn_uncert? scenario number vs scenario name?
        res = client[DB][scn].insert({'_id':'ann.'+`i`, 'v':cov_limited})
        i+=1
        update_progress(len(data), i, 'Ann_Uncert', False)


    t = 0
    #Rinse and repeat for each month
    for m in range(1,13):
        df = h5py.File(p + '/Month_Uncert'+`m`+'.mat')
        data = df.get('Month_Uncert')[:]
        df.close()
        i=0
        for cov in data:
            cov_limited = []
            for val in cov:
                cov_limited.append(to_fixed(val))
            res = client[DB][scn].insert({'_id':`m`+'.'+`i`, 'v':cov_limited})
            i+=1
            update_progress(len(data), i, 'Month_Uncert'+`m`,False)
    update_progress(len(data), i, 'Month_Uncert'+`m`,True)
        

def update_progress(tot, cur, title, clear=False):
    if (clear == False):
        progress = (cur/tot) * 100
        upd = '\r'+title+' progress '+'[{0:20}] {1:.1f}%'.format('#' * int((progress)/5), progress)
        sys.stdout.write(upd)
        sys.stdout.flush()
    else: 
        sys.stdout.write('\n')
        sys.stdout.flush()


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
    p = argparse.ArgumentParser(description='CASA-GFED data import tool')
    p.add_argument('-p','--path', type=str, 
        help='Specify the directory containing scenario subdirectories')
    p.add_argument('-s','--scenario', type=str, 
        help='Specify the scenario. This must match the ')
    p.add_argument('action', choices=['uncertainty','flux'],default='uncertainty',
        help='Select the default action')

    args = p.parse_args()

    if args.action == 'uncertainty':
        if args.scenario == None:
            p.error('--scenario must be set when action=uncertainty')
        if args.path == None:
            insert_covariance(args.scenario,SCN_PATH)
        else:
            insert_covariance(args.scenario,args.path)

    elif args.action == 'flux':
        insert_bulk(PATH)

    
