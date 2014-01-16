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
    defaults = { #TODO Have these config parameters applied as attributes in subclasses?
        'var_name': None, # The Matlab/HDF5 variable of interst
        'interval': None, # The time interval (ms) between observations (documents)
        'range': None, # The amount of time (ms) for which the measurements are valid after the timestamp
        'columns': None, # The column order
        'header': None, # The human-readable column headers, in order
        'units': None, # The units of measurement, in order
        'parameters': None, # The names of those data fields other than space and time fields
        'geometry': { # Only applies for non-structured data
            # True to specify that each document is a FeatureCollection; if False,
            #   each row will be stored as a separate document (a separate simple feature)
            'isCollection': False,
            'type': 'Point' # The WKT type to make for each row
        },
        'resolution': { # Mutually exclusive with the "geometry" key
            'x_length': 0.5, # Grid cell resolution in the x direction
            'y_length': 0.5, # Grid cell resolution in the y direction
            'units': 'degrees'
        }
    }

    def __init__(self, path=None):
        #TODO Have the collection_name specified in each instance?
        # Check to see if a config file with the same name exists
        config = os.path.join('.'.join(path.split('.')[:-1]), '.json')
        if os.path.exists(config):
            self.config = json.load(open(config, 'rb'))

        else:
            self.config = self.defaults

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
        'geometry': {
            'isCollection': False,
            'type': 'Point'
        },
        'header': ('lng', 'lat', 'xco2_ppm', 'day', 'year', 'error_ppm'),
        'parameters': ('value', 'error'),
        'units': ('degrees', 'degrees', 'ppm', None, None, 'ppm^2')
    }

    path_regex = re.compile(r'.+\.(?P<extension>mat|h5)')
    
    def __init__(self, path, **kwargs):
        if self.path_regex.match(path) is None:
            raise AttributeError('Only Matlab (*.mat) and HDF5 (*.h5 or *.mat) files are accepted')

        if self.path_regex.match(path).groupdict().get('extension') == 'mat':
            self.file_handler = scipy.io.loadmat

        else:
            self.file_handler = h5py.File
            
        self.config = {}

        # Check to see if a config file with the same name exists
        config = os.path.join('.'.join(path.split('.')[:-1]), '.json')
        if os.path.exists(config):
            self.config = json.load(open(config, 'rb'))
        
        for (key, value) in self.defaults.items():    
            self.config.setdefault(key, value)

        # Overrides in this instance
        self.config.update(kwargs)
        
        # Remember the path to the file
        self.filename = path
        
    def dump(self, data):
        pass

    def save(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''

        # Allow overrides through optional keyword arguments in save()
        kwargs.setdefault('var_name', self.config.get('var_name'))
        self.config.update(kwargs)
        
        if self.config.get('var_name') is None:
            raise AttributeError('One or more required configuration parameters were not provided')
        
        # HDF5/Matlab file interface
        f = self.file_handler(self.filename)
        
        # Data frame
        try:
            df = pd.DataFrame(f.get(self.config.get('var_name'))[:],
                columns=self.config.get('columns'))
            
        except TypeError:
            raise ValueError('Could not get at the variable named "%s"' % self.config.get('var_name'))

        # Add and populate a timestamp field
        t = []
        for i, series in df.iterrows():
            t.append(datetime.datetime(int(series['%Y']), 1, 1) + datetime.timedelta(days=int(series['%j'])))
            
        df['timestamp'] = pd.Series(t, dtype='datetime64[ns]')

        # Re-order columns; dispose of extraneous columns            
        # df = df.loc[:,['x', 'y', 't', 'value', 'error']]

        # Fix the precision of data values
        for col in self.config.get('formats').keys():
            df[col] = df[col].map(lambda x: float(self.config['formats'][col] % x))
        
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
        'parameters': ('value', 'error'),
        'resolution': {
            'x_length': 0.5,
            'y_length': 0.5,
            'units': 'degrees'
        },
        'units': ('degrees', 'degrees', 'ppm', 'ppm^2', None, None, None, None, None)
    }
    
    def save(self, *args, **kwargs):
        '''Creates a DataFrame properly encapsulating the associated file data'''

        # Allow overrides through optional keyword arguments in save()
        kwargs.setdefault('var_name', self.config.get('var_name'))
        kwargs.setdefault('timestamp', self.config.get('timestamp'))
        self.config.update(kwargs)

        if not all((self.config.get('var_name'), self.config.get('timestamp'))):
            raise AttributeError('One or more required configuration parameters were not provided')

        # HDF5/Matlab file interface
        f = self.file_handler(self.filename)

        # Data frame
        try:
            df = pd.DataFrame(f.get(self.config.get('var_name'))[:],
                columns=self.config.get('columns'))

        except TypeError:
            raise ValueError('Could not get at the variable named "%s"' % self.config.get('var_name'))
            
        # Fix the precision of data values
        for col in self.config.get('formats').keys():
            df[col] = df[col].map(lambda x: float(self.config['formats'][col] % x))

        return df


