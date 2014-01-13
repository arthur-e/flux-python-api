'''
e.g. /ws4/idata/fluxvis/casa_gfed_inversion_results/1.zerofull_casa_1pm_10twr/Month_Uncert1.mat
'''

import ipdb#FIXME
import datetime, os, sys, re, json, csv
import pandas as pd
import numpy as np
import scipy.io
import h5py
from dateutil.relativedelta import *
from pymongo import MongoClient
from fluxpy import DB, DEFAULT_PATH, RESERVED_COLLECTION_NAMES

class TransformationInterface:
    '''
    An abstract persistence transformation interface (modified from
    Andy Bulka, 2001), where save() and dump() methods are defined in
    subclasses. The save() method may take unique arguments as optional keyword
    arguments (they must default to None). The dump() method must take only one
    argument which is the interchange datum (a dictionary). A configuration
    file may be provided as a *.json file with the same name as the data file.
    '''
    defaults = {
        'var_name': None, # The Matlab/HDF5 variable of interst
        'interval': None, # The time interval (ms) between observations (documents)
        'range': None, # The amount of time (ms) for which the measurements are valid after the timestamp
        'columns': None, # The column order
        'header': None, # The human-readable column headers, in order
        'units': None, # The units of measurement, in order
        'fields': { # Lambda functions, operating on Series or sequences, for accessing fields
            'x': None,
            'y': None,
            't': None,
            'ident': None,
            'value': None,
            'error': None
        }
    }

    def __init__(self, path):
        # Check to see if a params file with the same name exists
        params = os.path.join('.'.join(path.split('.')[:-1]), '.json')
        if os.path.exists(params):
            self.params = json.load(open(params, 'rb'))

        else:
            self.params = self.defaults

    def __error_precision__(self, value):
        return round(value, 4)

    def __precision__(self, value):
        return round(value, 2)

    def dump(self, data):
        pass

    def save(self, *args, **kwargs):
        pass


class Mediator(object):
    '''
    A generic model for transforming data between foreign formats and the
    persistence layer of choice (MongoDB in this application). Mediator calls
    the save() method on subclasses of the TransformationInterface (those
    classes that interpret foreign formats).
    '''

    def __init__(self, client=None, db_name=DB):
        self.client = client or MongoClient() # The MongoDB client; defaults: MongoClient('localhost', 27017)
        self.db_name = db_name # The name of the MongoDB database
        self.instances = [] # Stored model instances
        
    def add(self, *args, **kwargs):
        '''Add model instances; set optional parameter overrides for all instances added'''
        for each in args:
            for key, value in kwargs.items():
                each.params[key] = value
                
            self.instances.append(each)

        return self
        
    def load_from_db(self):
        pass
        
    def parse_timestamp(self, timestamp):
        '''Parses an ISO 8601 timestamp'''
        try:
            return datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
            
        except ValueError:
            return datetime.datetime.strptime(timestamp, '%Y-%m-%d')
        
    def save_to_db(self, collection_name):
        if collection_name in RESERVED_COLLECTION_NAMES:
            raise ValueError('The collection name provided is a reserved name')
            
    def update_summary_stats(self, collection_name):
        pass


class Grid3DMediator(Mediator):
    '''
    Mediator that understands single-valued, spatial data on a structured,
    latitude-longitude grid; two spatial dimensions, one value dimension (3D).
    Geometry expected as grid centroids (e.g. centroids of 1-degree grid cells).
    '''

    def save_to_db(self, collection_name):
        super(Grid3DMediator, self).save_to_db(collection_name)
        
        # Drop the old collection; it will be recreated when inserting.
        r = self.client[self.db_name].drop_collection(collection_name)

        for inst in self.instances:
            df = inst.save()
            
            # Expect that a valid timestamp was provided
            timestamp = inst.params['timestamp']
            
            # Create the index of grid cell coordinates
            i = self.client[self.db_name]['coord_index'].insert({
                '_id': collection_name,
                'i': [i for i in df.apply(lambda c: [c['x'], c['y']], 1)]
            })

            # Create the data document itself            
            j = self.client[self.db_name][collection_name].insert({
                '_id': self.parse_timestamp(timestamp),
                '_range': int(inst.params['range']) or None,
                'values': [v for v in df['value']],
                'errors': [e for e in df['error']]
            })

        #TODO After instances are saved, call self.update_summary_stats()


class XCO2Matrix(TransformationInterface):
    '''
    Understands XCO2 data as formatted--Typically 6-day spans of XCO2
    concentrations (ppm) at daily intervals on a latitude-longitude grid.
    Matrix dimensions: 1311 (observations) x 6 (attributes).
    Columns: Longitude, latitude, XCO2 concentration (ppm), day of the year,
    year, retrieval error (ppm).
    '''
    defaults = {
        'var_name': 'XCO2',
        'interval': 86400000, # 1 day (daily) in ms
        'columns': ('x', 'y', 'value', None, None, 'error'),
        'header': ('lng', 'lat', 'xco2_ppm', 'day', 'year', 'error_ppm'),
        'units': ('degrees', 'degrees', 'ppm', None, None, 'ppm^2'),
        'fields': {
            'x': lambda s: s[0],
            'y': lambda s: s[1],
            't': lambda s: datetime.datetime(int(s[4]), 1, 1) + datetime.timedelta(days=s[3]),
            'ident': lambda s: None,
            'value': lambda s: s[2],
            'error': lambda s: s[5]
        }
    }

    path_regex = re.compile(r'.+\.(?P<extension>mat|h5)')

    def __init__(self, path, **kwargs):
        if self.path_regex.match(path) is None:
            raise AttributeError('Only Matlab (*.mat) and HDF5 (*.h5 or *.mat) files are accepted')

        if self.path_regex.match(path).groupdict().get('extension') == 'mat':
            self.file_handler = scipy.io.loadmat

        else:
            self.file_handler = h5py.File
            
        self.params = {}

        # Check to see if a params file with the same name exists
        params = os.path.join('.'.join(path.split('.')[:-1]), '.json')
        if os.path.exists(params):
            self.params = json.load(open(params, 'rb'))
        
        for (key, value) in self.defaults.items():    
            self.params.setdefault(key, value)

        # Overrides in this instance
        self.params.update(kwargs)
        
        self.filename = path

    def dump(self, data):
        pass

    def save(self, *args, **kwargs):
        pass


class KrigedXCO2Matrix(XCO2Matrix):
    '''
    Understands Kriged XCO2 data as formatted--Typically 6-day spans of XCO2
    concentrations (ppm) at daily intervals on a latitude-longitude grid.
    Matrix dimensions: 14,210 (model cells) x 9 (attributes).
    Columns: Longitude, latitude, XCO2 concentration (ppm), retrieval error (ppm)
    '''
    defaults = {
        'var_name': 'krigedData',
        'interval': None,
        'range': 518400000, # 6 days
        'columns': ('y', 'x', 'value', 'error', '', '', '', '', ''),
        'header': ('lat', 'lng', 'xco2_ppm', 'error_ppm^2', '', '', '', '', ''),
        'units': ('degrees', 'degrees', 'ppm', 'ppm^2')
    }
    
    def __precision__(self, value):
        return round(value, 2)
        
    def dump(self, data):
        # Restores the file from the interchange format
        pass
        
    def save(self, *args, **kwargs):
        # Called by a Mediator class member; should return data in interchange
        var_name = kwargs.get('var_name') or self.params.get('var_name')
        timestamp = kwargs.get('timestamp') or self.params.get('timestamp')
        
        if not all((var_name, timestamp)):
            raise AttributeError('One or more required configuration parameters were not provided')
        
        # HDF5/Matlab file interface
        f = self.file_handler(self.filename)
        
        # Data frame
        df = pd.DataFrame(f.get(var_name)[:], columns=self.params['columns'])
        
        # Fix the precision of data values
        df['value'] = df['value'].apply(self.__precision__)
        df['error'] = df['error'].apply(self.__error_precision__)
        
        return df




