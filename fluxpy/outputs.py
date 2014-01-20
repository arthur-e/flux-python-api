'''
For generating specific, derived outputs from spatio-temporal data.
'''

import ipdb#FIXME
import datetime, os, sys, re, math
import matplotlib.pyplot as plt; plt.rcdefaults()
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
from pykml.factory import KML_ElementMaker as KML
from lxml import etree
from shapely.geometry import Point
from fluxpy import DB, DEFAULT_PATH, RESERVED_COLLECTION_NAMES
from fluxpy.colors import *

class Legend:
    '''
    A legend for a classification scheme based on colored parcels. The entries
    are drawn as square cells in a vertical list.
    '''

    def __init__(self, entries, scale_name=None):
        # Unzip a sequence of (color, label) tuples
        self.colors, self.labels = zip(*entries)
        fig, self.ax = plt.subplots()
        self.filename = '%s.png' % (scale_name or 'legend')

    def __label__(self, xy, text, item_width):
        # Calls a text label on the plot
        plt.text(xy[0] + (item_width * 1.5), xy[1], text, ha='left', va='bottom',
            family='sans-serif', size=13)

    def render(self, patch_size=0.5, alpha=1.0):
        '''Draws the legend graphic and saves it to a file.'''
        n = len(self.colors)
        s = patch_size

        # Create grid to plot the artists
        grid = np.concatenate((
            np.ones(n).reshape(n, 1),
            np.arange(n + 1)[1:].reshape(n, 1)
        ), axis=1)

        patches = []
        for i in range(n):
            # Add a rectangle
            rect = mpatches.Rectangle(grid[i] - [0.01, 0.01], s, s, ec='none')
            patches.append(rect)
            self.__label__(grid[i], self.labels[1], patch_size)

        colors = np.linspace(0, 1, len(patches))
        collection = PatchCollection(patches, cmap=plt.cm.hsv, alpha=alpha)
        collection.set_facecolors(self.colors)
        self.ax.add_collection(collection)

        plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
        plt.axis('equal')
        plt.axis('off')

        plt.savefig(self.filename)


class KMLView:
    '''
    Writes out KML files from spatio-temporal data provided by a Mediator.
    '''
    alpha = 1.0
    filename_pattern = 'output%d.kml' # Must have %d format string in name
    colors = {
        'BrBG11': DivergingColors('brbg11')
    }

    def __init__(self, mediator, model, collection_name):
        self.mediator = mediator
        self.model = model
        self.collection_name = collection_name
        self.field_units = dict(zip(model.defaults.get('columns'),
            model.defaults.get('units')))

    def __legend__(self, style, path):
        return KML.ScreenOverlay(
            KML.overlayXY(x='0.0', y='0.0', xunits='fraction', yunits='fraction'),
            KML.screenXY(x='0.05', y='0.05', xunits='fraction', yunits='fraction'),
            KML.icon(KML.href(path)))

    def __score_style__(self, score, style):
        # Calculates the style ID of the color to use
        if score >= 0:
            style = '%s+' % style

        return ('#%s%d' % (style, score)).lower()

    def __scores__(self, series):
        # Calculates z scores for a given series
        mean = series.mean()
        std = series.std()
        return series.apply(lambda x: x - mean).apply(lambda x: x * (1/std))

    def __square_bounds__(self, coords, altitude=None):
        # For this gridded product, assume square cells; get grid cell resolution
        gridres = self.model.defaults.get('resolution').get('x_length')

        # Get the rectangular bounds of the model cell at the grid resolution
        bounds = map(str, Point(coords).buffer(gridres, 4).bounds)

        # Coordinates should be specified counter-clockwise
        # (https://developers.google.com/kml/documentation/kmlreference#polygon)
        # Permute corner creation from bounds; bounds=(minx, miny, maxx, maxy)
        coords = ((bounds[0], bounds[3]), (bounds[0], bounds[1]),
            (bounds[2], bounds[1]), (bounds[2], bounds[3]),
            (bounds[0], bounds[3]))

        if altitude is not None:
            coords = map(lambda c: (c[0], c[1], str(altitude)), coords)

        return ' '.join(map(lambda c: ','.join(c), coords))

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

            # Calculate z scores for the values
            dfs[i]['z%s' % keys[0]] = self.__scores__(dfs[i][keys[0]]).apply(math.ceil)
            dfs[i]['z%s' % keys[1]] = self.__scores__(dfs[i][keys[1]]).apply(lambda x: math.ceil(x) + 1 if x > 0 else 1)

            # Generate a legend graphic and get the <ScreenOverlay> element for such a graphic
            legend = Legend(self.colors.get(style).legend_entries(), 'BrBG11')
            legend_overlay = self.__legend__('BrBG11', legend.filename) #TODO

            # Iterate through the rows of the Data Frame
            for j, series in dfs[i].iterrows():
                altitude = (series['z%s' % keys[1]] * 100000) 
                coords = self.__square_bounds__((series['x'], series['y']), altitude)

                placemarks.append(KML.Placemark(
                    KML.description(desc_tpl.format(**dict(series))),
                    KML.styleUrl(self.__score_style__(series['z%s' % keys[0]], 'BrBG11')),
                    KML.Polygon(
                        KML.extrude(1),
                        KML.altitudeMode('absolute'),
                        KML.outerBoundaryIs(
                            KML.LinearRing(
                                KML.coordinates(*coords))))))

            preamble = list(self.colors.get('BrBG11').kml_styles(outlines=False,
                alpha=self.alpha))
            preamble.extend([
                KML.name(self.collection_name),
                legend_overlay, # The <ScreenOverlay> element
                KML.Folder(KML.name(self.collection_name), *placemarks)
            ])

            doc = KML.Document(*preamble)

            with open(os.path.join(output_path, self.filename_pattern % i), 'wb') as stream:
                stream.write(etree.tostring(doc))

            i += 1


if __name__ == '__main__':
    from fluxpy.mediators import *
    from fluxpy.models import *
    kml = KMLView(Grid3DMediator(), KrigedXCO2Matrix, 'xco2')
    kml.static_3d_grid_view({}, '/home/kaendsle/Desktop/')




