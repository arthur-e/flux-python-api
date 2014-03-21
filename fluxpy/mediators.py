'''
Example data: /ws4/idata/fluxvis/casa_gfed_inversion_results/1.zerofull_casa_1pm_10twr/Month_Uncert1.mat

from fluxpy.mediators import *
from fluxpy.models import *
mediator = Grid3DMediator()
xco2 = KrigedXCO2Matrix('xco2_data.mat', timestamp='2009-06-15')
mediator.add(xco2).save_to_db('my_xco2_data')
'''

import datetime
import os
import re
import sys
import pandas as pd
import numpy as np
from pymongo import MongoClient
from fluxpy import DB, DEFAULT_PATH, RESERVED_COLLECTION_NAMES

try:
    from hashlib import md5

except ImportError:
    import md5

class Mediator(object):
    '''
    A generic model for transforming data between foreign formats and the
    persistence layer of choice (MongoDB in this application). Mediator calls
    the extract() method on subclasses of the TransformationInterface (those
    classes that interpret foreign formats).
    '''

    def __init__(self, client=None, db_name=DB):
        self.client = client or MongoClient() # The MongoDB client; defaults: MongoClient('localhost', 27017)
        self.db_name = db_name # The name of the MongoDB database

    def __get_updates__(self, query, metadata):
        last_metadata = query.next()
        update_selection = {}

        # Check if the last date and the first new data are the same...
        if last_metadata['dates'][-1] != metadata['dates'][0]:
            new_dates = list(last_metadata['dates'])
            new_dates.extend(metadata['dates'])

            update_selection.update({
                'dates': new_dates
            })

        # Check if the last step and the first new step are the same...
        if last_metadata.has_key('steps'):
            if last_metadata.get('steps')[-1] != metadata.get('steps')[0]:
                new_steps = list(last_metadata.get('steps'))
                new_steps.extend(metadata.get('steps'))

                update_selection.update({
                    'steps': new_steps
                })

        # Check if the last span and the first new span are the same...
        if last_metadata.has_key('spans'):
            if last_metadata.get('spans')[-1] != metadata.get('spans')[0]:
                new_spans = list(last_metadata.get('spans'))
                new_spans.extend(metadata.get('spans'))

                update_selection.update({
                    'spans': new_spans
                })

        return update_selection

    def parse_timestamp(self, timestamp):
        '''Parses an ISO 8601 timestamp'''
        try:
            return datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
            
        except ValueError:
            return datetime.datetime.strptime(timestamp, '%Y-%m-%d')
        
    def save(self, collection_name, instance):
        '''Transforms contents of Data Frame into JSON representation for MongoDB'''
        if collection_name in RESERVED_COLLECTION_NAMES:
            raise ValueError('The collection name provided is a reserved name')


#TODO Compare to Grid4DMediator to make them both more DRY
class ImpliedGridMediator(Mediator):
    '''
    Mediator for what is essentially a matrix with only an implied grid--no
    spatial coordinate index (yet). Uses the coordinate index from an existing
    collection, specified as a new first argumet; can use the target
    collection name for this new required first argument if the target
    collection already exists.
    '''
    def __init__(self, coord_index_name=None, **kwargs):
        # Requires: Specify the name of a collection that already has a
        #   coordinate index
        self.coord_index_name = coord_index_name

        super(ImpliedGridMediator, self).__init__(**kwargs)

    def save(self, collection_name, instance):
        super(ImpliedGridMediator, self).save(collection_name, instance)

        df = instance.extract()

        # Create the index of grid cell coordinates, if needed
        if self.client[self.db_name]['coord_index'].find({
            '_id': collection_name
        }).count() == 0:
            coords = self.client[self.db_name]['coord_index'].find({
                '_id': self.coord_index_name or collection_name
            }).next()['i']

            k = self.client[self.db_name]['coord_index'].insert({
                '_id': collection_name,
                'i': coords
            })

        for i, series in df.iterrows():
            if instance.precision is not None:
                self.client[self.db_name][collection_name].insert({
                    '_id': '%s_%d' % (instance.timestamp, i),
                    'values': map(lambda x: round(x, instance.precision),
                        series.tolist())
                })

            else:
                self.client[self.db_name][collection_name].insert({
                    '_id': '%s_%d' % (instance.timestamp, i),
                    'values': series.tolist()
                })

        # Get the metadata; assume they are all the same
        metadata = instance.describe(df)

        # Set the unique identifier; include the summary statistics
        metadata['_id'] = collection_name
        metadata['stats'] = self.summarize(collection_name)

        if self.client[self.db_name]['metadata'].find({
            '_id': collection_name
        }).count() == 0:
            self.client[self.db_name]['metadata'].insert(metadata)

        else:
            update_selection = self.__get_updates__(query, metadata)

            # If anything's changed, update the database!
            if len(update_selection.items()) != 0:
                # Update the metadata
                self.client[self.db_name]['metadata'].update({
                    '_id': collection_name
                }, {
                    '$set': update_selection
                })

    def summarize(self, collection_name, query={}):
        df = self.load(collection_name, query)#TODO load() method

        return { # Axis 0 is the "row-wise" axis
            'mean': df.mean(0).mean(),
            'min': df.min(0).min(),
            'max': df.max(0).max(),
            'std': df.std(0).std(),
            'median': df.median(0).median()
        }


class Grid4DMediator(Mediator):
    '''
    Mediator that understands spatial data on a structured, longitude-latitude
    grid that vary in time; two spatial dimensions and an aribtrary number of
    time steps (frames). Geometry expected as grid centroids (e.g. centroids
    of 1-degree grid cells).
    '''
    values_precision = 2 #FIXME Should be done in the model

    def load(self, collection_name, query):
        # Retrieve a cursor to iterate over the records matching the query
        cursor = self.client[self.db_name][collection_name].find(query, {
            'values': 1,
        })
        
        # Create an n x 2 matrix of the longitude-latitude coordinates
        coords = np.array(self.client[self.db_name]['coord_index'].find({
            '_id': collection_name
        }).next()['i'])
        
        # Create a DataFrame of longitude-latitude coordinates
        coords = pd.DataFrame(coords, columns=('x', 'y'))

        series = []
        ids = []

        for record in cursor:
            values = pd.Series(record['values'], dtype='float64', name=record['_id'])
            series.append(values)
            ids.append(record.get('_id'))

        df = pd.concat([
            coords,
            pd.concat(series, axis=1)
        ], axis=1)

        # Capture a new DataFrame with a MultiIndex; promotes these columns to indexes
        dfm = df.set_index(['x', 'y'])

        return dfm

    def save(self, collection_name, instance):
        super(Grid4DMediator, self).save(collection_name, instance)

        df = instance.extract()

        # Create the index of grid cell coordinates, if needed
        if self.client[self.db_name]['coord_index'].find({
            '_id': collection_name
        }).count() == 0:
            k = self.client[self.db_name]['coord_index'].insert({
                '_id': collection_name,
                'i': list(df.index.values)
            })

        # Iterate over the transpose of the data frame
        for timestamp, series in df.T.iterrows():
            j = self.client[self.db_name][collection_name].insert({
                '_id': timestamp,
                'values': [
                    round(kv[1], self.values_precision) for kv in series.iterkv()
                ]
            })

        # Get the metadata; assume they are all the same
        metadata = instance.describe(df)

        # Set the unique identifier; include the summary statistics
        metadata['_id'] = collection_name
        metadata['stats'] = self.summarize(collection_name)

        if self.client[self.db_name]['metadata'].find({
            '_id': collection_name
        }).count() == 0:
            self.client[self.db_name]['metadata'].insert(metadata)

        else:
            update_selection = self.__get_updates__(query, metadata)

    def summarize(self, collection_name, query={}):
        df = self.load(collection_name, query)

        return { # Axis 0 is the "row-wise" axis
            'mean': df.mean(0).mean(),
            'min': df.min(0).min(),
            'max': df.max(0).max(),
            'std': df.std(0).std(),
            'median': df.median(0).median()
        }


class Grid3DMediator(Mediator):
    '''
    Mediator that understands single-valued, spatial data on a structured,
    longitude-latitude grid; two spatial dimensions, one value dimension (3D).
    Geometry expected as grid centroids (e.g. centroids of 1-degree grid cells).
    Additional fields beyond the "value" field may be included; currently
    supported is the additional "error" field.
    '''
    def load(self, collection_name, query={}):
        # Retrieve a cursor to iterate over the records matching the query
        cursor = self.client[self.db_name][collection_name].find(query, {
            'values': 1,
            'errors': 1,
        })
        
        # Create an n x 2 matrix of the longitude-latitude coordinates
        coords = np.array(self.client[self.db_name]['coord_index'].find({
            '_id': collection_name
        }).next()['i'])
        
        # Create a DataFrame of longitude-latitude coordinates
        coords = pd.DataFrame(coords, columns=('x', 'y'))

        frames = []
        ids = []

        for record in cursor:
            # Create values and error Series; concatenate them as a DataFrame,
            #   then concatenate them with the coordinates DataFrame
            values = pd.Series(record['values'], dtype='float64', name='values')
            errors = pd.Series(record['errors'], dtype='float64', name='errors')
            df = pd.concat([
                coords,
                pd.concat([values, errors], axis=1)
            ], axis=1)
            
            frames.append(df)
            ids.append(record.get('_id'))

        # Convert the Python datetime instances to ISO 8601 timestamps
        ids = map(lambda d: datetime.datetime.strftime(d, '%Y-%m-%dT%H:%M:%S'), ids)

        return dict(zip(ids, frames))

    def save(self, collection_name, instance):
        super(Grid3DMediator, self).save(collection_name, instance)

        df = instance.extract()

        # Expect that a valid timestamp was provided
        if instance.timestamp is None:
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
        data_dict = {
            '_id': self.parse_timestamp(instance.timestamp),
            '_span': int(instance.span) or None
        }
        
        for param in instance.parameters:
            data_dict[param] = df[param].tolist()
            
        j = self.client[self.db_name][collection_name].insert(data_dict)

    def summarize(self, model, collection_name, query={}):
        dfs = self.load_from_db(collection_name, query)
        
        # Merge them into a single, large data frame
        df = pd.concat(dfs)
        
        summary = {
            '_id': collection_name
        }
        
        for param in model.parameters:
            # Axis 0 is the "row-wise" axis
            summary[param] = {
                'mean': df.mean(0)[param],
                'min': df.min(0)[param],
                'max': df.max(0)[param],
                'std': df.std(0)[param],
                'median': df.median(0)[param]
            }
            
        return summary
        

class Unstructured3DMediator(Mediator):
    '''
    Mediator that understands single-valued, spatial data with arbitrary
    positions given as longitude-latitude pairs; two spatial dimensions, one
    value dimension (3D).
    '''
    
    def save(self, collection_name, instance):
        super(Unstructured3DMediator, self).save(collection_name, instance)

        df = instance.extract()
        
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

        if instance.geometry.get('isCollection'):                
            j = self.client[self.db_name][collection_name].insert({
                'features': features
            })
            
        else:
            for feature in features:
                j = self.client[self.db_name][collection_name].insert(feature)




