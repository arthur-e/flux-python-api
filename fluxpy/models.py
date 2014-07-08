'''
Data models for various science model outputs, including models that map from
flat files and hierarchical files (e.g. HDF5) to Python pandas Data Frames.
'''

import datetime
import json
import math
import os
import re
import sys
import pandas as pd
import numpy as np
import scipy.io
import h5py
from dateutil.relativedelta import *
from fluxpy import ISO_8601
from shapely.geometry import MultiPoint

try:
    from hashlib import md5

except ImportError:
    import md5

class TransformationInterface(object):
    '''
    An abstract persistence transformation interface (modified from
    Andy Bulka, 2001), where extract() and dump() methods are defined in
    subclasses. The extract() method may take unique arguments as optional keyword
    arguments (they must default to None). The dump() method must take only one
    argument which is the interchange datum (a dictionary). A configuration
    file may be provided as a *.json* file with the same name as the data file.
    '''
    path_regex = re.compile(r'.+\.(?P<extension>mat|h5)')
    var_regex = re.compile(r'^(?!__).*(?!__)$') # Skips __private__ variable names

    def __init__(self, path, config_file=None, *args, **kwargs):
        self.config = dict()

        if self.path_regex.match(path) is None:
            raise AttributeError('Only Matlab (*.mat) and HDF5 (*.h5 or *.mat) files are accepted')

        if self.path_regex.match(path).groupdict().get('extension') == 'mat':
            self.file_handler = scipy.io.loadmat

        else:
            self.file_handler = h5py.File

        # If config_file not specified, check to see if a config file with the same name exists
        config = config_file if config_file else '.'.join(path.split('.')[:-1]) + '.json'
        if os.path.exists(config):
            self.config = json.load(open(config, 'rb'))

        # If the filename can be parsed for information, mine the timestamp from it
        if getattr(self, 'regex', None) is not None:
            if self.regex.has_key('map'):
                if self.regex['map'].has_key('timestamp') and getattr(self, 'timestamp', None) is None:
                    match = re.compile(self.regex['regex']).match(os.path.basename(path))
                    if match is not None:
                        fmt = self.regex['map']['timestamp']
                        t = match.groupdict()['timestamp']
                        self.timestamp = datetime.datetime.strptime(t, fmt).strftime(ISO_8601)

        # Update and apply the configuration options as attributes
        self.__configure__(**kwargs)
        # Open the hierarchical file
        self.__open__(path)
            
    def __configure__(self, **kwargs):
        self.config.update(kwargs)

        # Set as attributes all of the configuration values
        for config in self.config.keys():
            setattr(self, config, self.config.get(config))

    def __date_series__(self, df=None, steps=None):
        if df is not None:
            steps = df.shape[1]

        dates = pd.date_range(self.timestamp, periods=steps,
            freq='%dS' % self.steps[0])
        if len(self.steps) > 1:
            i = 1
            while i < len(self.steps):
                dates = pd.concat(dates, pd.date_range(self.timestamp,
                    periods=steps, freq='%dS' % self.steps[i]))
                i += 1

        return dates

    def __open__(self, path, var_name=None):
        try:
            self.file = self.file_handler(path) # HDF5/Matlab file interface

        except NotImplementedError:
            self.file_handler = h5py.File
            self.file = self.file_handler(path)

        # Infer var_name; grab the first variable name that isn't __private__
        if var_name is None and getattr(self, 'var_name', None) is None:
            self.var_name = [
                k for k in self.file.keys() if self.var_regex.match(k) is not None
            ][0]

    def describe(self, df=None, **kwargs):
        if getattr(self, '__metadata__', None) is None:
            self.__metadata__ = dict()

        self.__metadata__.update({
            'gridded': getattr(self, 'gridded', True),
            'grid': getattr(self, 'grid', {}),
            'title': getattr(self, 'title', ''),
            'units': getattr(self, 'units', {})
        })

        if getattr(self, 'spans', None) is not None:
            self.__metadata__['spans'] = self.spans

        if getattr(self, 'steps', None) is not None:
            self.__metadata__['steps'] = self.steps

        return self.__metadata__

    def dump(self, data):
        pass

    def extract(self, *args, **kwargs):
        pass


class CovarianceMatrix(TransformationInterface):
    '''
    Represents a covariance matrix from aggregate covariances; assumes monthly
    aggregation (though this can be specified otherwise).
    '''
    def __init__(self, path, *args, **kwargs):
        self.precision = 5 
        self.grid = {
            'units': 'degrees',
            'x': 1.0,
            'y': 1.0,
        }
        self.parameters = ['value', 'error']
        self.units = {
            'x': 'degrees',
            'y': 'degrees'
        }

        super(CovarianceMatrix, self).__init__(path, *args, **kwargs)

    def describe(self, df=None, **kwargs):
        if df is None:
            df = self.extract(**kwargs)

        self.__metadata__ = {
            'dates': [self.timestamp],
            'gridded': True,
            'precision': getattr(self, 'precision', 2)
        }

        super(CovarianceMatrix, self).describe(df, **kwargs)

        return self.__metadata__

    def extract(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''

        # Allow overrides through optional keyword arguments in extract()
        self.__configure__(**kwargs)

        if getattr(self, 'timestamp', None) is None:
            raise AttributeError('One or more required configuration parameters were not provided')

        df = pd.DataFrame(self.file.get(self.var_name)[:])
        assert df.shape[0] == df.shape[1], 'Expected a square matrix (covariance matrix)'

        if self.precision is not None:
            df = df.apply(lambda col: col.map(lambda x: float(('%%.%df' % self.precision) % x)))

        return df


class SpatioTemporalMatrix(TransformationInterface):
    '''
    A generic matrix with two spatial dimensions in the first two columns and
    an arbitrary number of columns following each representing one step in time.
    '''
    def __init__(self, path, config_file=None, *args, **kwargs):
        self.precision = 2
        self.columns = ['x', 'y']
        self.formats = {
            'x': '%.5f',
            'y': '%.5f'
        }
        self.gridded = True
        self.grid = { # Mutually exclusive with the "geometry" key
            'units': 'degrees',
            'x': 1.0, # Grid cell resolution in the x direction
            'y': 1.0, # Grid cell resolution in the y direction
        }
        self.header = ['lng', 'lat']
        self.steps = [10800] # 3 hours in seconds
        self.parameters = ['values']
        self.units = {
            'x': 'degrees',
            'y': 'degrees'
        }
        self.transforms = {}

        super(SpatioTemporalMatrix, self).__init__(path, config_file, *args, **kwargs)

    def describe(self, df=None, **kwargs):
        if df is None:
            df = self.extract(**kwargs)

        bounds = MultiPoint(list(df.index.values)).bounds
        dates = self.__date_series__(df)

        self.__metadata__ = {
            'dates': map(lambda t: t.strftime(ISO_8601),
                [dates[0], dates[-1]]),
            'bbox': bounds,
            'bboxmd5': md5(str(bounds)).hexdigest()
        }

        super(SpatioTemporalMatrix, self).describe(df, **kwargs)

        return self.__metadata__

    def extract(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''

        # Allow overrides through optional keyword arguments in extract()
        self.__configure__(**kwargs)

        if getattr(self, 'timestamp', None) is None:
            raise AttributeError('One or more required configuration parameters were not provided')

        # Create the column headers as a time series
        steps = self.file.get(self.var_name).shape[1] - len(self.columns)
        cols = list(self.columns)

        # Iterate through steps and concatenate the dates series; use as the
        #   column headers
        cols.extend(self.__date_series__(None, steps))

        # Alternatively; for column names as strings:
        # dt = datetime.datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%S')
        # cols.extend([
        #     datetime.datetime.strftime(dt + relativedelta(seconds=int(self.step*j)),
        #         '%Y-%m-%dT%H:%M:%S') for j in range(steps)
        # ])

        # Data frame
        try:
            df = pd.DataFrame(self.file.get(self.var_name)[:], columns=cols)

        except TypeError:
            raise ValueError('Could not get at the variable named "%s"' % self.var_name)

        # Apply any data transforms
        if isinstance(self.transforms, dict):
            for col, transform in self.transforms.items():
                if transform is not None:
                    df[col] = df[col].apply(transform)

        # Fix the precision of data values
        for col in self.formats.keys():
            df[col] = df[col].map(lambda x: float(self.formats[col] % x))

        # Capture a new DataFrame with a MultiIndex; promotes these columns to indexes
        dfm = df.set_index(self.columns)

        # Create metadata
        self.describe(dfm)

        return dfm


class XCO2Matrix(TransformationInterface):
    '''
    Understands XCO2 data as formatted--Typically 6-day spans of XCO2
    concentrations (ppm).
    Matrix dimensions: 1,311 (observations) x 6 (attributes).
    Columns: Longitude, latitude, XCO2 concentration (ppm), day of the year,
    year, retrieval error (ppm).
    '''
    def __init__(self, path, *args, **kwargs):
        self.precision = 1
        self.columns = ['x', 'y', 'value', '%j', '%Y', 'error']
        self.formats = {
            'x': '%.5f',
            'y': '%.5f',
            'value': '%.2f',
            'error': '%.4f'
        }
        self.gridded = False
        self.geometry = {
            'collection': False,
            'type': 'Point'
        }
        self.header = ['lng', 'lat', 'xco2_ppm', 'day', 'year', 'error_ppm']
        self.parameters = ['value', 'error']
        self.regex = {
            'regex': '^XCO2_(?P<timestamp>\d{4}\d{2}\d{2})_.*$',
            'map': {
                'timestamp': '%Y%m%d'
            }
        }
        self.units = {
            'x': 'degrees',
            'y': 'degrees',
            'value': 'ppm',
            'error': 'ppm&sup2;'
        }
        self.var_name = 'XCO2'
        self.title = 'Bias-Corrected XCO2 Retrievals'

        super(XCO2Matrix, self).__init__(path, *args, **kwargs)

    def describe(self, df=None, **kwargs):
        if df is None:
            df = self.extract(**kwargs)

        bounds = MultiPoint(df.set_index(['x', 'y']).index.tolist()).bounds
        dates = df['timestamp'].map(lambda x: x.strftime('%Y-%m-%dT%H:%M:%S'))\
            .unique().tolist()
        dates.sort(lambda x, y: cmp(y, x))

        self.__metadata__ = {
            'dates': dates,
            'bbox': bounds,
            'bboxmd5': md5(str(bounds)).hexdigest()
        }

        super(XCO2Matrix, self).describe(df, **kwargs)

        return self.__metadata__

    def extract(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''

        # Allow overrides through optional keyword arguments in extract()
        self.__configure__(**kwargs)

        if getattr(self, 'timestamp', None) is None:
            raise AttributeError('One or more required configuration parameters were not provided')
        
        if getattr(self, 'var_name', None) is None:
            raise AttributeError('One or more required configuration parameters were not provided')
        
        # Data frame
        try:
            df = pd.DataFrame(self.file.get(self.var_name)[:], columns=self.columns)
            
        except TypeError:
            raise ValueError('Could not get at the variable named "%s"' % self.var_name)

        # Add and populate a timestamp field
        t = []
        for i, series in df.iterrows():
            t.append(datetime.datetime(int(series['%Y']), 1, 1) + datetime.timedelta(days=int(series['%j'])))
            
        df['timestamp'] = pd.Series(t, dtype='datetime64[ns]')

        # Re-order columns; dispose of extraneous columns            
        # df = df.loc[:,['x', 'y', 't', 'value', 'error']]

        # Fix the precision of data values
        for col in self.formats.keys():
            df[col] = df[col].map(lambda x: float(self.formats[col] % x))
        
        return df


class KrigedXCO2Matrix(TransformationInterface):
    '''
    Understands Kriged XCO2 data as formatted--Typically 6-day spans of XCO2
    concentrations (ppm) at daily steps on a latitude-longitude grid.
    Matrix dimensions: 14,210 (model cells) x 9 (attributes).
    Columns: Longitude, latitude, XCO2 concentration (ppm), retrieval error (ppm)
    '''
    def __init__(self, path, *args, **kwargs):
        self.precision = 1
        self.columns = ['y', 'x', 'values', 'errors', '4', '5', '6', '7', '8']
        self.formats = {
            'x': '%.5f',
            'y': '%.5f',
            'values': '%.2f',
            'errors': '%.4f'
        }
        self.gridded = True
        self.grid = {
            'x': 1.0,
            'y': 1.0,
            'units': 'degrees'
        }
        self.header = ['lat', 'lng', 'xco2_ppm', 'error_ppm^2', '', '', '', '', '']
        self.parameters = ['values', 'errors']
        self.spans = [518400] # 6 days in seconds
        self.regex = {
            'regex': '^Kriged_(?P<timestamp>\d{4}\d{2}\d{2})_.*$',
            'map': {
                'timestamp': '%Y%m%d'
            }
        }
        self.transforms = {
            'errors': lambda x: math.sqrt(x)
        }
        self.units = {
            'x': 'degrees',
            'y': 'degrees',
            'values': 'ppm',
            'errors': 'ppm'
        }
        self.var_name = 'krigedData'
        self.title = 'Kriged XCO2 Test'

        super(KrigedXCO2Matrix, self).__init__(path, *args, **kwargs)

    def describe(self, df=None, **kwargs):
        if df is None:
            df = self.extract(**kwargs)

        bounds = MultiPoint(df.set_index(['x', 'y']).index.tolist()).bounds

        self.__metadata__ = {
            'dates': [self.timestamp],
            'bbox': bounds,
            'bboxmd5': md5(str(bounds)).hexdigest()
        }

        super(KrigedXCO2Matrix, self).describe(df, **kwargs)

        return self.__metadata__
    
    def extract(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''

        # Allow overrides through optional keyword arguments in extract()
        self.__configure__(**kwargs)

        if getattr(self, 'timestamp', None) is None:
            raise AttributeError('One or more required configuration parameters were not provided')

        if not all((self.var_name, self.timestamp)):
            raise AttributeError('One or more required configuration parameters were not provided')

        file_data = self.file.get(self.var_name)[:]
        assert file_data.shape[1] == len(self.columns), 'Mismatched number of columns and number of fields in the data'

        # Data frame
        try:
            df = pd.DataFrame(file_data, columns=self.columns)

        except TypeError:
            raise ValueError('Could not get at the variable named "%s"' % self.var_name)

        # Apply any data transforms
        if isinstance(self.transforms, dict):
            for col, transform in self.transforms.items():
                if transform is not None:
                    df[col] = df[col].apply(transform)

        # Fix the precision of data values
        for col in self.formats.keys():
            df[col] = df[col].map(lambda x: float(self.formats[col] % x))

        return df

    def get_coords(self):
        return self.extract().apply(lambda c: [c['x'], c['y']], 1)


