'''
e.g. /ws4/idata/fluxvis/casa_gfed_inversion_results/1.zerofull_casa_1pm_10twr/Month_Uncert1.mat
'''

import datetime, os, sys, re
import pandas as pd
import numpy as np
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
    Additional fields beyond the "value" field may be included; currently
    supported is the additional "error" field.
    '''
    def load_from_db(self, collection_name, query={}):
        
        # Retrieve a cursor to iterate over the records matching the query
        cursor = self.client[self.db_name][collection_name].find(query, {
            '_id': 0
            'values': 1,
            'errors': 1,
        })
        
        # Create an n x 2 matrix of the longitude-latitude coordinates
        coords = np.array(self.client[self.db_name]['coord_index'].find({
            '_id': collection_name
        }).next()['i'])
        
        # Create a DataFrame of longitude-latitude coordinates
        coords = pd.DataFrame(coords, columns=('x', 'y'))
        
        # Clear out any saved instances
        self.instances = []
        
        for record in cursor:
            # Create values and error Series; concatenate them as a DataFrame,
            #   then concatenate them with the coordinates DataFrame
            values = pd.Series(record['values'], dtype='float64', name='value')
            errors = pd.Series(record['errors'], dtype='float64', name='error')
            df = pd.concat([
                coords,
                pd.concat([values, errors], axis=1)
            ], axis=1)
            
            self.instances.append(df)
            
    def save_to_db(self, collection_name):
        super(Grid3DMediator, self).save_to_db(collection_name)

        for inst in self.instances:
            df = inst.save()

            # Expect that a valid timestamp was provided
            timestamp = inst.params.get('timestamp')
            if timestamp is None:
                raise AttributeError('Expected a model to have a "timestamp" parameter; is this the right model for this Mediator?')

            # Create the index of grid cell coordinates, if needed
            if self.client[self.db_name]['coord_index'].find({
                '_id': collection_name
            }) is None:
                i = self.client[self.db_name]['coord_index'].insert({
                    '_id': collection_name,
                    'i': [i for i in df.apply(lambda c: [c['x'], c['y']], 1)]
                })

            # Create the data document itself            
            j = self.client[self.db_name][collection_name].insert({
                '_id': self.parse_timestamp(timestamp),
                '_range': int(inst.params['range']) or None,
                'values': df['value'].tolist(),
                'errors': df['error'].tolist()
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

        for inst in self.instances:
            df = inst.save()
            
            features = []
            for i, series in df.iterrows():
                features.append({
                    'coordinates': [
                        series['x'],
                        series['y']
                    ],
                    'value': series['value'],
                    'error': series['error'],
                    'timestamp': series['timestamp']
                })

            if inst.params['geometry'].get('isCollection'):                
                j = self.client[self.db_name][collection_name].insert({
                    'features': features
                })
                
            else:
                for feature in features:
                    j = self.client[self.db_name][collection_name].insert(feature)




