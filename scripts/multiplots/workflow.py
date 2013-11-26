'''
Functions from the workflow for reproducing the carbon flux multiplots.
'''
import ipdb #FIXME
import sys, datetime, json, csv
import pandas as pd
import numpy as np
from shapely import wkt
from shapely.geometry import shape
from pymongo import MongoClient

client = MongoClient() # Defaults: MongoClient('localhost', 27017)
DB = 'fluxvis'
COLLECTION = 'casa_gfed_3hrly'
FLUX_PRECISION = 2
INDEX_COLLECTION = 'coord_index'
START = datetime.datetime.strptime('2004-01-01T00:00:00', '%Y-%m-%dT%H:%M:%S')
END = datetime.datetime.strptime('2004-12-22T03:00:00', '%Y-%m-%dT%H:%M:%S')

def flux_magnitudes_table(aggr='mean', plot_interval='M', frame_interval='3H'):
    '''
    Tabulates the flux magnitudes over a certain time period where the rows
    are the model cells and the columns are a convolution of the frame and plot
    intervals e.g. columns for yearly plots of monthly frames are labeled
    201201, 201202, 201203, ..., 201212.
    ''' 
    cell_count = len(client[DB][INDEX_COLLECTION].find_one()['i'])
       
    cursor = client[DB][COLLECTION].find({
        '_id': {
            '$gte': START,
            '$lte': END
        }
    }).sort([('_id', 1)])

    # Create an index of 3-hour intervals
    date_index = pd.date_range(START.strftime('%Y%m%d%H%M%S'),
        periods=cursor.count(), freq='3H', tz='UTC')
        
    # This is the aggregator in time; functions that are array-valued
    if aggr in ('mean', 'median', 'min', 'max'):
        aggregator = aggr

    elif aggr == 'net':
        aggregator = sum

    elif aggr == 'positive':
        aggregator = lambda x: sum(map(lambda y: y if y > 0 else 0, x))

    elif aggr == 'negative':
        aggregator = lambda x: sum(map(lambda y: y if y < 0 else 0, x))
        
    data_frame = pd.DataFrame(columns=date_index, index=range(0, cell_count))
    
    for window in cursor:
        data_frame[window['_id']] = window['values']
        
    return data_frame


if __name__ == '__main__':
    pass
