'''
Data models for various science model outputs, including models that map from
flat files and hierarchical files (e.g. HDF5) to Python pandas Data Frames.
Example JSON configuration file for a model:

{
    "columns": [], # The column order
    "geometry": { # Only applies for non-structured data
        # True to specify that each document is a FeatureCollection; if False,
        #   each row will be stored as a separate document (a separate simple feature)
        "is_collection": false,
        "type": "Point" # The WKT type to make for each row
    },
    "header": [], # The human-readable column headers, in order
    "step": null, # The time step (seconds) between observations (documents)
    "parameters": [], # The names of those data fields other than space and time fields
    "span": null, # The amount of time (ms) for which the measurements are valid after the timestamp
    "gridres": { # Mutually exclusive with the "geometry" key
        "units": "degrees",
        "x": 0.5, # Grid cell resolution in the x direction
        "y": 0.5, # Grid cell resolution in the y direction
    },
    "timestamp": null, # The ISO 8601 timestamp
    "units": [], # The units of measurement, in order
    "var_name": null, # The Matlab/HDF5 variable of interst
}
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
    file may be provided as a *.json file with the same name as the data file.
    '''
    path_regex = re.compile(r'.+\.(?P<extension>mat|h5)')
    var_regex = re.compile(r'^(?!__).*(?!__)$') # Skips __private__ variable names

    def __init__(self, path, *args, **kwargs):
        self.config = dict()

        if self.path_regex.match(path) is None:
            raise AttributeError('Only Matlab (*.mat) and HDF5 (*.h5 or *.mat) files are accepted')

        if self.path_regex.match(path).groupdict().get('extension') == 'mat':
            self.file_handler = scipy.io.loadmat

        else:
            self.file_handler = h5py.File

        # Check to see if a config file with the same name exists
        config = os.path.join('.'.join(path.split('.')[:-1]), '.json')
        if os.path.exists(config):
            self.config = json.load(open(config, 'rb'))

        # Update and apply the configuration options as attributes
        self.__configure__(**kwargs)

        # Open the hierarchical file
        self.__open__(path)
            
    def __configure__(self, **kwargs):
        self.config.update(kwargs)

        # Set as attributes all of the configuration values
        for config in self.config.keys():
            setattr(self, config, self.config.get(config))

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
        self.precision = 5 #TODO Add to schema
        self.gridres = {
            'units': 'degrees',
            'x': 1.0,
            'y': 1.0,
        }
        self.parameters = ['value', 'error']
        self.units = ['degrees', 'degrees']

        super(CovarianceMatrix, self).__init__(path, *args, **kwargs)

    def describe(self, df=None, **kwargs):
        if df is None:
            df = self.extract(**kwargs)

        self.__metadata__ = {
            'dates': [self.timestamp],
            'gridded': True,
            'gridres': self.gridres
        }

        if getattr(self, 'span', None) is not None:
            self.__metadata__['spans'] = [self.span]

        if getattr(self, 'step', None) is not None:
            self.__metadata__['steps'] = [self.step]

        return self.__metadata__

    def extract(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''
        if self.timestamp is None:
            raise AttributeError('One or more required configuration parameters were not provided')

        # Allow overrides through optional keyword arguments in extract()
        self.__configure__(**kwargs)

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
    def __init__(self, path, *args, **kwargs):
        self.columns = ['x', 'y']
        self.formats = {
            'x': '%.5f',
            'y': '%.5f'
        }
        self.gridres = { # Mutually exclusive with the "geometry" key
            'units': 'degrees',
            'x': 1.0, # Grid cell resolution in the x direction
            'y': 1.0, # Grid cell resolution in the y direction
        }
        self.header = ['lng', 'lat']
        self.step = 10800 # 3 hours in seconds
        self.parameters = ['value', 'error']
        self.units = ['degrees', 'degrees']
        self.span = None
        self.timestamp = None
        self.transforms = {}
        self.var_name = None

        super(SpatioTemporalMatrix, self).__init__(path, *args, **kwargs)

    def describe(self, df=None, **kwargs):
        if df is None:
            df = self.extract(**kwargs)

        bounds = MultiPoint(list(df.index.values)).bounds
        dates = pd.date_range(self.timestamp, periods=df.shape[1],
            freq='%dS' % self.step)

        self.__metadata__ = {
            'dates': map(lambda t: t.strftime('%Y-%m-%d'),
                [dates[0], dates[-1]]),
            'gridded': True,
            'bbox': bounds,
            'bboxmd5': md5(str(bounds)).hexdigest(),
            'gridres': self.gridres
        }

        if getattr(self, 'span', None) is not None:
            self.__metadata__['spans'] = [self.span]

        if getattr(self, 'step', None) is not None:
            self.__metadata__['steps'] = [self.step]

        return self.__metadata__

    def extract(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''
        if self.timestamp is None:
            raise AttributeError('One or more required configuration parameters were not provided')

        # Allow overrides through optional keyword arguments in extract()
        self.__configure__(**kwargs)

        # Create the column headers as a time series
        steps = self.file.get(self.var_name).shape[1] - len(self.columns)
        cols = list(self.columns)
        cols.extend(pd.date_range(self.timestamp, periods=steps,
            freq='%dS' % self.step))

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
    concentrations (ppm) at daily steps on a latitude-longitude grid.
    Matrix dimensions: 1,311 (observations) x 6 (attributes).
    Columns: Longitude, latitude, XCO2 concentration (ppm), day of the year,
    year, retrieval error (ppm).
    '''
    def __init__(self, path, *args, **kwargs):
        self.columns = ['x', 'y', 'value', '%j', '%Y', 'error']
        self.formats = {
            'x': '%.5f',
            'y': '%.5f',
            'value': '%.2f',
            'error': '%.4f'
        }
        self.geometry = {
            'is_collection': False,
            'type': 'Point'
        }
        self.header = ['lng', 'lat', 'xco2_ppm', 'day', 'year', 'error_ppm']
        self.step = 86400 # 1 day (daily) in seconds
        self.parameters = ['value', 'error']
        self.units = ['degrees', 'degrees', 'ppm', None, None, 'ppm^2']
        self.var_name = 'XCO2'
        self.span = None

        super(XCO2Matrix, self).__init__(path, *args, **kwargs)

    def dump(self, data):
        pass

    def extract(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''
        if self.timestamp is None:
            raise AttributeError('One or more required configuration parameters were not provided')

        # Allow overrides through optional keyword arguments in extract()
        self.__configure__(**kwargs)
        
        if self.var_name is None:
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
        self.columns = ['y', 'x', 'values', 'errors', '4', '5', '6', '7', '8']
        self.formats = {
            'x': '%.5f',
            'y': '%.5f',
            'values': '%.2f',
            'errors': '%.4f'
        }
        self.gridres = {
            'x': 0.5,
            'y': 0.5,
            'units': 'degrees'
        }
        self.header = ['lat', 'lng', 'xco2_ppm', 'error_ppm^2', '', '', '', '', '']
        self.step = None
        self.parameters = ['values', 'errors']
        self.span = 518400 # 6 days in seconds
        self.transforms = {
            'errors': lambda x: math.sqrt(x)
        }
        self.units = ['degrees', 'degrees', 'ppm', 'ppm', None, None, None, None, None]
        self.var_name = 'krigedData'

        super(KrigedXCO2Matrix, self).__init__(path, *args, **kwargs)
    
    def extract(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''
        if self.timestamp is None:
            raise AttributeError('One or more required configuration parameters were not provided')

        # Allow overrides through optional keyword arguments in extract()
        self.__configure__(**kwargs)

        if not all((self.var_name, self.timestamp)):
            raise AttributeError('One or more required configuration parameters were not provided')

        # Data frame
        try:
            df = pd.DataFrame(self.file.get(self.var_name)[:], columns=self.columns)

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


