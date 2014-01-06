import datetime, os, sys, re, json, csv
import pandas as pd
import numpy as np
import scipy.io
import h5py
from dateutil.relativedelta import *
from pymongo import MongoClient
from fluxpy import DB, COLLECTION, INDEX_COLLECTION, DEFAULT_PATH

client = MongoClient() # Defaults: MongoClient('localhost', 27017)

class TransformationInterface:
    '''
    An abstract persistence transformation interface (modified from
    Andy Bulka, 2001), where save() and dump() methods are defined in
    subclasses. The save() method may take unique arguments as optional keyword
    arguments (they must default to None). The dump() method must take only one
    argument which is the interchange datum (a dictionary).
    '''
    def __init__(self, path, config=None):
        if config is None:
            # Check to see if a config file with the same name exists
            config = os.path.join('.'.join(path.split('.')[:-1]), '.json')
            if not os.path.exists(config):
                raise AttributeError('No configuration file (*.json) was provided')
            
        self.config = json.load(open(config, 'rb'))
    
    def save(self):
        pass
    
    def dump(self, data):
        pass #TODO Allow for formats to be specified?
        
    def get_id(self):
        pass


class Mediator:
    '''
    A generic model for transforming data between foreign formats and the
    persistence layer of choice (MongoDB in this application). Mediator calls
    the save() method on subclasses of the TransformationInterface (those
    classes that interpret foreign formats).
    '''

    def __init__(self, path):
        if path is None:
            raise AttributeError('A file path must be specified')
            
        self.filename = path

    def save_to_db(self):
        pass
        
    def load_from_db(self);
        pass


class XCO2Matrix(TransformationInterface):
    '''
    Understands XCO2 data as formatted--Typically 6-day spans of XCO2
    concentrations (ppm) at daily intervals on a latitude-longitude grid.
    Matrix dimensions: 1311 (observations) x 6 (days).
    Columns: Longitude, latitude, XCO2 concentration (ppm), day of the year,
    year, retrieval error (ppm).
    '''
    path_regex = re.compile(r'.+\.(mat|h5)')
    config = {
        'var_name': 'XCO2',
        'start': None,
        'interval': 86400000 # 1 day (daily)
    }

    def __init__(self, path, config=None):
        if self.path_regex.match(path) is None:
            raise AttributeError('Only Matlab (*.mat) and HDF5 (*.h5 or *.mat) files are accepted')
            
        if config is not None and os.path.exists(config):
            # Override the default configuration (on the class)
            self.config = json.load(open(config, 'rb'))
        
        self.filename = path
        
    def dump(self, data):
        # Restores the file from the interchange format (dictionary)
        pass
        
    def save(self, var_name=None, start=None, interval=None):
        # Called by a Mediator class member; should return data in interchange (dictionary)
        var_name = var_name or self.config['var_name']
        start = start or self.config['start']
        interval = interval or self.config['interval']
        
        # e.g. '/ws4/idata/fluxvis/casa_gfed_inversion_results/1.zerofull_casa_1pm_10twr/Month_Uncert1.mat'
        f = h5py.File(self.filename)
        
        df = pd.DataFrame(f.get(var_name)[:])


