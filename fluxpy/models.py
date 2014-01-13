'''
Data models for various science model outputs, including models that map from
flat files and hierarchical files (e.g. HDF5) to Python pandas Data Frames.
'''

import datetime, os, sys, re, json, csv
import pandas as pd
import numpy as np
import scipy.io
import h5py

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
        'geometry': { # Only applies for non-structured data
            # True to specify that each document is a FeatureCollection; if False,
            #   each row will be stored as a separate document (a separate simple feature)
            'isCollection': False,
            'type': 'Point' # The WKT type to make for each row
        },
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
        'geometry': {
            'isCollection': False,
            'type': 'Point'
        }
    }

    path_regex = re.compile(r'.+\.(?P<extension>mat|h5)')
    
    #TODO Remove Fields; reshape Data Frame with only y, x, value, error, and t columns
    class Fields:
        '''Field getters; returns the corresponding value from a given series'''
        x = lambda z, s: s[0]
        y = lambda z, s: s[1]
        t = lambda z, s: datetime.datetime(int(s[4]), 1, 1) + datetime.timedelta(days=int(s[3]))
        ident = lambda z, s: None
        value = lambda z, s: s[2]
        error = lambda z, s: s[5]

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
        
        # Remember the path to the file
        self.filename = path
        
        # Set up field getters
        self.fields = self.Fields()
    
    def __precision__(self, value):
        return round(value, 2)

    def dump(self, data):
        pass

    def save(self, *args, **kwargs):
        # Called by a Mediator class member; should return data in interchange
        var_name = kwargs.get('var_name') or self.params.get('var_name')
        
        if not all((var_name,)):
            raise AttributeError('One or more required configuration parameters were not provided')
        
        # HDF5/Matlab file interface
        f = self.file_handler(self.filename)
        
        # Data frame
        try:
            df = pd.DataFrame(f.get(var_name)[:], columns=self.params['columns'])
            
        except TypeError:
            raise ValueError('Could not get at the variable named "%s"' % var_name)
        
        # Fix the precision of data values
        df['value'] = df['value'].apply(self.__precision__)
        df['error'] = df['error'].apply(self.__error_precision__)
        
        return df


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
    
    #TODO Remove Fields; reshape Data Frame with only y, x, value, error, and t columns
    class Fields:
        '''Field getters; returns the corresponding value from a given Series'''
        x = lambda z, s: s[1]
        y = lambda z, s: s[0]
        t = lambda z, s: datetime.datetime(int(s[4]), 1, 1) + datetime.timedelta(days=s[3])
        ident = lambda z, s: None
        value = lambda z, s: s[2]
        error = lambda z, s: s[3]

    def __precision__(self, value):
        return round(value, 2)

    def save(self, *args, **kwargs):
        # Called by a Mediator class member; should return data in interchange
        var_name = kwargs.get('var_name') or self.params.get('var_name')
        timestamp = kwargs.get('timestamp') or self.params.get('timestamp')

        if not all((var_name, timestamp)):
            raise AttributeError('One or more required configuration parameters were not provided')

        # HDF5/Matlab file interface
        f = self.file_handler(self.filename)

        # Data frame
        try:
            df = pd.DataFrame(f.get(var_name)[:], columns=self.params['columns'])

        except TypeError:
            raise ValueError('Could not get at the variable named "%s"' % var_name)

        # Fix the precision of data values
        df['value'] = df['value'].apply(self.__precision__)
        df['error'] = df['error'].apply(self.__error_precision__)

        return df


