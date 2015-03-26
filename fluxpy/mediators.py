#===============================================================================
# Example data:
# /ws4/idata/fluxvis/casa_gfed_inversion_results/1.zerofull_casa_1pm_10twr/Month_Uncert1.mat
# 
# from fluxpy.mediators import *
# from fluxpy.models import *
# mediator = Grid3DMediator()
# xco2 = KrigedXCO2Matrix('xco2_data.mat', timestamp='2009-06-15')
# mediator.add(xco2).save_to_db('my_xco2_data')
#===============================================================================

import datetime
import os
import re
import sys
import pandas as pd
import numpy as np
from dateutil import parser
from pymongo import MongoClient
from fluxpy import DB, DEFAULT_PATH, ISO_8601, RESERVED_COLLECTION_NAMES

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
        # Updates the metadata in the passed MongoDB query
        last_metadata = query.next()
        update_selection = {}

        if last_metadata.has_key('dates'):
            if last_metadata.has_key('steps'):
                key = 'steps'

            elif last_metadata.has_key('spans'):
                key = 'spans'

            else:
                key = None

            last_dates = last_metadata.get('dates')
            dates_update = list(last_metadata.get('dates'))

            if key is not None:
                steps_update = list(last_metadata.get(key))
                the_update = zip(metadata.get('dates'), metadata.get(key))

            else:
                the_update = zip(metadata.get('dates'), range(len(metadata.get('dates'))))

            for datestr, step_or_span in the_update:
                date = parser.parse(datestr)

                i = 0
                while i < len(last_dates):
                    dt = datetime.timedelta(seconds=step_or_span)
                    last_date = parser.parse(last_dates[i])
                    very_last_date = parser.parse(last_dates[-1])

                    # If this date is 1 step or span away from the last...
                    if (date + dt) == last_date or (date + dt) == very_last_date:
                        break

                    # Is it before the most recent date?
                    if date < last_date:

                        # Insert older timestamp, step/span e.g. [old, *new, old, old]
                        dates_update.insert(i, datestr)
                        if key is not None:
                            steps_update.insert(i, step_or_span)

                        break

                    # Is it being compared to the last date and still more recent?
                    elif (i + 1) == len(last_dates) and date > very_last_date:

                        if date != very_last_date:
                            # Add new timestamp, step/span e.g.: [old, old, *new]
                            dates_update.append(datestr)
                            if key is not None:
                                steps_update.append(step_or_span)

                            break

                    i += 1

        if last_metadata.has_key('steps'):
            update_selection.update({
                'dates': dates_update,
                'steps': steps_update
            })

        elif last_metadata.has_key('spans'):
            update_selection.update({
                'dates': dates_update,
                'spans': steps_update
            })

        else:
            update_selection.update({
                'dates': dates_update
            })

        return update_selection

    def copy_grid_geometry(self, reference_name):
        coords = self.client[self.db_name]['coord_index'].find({
            '_id': reference_name
        }).next()['i']

        self.client[self.db_name]['coord_index'].insert({
            '_id': collection_name,
            'i': coords
        })

    def generate_metadata(self, collection_name, instance, force=False, verbose=False):
        '''
        Creates an entry in the metadata collection for this instance of data;
        updates the summary statistics of that entry if it already exists.
        '''
        
        if verbose: sys.stderr.write('\nGenerating metadata...')
        
        # Get the metadata
        metadata = instance.describe()

        # Set the unique identifier; include the summary statistics
        metadata['_id'] = collection_name
        metadata['stats'] = self.summarize(collection_name)

        # Find or create metadata; if it already exists, update it based on the
        #   the new values in the time series being considered
        query = self.client[self.db_name]['metadata'].find({
            '_id': collection_name
        })
        if query.count() == 0:
            self.client[self.db_name]['metadata'].insert(metadata)

        elif force:
            self.client[self.db_name]['metadata'].remove({'_id': collection_name})
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

        return metadata

    def save(self, collection_name, instance):
        '''Transforms contents of Data Frame into JSON representation for MongoDB'''
        if collection_name in RESERVED_COLLECTION_NAMES:
            raise ValueError('The collection name provided is a reserved name')

    def summarize(self, collection_name, query={}):
        '''
        Generates summary statistics by parameter over the data in a collection.
        This was designed and tested for the "3D" case i.e. spatial data in a
        tabular form and NOT for the "4D" case i.e. spatiotemporal data in a
        matrix form.
        '''
        disallowed_params = ('x', 'y', 'timestamp')
        dfs = self.load(collection_name, query)
        values = dict()

        if type(dfs) == dict:
            for df in dfs.values():
                for param in df.keys().values:
                    if param in disallowed_params:
                        continue

                    if not values.has_key(param):
                        values[param] = pd.Series([])

                    values[param] = pd.concat([
                        values[param], df[param]
                    ], axis=0)

        elif type(dfs) == pd.DataFrame:
            values = dfs

        summary = dict()
        for param in values.keys():
            if param in disallowed_params:
                continue

            summary[param] = {
                'mean': values[param].mean(),
                'min': values[param].min(),
                'max': values[param].max(),
                'std': values[param].std(),
                'median': values[param].median()
            }

        return summary


class Grid4DMediator(Mediator):
    '''
    Mediator that understands spatial data on a structured, longitude-latitude
    grid that vary in time; two spatial dimensions and an aribtrary number of
    time steps (frames). Geometry expected as grid centroids (e.g. centroids
    of 1-degree grid cells).
    '''

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

    def save(self, collection_name, instance, verbose=False):
        super(Grid4DMediator, self).save(collection_name, instance)

        df = instance.extract()

        # Create the index of grid cell coordinates, if needed
        if self.client[self.db_name]['coord_index'].find({
            '_id': collection_name
        }).count() == 0:
            self.client[self.db_name]['coord_index'].insert({
                '_id': collection_name,
                'i': list(df.index.values)
            })

        # Iterate over the transpose of the data frame
        total_records = len(df.T)
        for i, (timestamp, series) in enumerate(df.T.iterrows()):
            if getattr(instance, 'precision', None) is not None:
                self.client[self.db_name][collection_name].insert({
                    '_id': timestamp,
                    'values': map(lambda x: round(x[1], instance.precision),
                        series.iterkv())
                })

            else:
                self.client[self.db_name][collection_name].insert({
                    '_id': timestamp,
                    'values': series.tolist()
                })
                
            if verbose: sys.stderr.write('\rInserted %d of %d records...'
                                 % (i+1, total_records))

        self.generate_metadata(collection_name, instance, verbose=verbose)

    def summarize(self, collection_name, query={}):
        df = self.load(collection_name, query)

        return {
            'values': { # Axis 0 is the "row-wise" axis
                'mean': df.mean(0).mean(),
                'min': df.min(0).min(),
                'max': df.max(0).max(),
                'std': df.std(0).std(),
                'median': df.median(0).median()
            }
        }


class Grid3DMediator(Mediator):
    '''
    Mediator that understands single-valued, spatial data on a structured,
    longitude-latitude grid; two spatial dimensions, one value dimension (3D).
    Geometry expected as grid centroids (e.g. centroids of 1-degree grid cells).
    Additional fields beyond the "values" field may be included; currently
    supported is the additional "errors" field.
    '''

    def __align__(self, instance, alignment):
        df = instance.extract()

        # Get a list of column names for only the essential parameters
        cols = ['x', 'y']
        cols.extend(instance.parameters)

        # Remove extraneous columns; create the index on the incoming data frame
        dfm = df.ix[df.index, cols].set_index(['x', 'y'])

        # Get the two aligned DataFrames
        empty, aligned = alignment.align(dfm, axis=0)

        # Return None in place of NaN
        return aligned.where((pd.notnull(aligned)), None)

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

    def save(self, collection_name, instance, alignment=None, verbose=False):
        super(Grid3DMediator, self).save(collection_name, instance)

        if alignment is not None:
            df = self.__align__(instance, alignment).reset_index()

        else:
            df = instance.extract()

        # Expect that a valid timestamp was provided
        if instance.timestamp is None:
            raise AttributeError('Expected a model to have a "timestamp" parameter; is this the right model for this Mediator?')

        # Create the index of grid cell coordinates, if needed
        if self.client[self.db_name]['coord_index'].find({
            '_id': collection_name
        }).count() == 0:
            i = self.client[self.db_name]['coord_index'].insert({
                '_id': collection_name,
                'i': df.set_index(['x', 'y']).index.tolist()
            })

        # Create the data document itself
        data_dict = {
            '_id': parser.parse(instance.timestamp)
        }

        if getattr(instance, 'spans', None) is not None:
            try:
                metadata = instance.describe()
                data_dict['_span'] = metadata['spans'][
                    metadata['dates'].index(instance.timestamp)
                ]

            except ValueError:
                data_dict['_span'] = instance.spans[0]

        for param in instance.parameters:
            if verbose: sys.stderr.write('\nProcessing data for parameter: {0}...'.format(param))
            if getattr(instance, 'precision', None) is not None:
                data_dict[param] = map(lambda x: round(x[1],
                    instance.precision) if x[1] is not None else None, df[param].iterkv())

            else:
                data_dict[param] = df[param].tolist()
                
        if verbose: sys.stderr.write('\nInserting records...')

        self.client[self.db_name][collection_name].insert(data_dict)
        self.generate_metadata(collection_name, instance)


class Unstructured3DMediator(Mediator):
    '''
    Mediator that understands single-valued, spatial data with arbitrary
    positions given as longitude-latitude pairs; two spatial dimensions, one
    value dimension (3D).
    '''

    def load(self, collection_name, query={}):
        # Retrieve a cursor to iterate over the records matching the query
        result = self.client[self.db_name][collection_name].aggregate([{
            '$match': query,
        }, {
            '$group': {
                '_id': 0,
                'timestamp': { '$push': '$timestamp' },
                'value': { '$push': '$properties.value' },
                'error': { '$push': '$properties.error' }
            }
        }, {
            '$project': {
                '_id': 0,
                'timestamp': 1,
                'value': 1,
                'error': 1
            }
        }])

        series = []
        aggregate = result['result'][0]
        for param in aggregate.keys():
            series.append(pd.Series(aggregate[param], name=param))

        return pd.concat(series, axis=1)
    
    def save(self, collection_name, instance, verbose=False):
        super(Unstructured3DMediator, self).save(collection_name, instance)

        is_multi = (instance.geometry.get('type')[0:5] == 'Multi')

        df = instance.extract()
        features = []
        for i, series in df.iterrows():
            data_dict = {
                'timestamp': series['timestamp'] if type(series['timestamp'] <> 'datetime.datetime') else series['timestamp'].to_datetime(),
                'coordinates': [series['x'], series['y']],
                'properties': dict()
            }

            for param in instance.parameters:
                data_dict['properties'][param] = series[param]

            features.append(data_dict)
            
        # Create the index of grid cell coordinates, if needed
        if self.client[self.db_name]['coord_index'].find({
            '_id': collection_name
        }).count() == 0:
            i = self.client[self.db_name]['coord_index'].insert({
                '_id': collection_name,
                'i': df.set_index(['x', 'y']).index.tolist()
            })

        # If it's a collection, we can assume each data member is unique;
        #   we insert a single document
        if is_multi:
            if verbose:
                sys.stderr.write('\nInserting records...')

            j = self.client[self.db_name][collection_name].insert({
                'features': features
            })

        # Otherwise, each data member may not be unique e.g. each is a POINT
        #   among potentially other POINTs at the same date/time
        else:
            total_records = len(features)
            for i, feature in enumerate(features):
                j = self.client[self.db_name][collection_name].insert(feature)
                if verbose:
                    sys.stderr.write('\rInserted %d of %d records...' % (i + 1, total_records))

        self.generate_metadata(collection_name, instance)



