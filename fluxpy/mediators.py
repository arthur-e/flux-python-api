'''
e.g. /ws4/idata/fluxvis/casa_gfed_inversion_results/1.zerofull_casa_1pm_10twr/Month_Uncert1.mat
'''

import ipdb
import datetime, os, sys, re, json, csv
import pandas as pd
import numpy as np
import scipy.io
import h5py
from pymongo import MongoClient
from fluxpy import DB, DEFAULT_PATH, RESERVED_COLLECTION_NAMES

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
        '''Transforms contents of Data Frame into JSON representation for MongoDB'''
        if collection_name in RESERVED_COLLECTION_NAMES:
            raise ValueError('The collection name provided is a reserved name')


class Grid3DMediator(Mediator):
    '''
    Mediator that understands single-valued, spatial data on a structured,
    longitude-latitude grid; two spatial dimensions, one value dimension (3D).
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


class Unstructured3DMediator(Mediator):
    '''
    Mediator that understands single-valued, spatial data with arbitrary
    positions given as longitude-latitude pairs; two spatial dimensions, one
    value dimension (3D).
    '''
    def fix(self, value, precision=5):
        return round(value, precision)
    
    def save_to_db(self, collection_name):
        super(Unstructured3DMediator, self).save_to_db(collection_name)

        # Drop the old collection; it will be recreated when inserting.
        r = self.client[self.db_name].drop_collection(collection_name)

        for inst in self.instances:
            df = inst.save()
            
            tpl = {
                'coordinates': [],
                'value': None,
                'error': None,
                'timestamp': None
            }

            features = []
            for i, series in df.iterrows():
                feature = dict(tpl)
                feature['coordinates'] = map(self.fix, [
                    series['x'],
                    series['y']
                ])
                feature['value'] = inst.__precision__(series['value'])
                feature['error'] = inst.__error_precision__(series['error'])
                feature['timestamp'] = inst.fields.t(series) #FIXME Use column slicing when available
                features.append(feature)

            if inst.params['geometry'].get('isCollection'):                
                j = self.client[self.db_name][collection_name].insert({
                    'features': features
                })
                
            else:
                for feature in features:
                    try:
                        j = self.client[self.db_name][collection_name].insert(feature)
                        
                    except:
                        ipdb.set_trace()#FIXME




