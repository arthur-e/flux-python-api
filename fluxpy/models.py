'''
Data models for various science model outputs, including models that map from
flat files and hierarchical files (e.g. HDF5) to Python pandas Data Frames.
Example JSON configuration file for a model:

{
    "columns": [], # The column order
    "geometry": { # Only applies for non-structured data
        # True to specify that each document is a FeatureCollection; if False,
        #   each row will be stored as a separate document (a separate simple feature)
        "isCollection": false,
        "type": "Point" # The WKT type to make for each row
    },
    "header": [], # The human-readable column headers, in order
    "interval": null, # The time interval (seconds) between observations (documents)
    "parameters": [], # The names of those data fields other than space and time fields
    "range": null, # The amount of time (ms) for which the measurements are valid after the timestamp
    "resolution": { # Mutually exclusive with the "geometry" key
        "units": "degrees",
        "x_length": 0.5, # Grid cell resolution in the x direction
        "y_length": 0.5, # Grid cell resolution in the y direction
    },
    "timestamp": null, # The ISO 8601 timestamp
    "transforms": [], # Lambda functions (as strings for eval()) to be applied to values per-field
    "units": [], # The units of measurement, in order
    "var_name": null, # The Matlab/HDF5 variable of interst
}
'''

import ipdb#FIXME
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

class TransformationInterface:
    '''
    An abstract persistence transformation interface (modified from
    Andy Bulka, 2001), where extract() and dump() methods are defined in
    subclasses. The extract() method may take unique arguments as optional keyword
    arguments (they must default to None). The dump() method must take only one
    argument which is the interchange datum (a dictionary). A configuration
    file may be provided as a *.json file with the same name as the data file.
    '''
    config = dict()
    path_regex = re.compile(r'.+\.(?P<extension>mat|h5)')
    var_regex = re.compile(r'^(?!__).*(?!__)$') # Skips __private__ variable names

    def __init__(self, path, **kwargs):
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
        for config in self.config:
            setattr(self, config, self.config.get(config))

    def __open__(self, path):
        # HDF5/Matlab file interface
        self.file = self.file_handler(path)

        if self.timestamp is None:
            raise AttributeError('One or more required configuration parameters were not provided')

        if self.var_name is None:
            self.var_name = [
                k for k in self.file.keys() if self.var_regex.match(k) is not None
            ][0] # Grab the first variable name that isn't __private__

    def dump(self, data):
        pass

    def extract(self, *args, **kwargs):
        pass


class SpatioTemporalMatrix(TransformationInterface):
    '''
    A generic matrix with two spatial dimensions in the first two columns and
    an arbitrary number of columns following each representing one step in time.
    '''
    columns = ['x', 'y']
    formats = {
        'x': '%.5f',
        'y': '%.5f'
    }
    geometry = {
        'isCollection': False,
        'type': 'Point'
    }
    header = ['lng', 'lat']
    interval = 10800 # 3 hours in seconds
    parameters = ['value', 'error']
    units = ['degrees', 'degrees']
    timestamp = None
    transforms = {}
    var_name = None


class InvertedSurfaceFlux(SpatioTemporalMatrix):
    '''
    Input (lng, lat, flux at t1, flux at t2, ...)
    -166.50   65.500   8.0282e-02 ...
    -165.50   61.500   1.5991e-01 ...
    -165.50   65.500   1.0994e-01 ...
        ...      ...          ...

    Output:
    {
	    "_id" : ISODate("2003-12-22T03:00:00Z"),
	    "values" : [
		    0.08, ...
    '''

    def extract(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''

        dt = datetime.datetime.strptime(self.timestamp, '%Y-%m-%dT%H:%M:%S')
        intervals = self.file[self.var_name].shape[1] - len(self.columns)
        cols = list(self.columns)
        cols.extend([str(dt + relativedelta(seconds=+(self.interval*j))) for j in range(intervals)])

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

        return dfm


class XCO2Matrix(TransformationInterface):
    '''
    Understands XCO2 data as formatted--Typically 6-day spans of XCO2
    concentrations (ppm) at daily intervals on a latitude-longitude grid.
    Matrix dimensions: 1,311 (observations) x 6 (attributes).
    Columns: Longitude, latitude, XCO2 concentration (ppm), day of the year,
    year, retrieval error (ppm).
    '''
    columns = ['x', 'y', 'value', '%j', '%Y', 'error']
    formats = {
        'x': '%.5f',
        'y': '%.5f',
        'value': '%.2f',
        'error': '%.4f'
    }
    geometry = {
        'isCollection': False,
        'type': 'Point'
    }
    header = ['lng', 'lat', 'xco2_ppm', 'day', 'year', 'error_ppm']
    interval = 86400 # 1 day (daily) in seconds
    parameters = ['value', 'error']
    units = ['degrees', 'degrees', 'ppm', None, None, 'ppm^2']
    var_name = 'XCO2'
    range = None

    def dump(self, data):
        pass

    def extract(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''

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


class KrigedXCO2Matrix(XCO2Matrix):
    '''
    Understands Kriged XCO2 data as formatted--Typically 6-day spans of XCO2
    concentrations (ppm) at daily intervals on a latitude-longitude grid.
    Matrix dimensions: 14,210 (model cells) x 9 (attributes).
    Columns: Longitude, latitude, XCO2 concentration (ppm), retrieval error (ppm)
    '''
    columns = ['y', 'x', 'values', 'errors', '4', '5', '6', '7', '8']
    formats = {
        'x': '%.5f',
        'y': '%.5f',
        'values': '%.2f',
        'errors': '%.4f'
    }
    header = ['lat', 'lng', 'xco2_ppm', 'error_ppm^2', '', '', '', '', '']
    interval = None
    parameters = ['values', 'errors']
    range = 518400 # 6 days in seconds
    resolution = {
        'x_length': 0.5,
        'y_length': 0.5,
        'units': 'degrees'
    }
    transforms = {
        'errors': lambda x: math.sqrt(x)
    }
    units = ['degrees', 'degrees', 'ppm', 'ppm', None, None, None, None, None]
    var_name = 'krigedData'
    
    def extract(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''

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


