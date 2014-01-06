import datetime, os, sys, re, json, csv, pprint
import pandas as pd
import numpy as np
import scipy.io
import h5py
from dateutil.relativedelta import *
from pymongo import MongoClient
from fluxpy import DB, COLLECTION, INDEX_COLLECTION, DEFAULT_PATH

client = MongoClient() # Defaults: MongoClient('localhost', 27017)

class TransformationInterface:
    '''
    An abstract persistence transformation interface (Andy Bulka, 2001).
    '''
    
    def save(self):
        pass
    
    def load(self):
        pass
        
    def get_id(self):
        pass


class Mediator:
    '''
    A generic model for transforming data between foreign formats and the
    persistence layer of choice (MongoDB in this application). Mediator calls
    the save() method on subclasses of the TransformationInterface (those
    classes that interpret foreign formats).
    '''

    def __init__(self, path):
        if path is None:
            raise AttributeError('A file path must be specified')
            
        self.filename = path

    def save_to_db(self):
        pass
        
    def load_from_db(self);
        pass


class XCO2Matrix(TransformationInterface):
    '''
    Understands XCO2 data as formatted--Typically 6-day spans of XCO2
    concentrations (ppm) at daily intervals on a latitude-longitude grid.
    Matrix dimensions: 1311 (observations) x 6 (days).
    Columns: Longitude, latitude, XCO2 concentration (ppm), day of the year,
    year, retrieval error (ppm).
    '''

    def __init__(self, path):
        if path is None:
            raise AttributeError('A file path must be specified')
            
        self.filename = path
        
    def load(self, data):
        # Restores the file from the interchange format (dictionary)
        pass
        
    def save(self):
        # Called by a Mediator class member; should return data in interchange (dictionary)
        pass


