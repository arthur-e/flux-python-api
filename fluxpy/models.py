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

    def dump(self, data):
        pass

    def save(self, *args, **kwargs):
        pass


class XCO2Matrix(TransformationInterface):
    '''
    Understands XCO2 data as formatted--Typically 6-day spans of XCO2
    concentrations (ppm) at daily intervals on a latitude-longitude grid.
    Matrix dimensions: 1,311 (observations) x 6 (attributes).
    Columns: Longitude, latitude, XCO2 concentration (ppm), day of the year,
    year, retrieval error (ppm).
    '''
    defaults = {
        'var_name': 'XCO2',
        'interval': 86400000, # 1 day (daily) in ms
        'columns': ('x', 'y', 'value', '%j', '%Y', 'error'),
        'formats': {
            'x': '%.5f',
            'y': '%.5f',
            'value': '%.2f',
            'error': '%.4f'
        },
        'header': ('lng', 'lat', 'xco2_ppm', 'day', 'year', 'error_ppm'),
        'units': ('degrees', 'degrees', 'ppm', None, None, 'ppm^2'),
        'geometry': {
            'isCollection': False,
            'type': 'Point'
        }
    }

    path_regex = re.compile(r'.+\.(?P<extension>mat|h5)')
    
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
        
    def dump(self, data):
        pass

    def save(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''

        # Allow overrides through optional keyword arguments in save()
        kwargs.setdefault('var_name', self.params.get('var_name'))
        self.params.update(kwargs)
        
        if self.params.get('var_name') is None:
            raise AttributeError('One or more required configuration parameters were not provided')
        
        # HDF5/Matlab file interface
        f = self.file_handler(self.filename)
        
        # Data frame
        try:
            df = pd.DataFrame(f.get(self.params.get('var_name'))[:],
                columns=self.params.get('columns'))
            
        except TypeError:
            raise ValueError('Could not get at the variable named "%s"' % self.params.get('var_name'))

        # Add and populate a timestamp field
        t = []
        for i, series in df.iterrows():
            t.append(datetime.datetime(int(series['%Y']), 1, 1) + datetime.timedelta(days=int(series['%j'])))
            
        df['timestamp'] = pd.Series(t, dtype='datetime64[ns]')

        # Re-order columns; dispose of extraneous columns            
        # df = df.loc[:,['x', 'y', 't', 'value', 'error']]

        # Fix the precision of data values
        for col in self.params.get('formats').keys():
            df[col] = df[col].map(lambda x: float(self.params['formats'][col] % x))
        
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
        'columns': ('y', 'x', 'value', 'error', '4', '5', '6', '7', '8'),
        'formats': {
            'x': '%.5f',
            'y': '%.5f',
            'value': '%.2f',
            'error': '%.4f'
        },
        'header': ('lat', 'lng', 'xco2_ppm', 'error_ppm^2', '', '', '', '', ''),
        'units': ('degrees', 'degrees', 'ppm', 'ppm^2', None, None, None, None, None)
    }
    
    def save(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''

        # Allow overrides through optional keyword arguments in save()
        kwargs.setdefault('var_name', self.params.get('var_name'))
        kwargs.setdefault('timestamp', self.params.get('timestamp'))
        self.params.update(kwargs)

        if not all((self.params.get('var_name'), self.params.get('timestamp'))):
            raise AttributeError('One or more required configuration parameters were not provided')

        # HDF5/Matlab file interface
        f = self.file_handler(self.filename)

        # Data frame
        try:
            df = pd.DataFrame(f.get(self.params.get('var_name'))[:],
                columns=self.params.get('columns'))

        except TypeError:
            raise ValueError('Could not get at the variable named "%s"' % self.params.get('var_name'))
            
        # Fix the precision of data values
        for col in self.params.get('formats').keys():
            df[col] = df[col].map(lambda x: float(self.params['formats'][col] % x))

        return df


