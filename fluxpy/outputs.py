'''
For generating specific, derived outputs from spatio-temporal data.
'''

import ipdb#FIXME
import datetime, os, sys, re
import pandas as pd
from pykml.factory import KML_ElementMaker as KML
from pykml import parser as kml_parser
from lxml import etree
from shapely.geometry import Point
from pymongo import MongoClient
from fluxpy import DB, DEFAULT_PATH, RESERVED_COLLECTION_NAMES

class KMLView:
    '''
    Writes out KML files from spatio-temporal data provided by a Mediator.
    '''
    filename_pattern = 'output%d.kml' # Must have %d format string in name
    
    def __init__(self, mediator, model, collection_name):
        self.mediator = mediator
        self.model = model
        self.collection_name = collection_name
        self.field_units = dict(zip(model.defaults.get('columns'),
            model.defaults.get('units')))
        
    def __square_bounds__(self, coords):
        # For this gridded product, assume square cells; get grid cell resolution
        gridres = self.model.defaults.get('resolution').get('x_length')
        
        # Get the rectangular bounds of the model cell at the grid resolution
        bounds = bounds=map(str, Point(coords).buffer(gridres, 4).bounds)

        # Permute corner creation from bounds; bounds=(minx, miny, maxx, maxy)
        return (','.join((bounds[0], bounds[1])), ','.join((bounds[0], bounds[3])),
            ','.join((bounds[2], bounds[3])), ','.join((bounds[2], bounds[1])),
            ','.join((bounds[0], bounds[1])))
        
    def __query__(self, query_object):
        return self.mediator.load_from_db(self.collection_name, query_object)

    def static_3d_grid_view(self, query, output_path, keys=('value', 'error')):
        '''
        Generates a static (no time component) KML view of gridded, 3D data 
        using up to two fields, given by the dictionary keys, in the connected 
        data e.g. the first field will be used to encode color and the second
        field to encode the KML Polygon extrusion height. Assumes that each grid
        cell has a single longitude-latitude pair describing its centroid.
        '''
        dfs = self.__query__(query)
        
        if not os.path.exists(output_path):
            raise ValueError('The specified output_path does not exist or cannot be read')

        # KML Placemark description template
        desc_tpl = '<h3>{{x}}, {{y}}</h3><h4>{k1}: %s {u1}<h4>'.format(x='{x}',
                y='{y}', k1=keys[0], u1=self.field_units[keys[0]])

        # Sets up a new format string with field names and units e.g. "Value: {value} ppm"
        if len(keys) > 1:
            desc_tpl += '<h4>{k2}: %s {u2}<h4>'.format(k2=keys[1],
                u2=self.field_units[keys[1]])
                
            desc_tpl = desc_tpl % ('{%s}' % keys[0], '{%s}' % keys[1])
            
        else:
            desc_tpl = desc_tpl % ('{%s}' % keys[0])
            
        # Iterate through the returned DataFrames
        i = 0
        while i < len(dfs):
            placemarks = []
        
            # Iterate through the rows of the Data Frame
            for j, series in dfs[i].iterrows():
                coords = self.__square_bounds__((series['x'], series['y']))
            
                placemarks.append(KML.Placemark(
                    KML.description(desc_tpl.format(**dict(series))),
                    KML.extrude(1),
                    KML.tesselate(1),
                    KML.Polygon(
                        KML.outerBoundaryIs(
                            KML.LinearRing(
                                KML.coordinates(*coords))))))
        
            doc = KML.Document(
                KML.name(self.collection_name),
                KML.Folder(KML.name(self.collection_name), *placemarks))

            with open(os.path.join(output_path, self.filename_pattern % i), 'wb') as stream:
                stream.write(etree.tostring(doc))
                
            i += 1


