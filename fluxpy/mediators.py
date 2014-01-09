'''
e.g. /ws4/idata/fluxvis/casa_gfed_inversion_results/1.zerofull_casa_1pm_10twr/Month_Uncert1.mat
'''

import datetime, os, sys, re, json, csv
import pandas as pd
import numpy as np
import scipy.io
import h5py
from dateutil.relativedelta import *
from pymongo import MongoClient
from fluxpy import DB, COLLECTION, INDEX_COLLECTION, DEFAULT_PATH, RESERVED_COLLECTION_NAMES

client = MongoClient() # Defaults: MongoClient('localhost', 27017)

class TransformationInterface:
    '''
    An abstract persistence transformation interface (modified from
    Andy Bulka, 2001), where save() and dump() methods are defined in
    subclasses. The save() method may take unique arguments as optional keyword
    arguments (they must default to None). The dump() method must take only one
    argument which is the interchange datum (a dictionary). A configuration
    file may be provided as a *.json file with the same name as the data file.
    '''
    def __init__(self, path):
        # Check to see if a params file with the same name exists
        params = os.path.join('.'.join(path.split('.')[:-1]), '.json')
        if os.path.exists(params):
            self.params = json.load(open(params, 'rb'))

        else:
            self.params = self.defaults

    def config(self, key, value=None):
        if value is not None:
            self.params[key] = value
        
        return self.params[key]

    def dump(self, data):
        pass #TODO Allow for formats to be specified?
    
    def save(self):
        pass


class Mediator:
    '''
    A generic model for transforming data between foreign formats and the
    persistence layer of choice (MongoDB in this application). Mediator calls
    the save() method on subclasses of the TransformationInterface (those
    classes that interpret foreign formats).
    '''

    def __init__(self, client, db_name=DB):
        self.client = client # The MongoDB client
        self.db_name = db_name # The name of the MongoDB database
        self.instances = [] # Stored model instances
        
    def add(self, inst):
        self.instances.append(inst)
        return self
        
    def load_from_db(self):
        pass
        
    def save_to_db(self, collection_name):
        if collection_name in RESERVED_COLLECTION_NAMES:
            raise ValueError('The collection name provided is a reserved name')
            
    def update_summary_stats(self, collection_name):
        pass


class 4DGridMediator(Mediator):
    '''
    Mediator that understands single-valued, spatio-temporal (4D) data on
    a structure, latitude-longitude grid.
    '''

    def __precision__(self, value):
        return round(value, 2)

    def save_to_db(self, collection_name):
        super(4DGridMediator, self).save_to_db(collection_name)

        # Drop the old collection; it will be recreated when inserting.
        r = self.client[self.db_name].drop_collection(collection_name)

        for inst in self.instances:
            df = inst.save()
            #TODO Resulting dataframe
            pass

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
        'timestamp': None,
        'interval': 86400000, # 1 day (daily) in ms
        'columns': ('lng', 'lat', 'value', None, None, 'error'),
        'header': ('lng', 'lat', 'xco2_ppm', 'day', 'year', 'error_ppm'),
        'units': ('degrees', 'degrees', 'ppm', None, None, 'ppm^2'),
        'fields': {
            'lng': lambda s: s[0],
            'lat': lambda s: s[1],
            'value': lambda s: s[2],
            'timestamp': lambda s: datetime.datetime(int(s[4]), 1, 1) + datetime.timedelta(days=s[3]),
            'error': lambda s: s[5]
        }
    }

    path_regex = re.compile(r'.+\.(?P<extension>mat|h5)')

    def __init__(self, path, timestamp=None, var_name=None):
        if self.path_regex.match(path) is None:
            raise AttributeError('Only Matlab (*.mat) and HDF5 (*.h5 or *.mat) files are accepted')

        if self.path_regex.match(path).groupdict().get('extension') == 'mat':
            self.file_handler = scipy.io.loadmat

        else:
            self.file_handler = h5py.File

        # Check to see if a params file with the same name exists
        params = os.path.join('.'.join(path.split('.')[:-1]), '.json')
        if os.path.exists(params):
            self.params = json.load(open(params, 'rb'))

        else:
            self.params = self.defaults

        # Overrides in this instance
        self.params['timestamp'] = timestamp
        self.params['var_name'] = var_name
        
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
        'timestamp': None,
        'interval': None,
        'columns': ('lng', 'lat', 'value', 'error'),
        'header': ('lng', 'lat', 'xco2_ppm', 'error_ppm^2'),
        'units': ('degrees', 'degrees', 'ppm', 'ppm^2'),
        'fields': {
            'lng': lambda s: s[0],
            'lat': lambda s: s[1],
            'value': lambda s: s[2],
            'timestamp': lambda s: None,
            'error': lambda s: s[3]
        }
    }
        
    def dump(self, data):
        # Restores the file from the interchange format (dictionary)
        pass
        
    def save(self, *args, **kwargs):
        # Called by a Mediator class member; should return data in interchange (dictionary)
        var_name = kwargs['var_name'] or self.params['var_name']
        timestamp = kwargs['timestamp'] or self.params['timestamp']
        
        if not all((var_name, timestamp)):
            raise AttributeError('One or more required configuration parameters were not provided')
        
        # HDF5/Matlab file interface
        f = self.file_handler(self.filename)
        
        # Data frame
        df = pd.DataFrame(f.get(var_name)[:], cols=self.params['columns'])
        
        return df




