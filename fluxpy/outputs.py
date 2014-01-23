'''
For generating specific, derived outputs from spatio-temporal data. If a class
here has the render() method on one of its instances, the method is expected
to return a string or sequence of strings where each string is a file system 
path (either a directory or a file).
'''

import datetime, os, sys, re, math, warnings, ipdb #FIXME
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from zipfile import ZipFile, ZIP_DEFLATED
from matplotlib.collections import PatchCollection
from pykml.factory import KML_ElementMaker as KML
from lxml import etree
from shapely.geometry import Point
from fluxpy import DB, DEFAULT_PATH, RESERVED_COLLECTION_NAMES
from fluxpy.colors import COLORS, DivergingColors

class AbstractGridView:
    '''
    An abstract class of gridded outputs.
    '''
    colors = dict([(n, DivergingColors(n)) for n in COLORS.keys()])

    def __init__(self, mediator, model, collection_name):
        self.mediator = mediator
        self.model = model
        self.collection_name = collection_name
        self.field_units = dict(zip(model.defaults.get('columns'),
            model.defaults.get('units')))

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


class AbstractScoreView(AbstractGridView):
    '''
    An abstract class of outputs based on standard scores (z scores).
    '''

    def __labels__(self, sigmas, clamped=False):
        '''Create legend labels for standard scores (z scores)'''
        labels = []

        # e.g. create [-2, -1, 0, 1, 2] for sigmas=2
        bins = range(-sigmas, 0)
        bins.extend(range(0, (sigmas + 1)))

        for value in reversed(bins):
            if value > 0:
                labels.append('z Score: +%d' % value)

            elif value == 0:
                labels.append('Mean')

            else:
                labels.append('z Score: %d' % value)

        if clamped:
            labels[0] = '</= %s' % labels[0]
            labels[-1] = '>/= %s' % labels[-1]

        return labels

    def __score_style__(self, score, color):
        num_score_classes = self.colors.get(color).score_length

        # Calculates the style ID of the color to use
        if score >= 0:
            color = '%s+' % color

        # If the number of standard deviations is outside the number of classes
        #   provided, clamp the style to the highest (or lowest) class
        if num_score_classes <= abs(score):
            score = (score * num_score_classes) / abs(score)

        return ('#%s%d' % (color, score)).lower()

    def __scores__(self, series):
        # Calculates z scores for a given series
        mean = series.mean()
        std = series.std()
        return series.apply(lambda x: x - mean).apply(lambda x: x * (1/std))


class KMLView(AbstractScoreView):
    '''
    Writes out KML files from spatio-temporal data provided by a Mediator.
    '''
    alpha = 1.0
    filename_pattern = '%s_%d.kml' # Must have %s and %d format strings in name
    legend_size = (2.5, 5.0) # Size of the legend in inches

    def __legend__(self, dimensions, style, path, x_fraction=0.1, y_fraction=0.95):
        dim = map(str, dimensions)

        # Note: KML does not use SVG, matplotlib drawing orientation; instead,
        #   fractional position is measured from the bottom left corner
        return KML.ScreenOverlay(
            KML.name('Legend'),
            KML.overlayXY(x=str(x_fraction), y=str(y_fraction), xunits='fraction', yunits='fraction'),
            KML.screenXY(x='0', y='1', xunits='fraction', yunits='fraction'),
            KML.rotationXY(x='0', y='0', xunits='fraction', yunits='fraction'),
            KML.Icon(KML.href(path)),
            KML.size(x=dim[0], y=dim[1], xunits='pixels', yunits='pixels'))

    def __legend_vertical__(self, levels=5, origin=(0, 0), vscale=100000):
        # Generate a vertical legend for error
        elements = []
        z = 1
        while z <= levels:
            # Assumes that 1 unit height (vscale) is the mean error
            elements.append(KML.Placemark(
                KML.name('+%d z Score' % (z - 1) if z > 1 else 'Mean Error'),
                KML.Style(
                    KML.IconStyle(
                        KML.Icon(
                            KML.href('http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')))),
                KML.Point(
                    KML.extrude(1),
                    KML.altitudeMode('absolute'),
                    KML.coordinates(('%d,%d,' % (origin[0] + z,
                        origin[1])) + str(z * vscale)))))
            z += 1

        return elements

    def static_3d_grid_view(self, query, output_path, keys=('values', 'errors'),
            color='BrBG11', vscale=100000):
        '''
        Generates a static (no time component) KML view of gridded, 3D data 
        using up to two fields, given by the dictionary keys, in the connected 
        data e.g. the first field will be used to encode color and the second
        field to encode the KML Polygon extrusion height. Assumes that each grid
        cell has a single longitude-latitude pair describing its centroid.
        '''
        dfs = self.__query__(query)
        file_paths = [] # Remember all files that may need to be bundled in KMZ
        scale = self.colors.get(color)

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

        i = 0 # Iterate through the returned DataFrames

        # Parse out the identifier and the DataFrame
        for ident, df in dfs.items():
            placemarks = [] # Initial container

            # Calculate z scores for the values
            df['z%s' % keys[0]] = s1 = self.__scores__(df[keys[0]]).apply(math.ceil)
            df['z%s' % keys[1]] = s2 = self.__scores__(df[keys[1]]).apply(lambda x: math.ceil(x) + 1 if x > 0 else 1)

            # Generate a legend graphic and get the <ScreenOverlay> element for such a graphic
            legend = Legend(self.legend_size, zip(scale.hex_colors(),
                self.__labels__(scale.score_length, len(s1.unique()) > len(scale))),
                output_path, color)

            # Iterate through the rows of the Data Frame
            for j, series in df.iterrows():
                s1 = series['z%s' % keys[0]]
                s2 = series['z%s' % keys[1]]

                altitude = (s2 * vscale) 
                coords = self.__square_bounds__((series['x'], series['y']), altitude)

                placemarks.append(KML.Placemark(
                    KML.description(desc_tpl.format(**dict(series))),
                    KML.styleUrl(self.__score_style__(s1, color)),
                    KML.Polygon(
                        KML.extrude(1),
                        KML.altitudeMode('absolute'),
                        KML.outerBoundaryIs(
                            KML.LinearRing(
                                KML.coordinates(*coords))))))

            preamble = list(scale.kml_styles(outlines=False, alpha=self.alpha))
            preamble.append(KML.name(self.collection_name))

            # Add the legends and the <Folder> element with <Placemarks>
            preamble.extend(self.__legend_vertical__(vscale=vscale))
            preamble.extend([
                # Calculate the legend image dimensions based on its size in inches and the DPI
                self.__legend__(map(lambda x: x * legend.dpi, self.legend_size),
                    color, legend.file_path),
                KML.Folder(KML.name(ident), *placemarks)
            ])

            doc = KML.Document(*preamble)

            with open(os.path.join(output_path, self.filename_pattern % (ident, i)), 'wb') as stream:
                stream.write(etree.tostring(doc))

            file_paths.append(legend.render())

            i += 1

        file_paths.insert(0, output_path)

        return file_paths


class KMZView:
    '''
    A Zipped KML view; a ZIP archive with KML files and dependencies (e.g.
    image overlays, icons) inside.
    '''
    kml_matcher = re.compile(r'.+\.kml$')

    def __init__(self, path, files):
        self.path = path
        self.filename = os.path.join(path, 'output.kmz')
        self.files = files

    def render(self, files=None):
        if files is not None:
            self.files = files

        with ZipFile(self.filename, 'w', ZIP_DEFLATED) as archive:
            for path in self.files:
                if os.path.isdir(path):
                    for filename in os.listdir(path):
                        if self.kml_matcher.match(filename) is not None:
                            archive.write(os.path.join(path, filename), filename)

                else:
                    archive.write(path, os.path.basename(path))


class Legend:
    '''
    A legend for a classification scale based on colored parcels. The entries
    are drawn as square cells in a vertical list.
    '''

    def __init__(self, size, entries, path='.', scale_name='legend'):
        self.bg_color = '#000000'

        # Pad the legend entries to keep them the right size
        while len(entries) < 11:
            entries.append((self.bg_color, ''))

        # Unzip a sequence of (color, label) tuples
        self.colors, self.labels = zip(*entries)
        self.dpi = 92.0 # Should be float
        self.width = self.dpi * size[0] # e.g. 2.0 inches
        self.height = self.dpi * size[1] # e.g. 5.0 inches
        self.figure, self.axis = plt.subplots()
        self.file_path = os.path.join(path, '%s.png' % scale_name)
        self.figure.set_tight_layout(False)
        self.figure.set_size_inches(*size)

        # Reverse the labels and color order; the drawing process is backwards
        #   from intuition
        self.labels = self.labels[::-1]
        self.colors = self.colors[::-1]

        # Supress warnings about these axes and the tight layout
        warnings.filterwarnings('ignore', r'.*tight_layout.*',
            UserWarning, r'.*figure.*')

    def __label__(self, xy, text, x_offset=0):
        # Calls a text label on the plot
        plt.text(xy[0] - (x_offset / self.dpi), xy[1], text, ha='left', va='bottom',
            family='sans-serif', size=13, color='#ffffff')

    def render(self, patch_size=0.5, alpha=1.0, x_offset=100):
        '''Draws the legend graphic and saves it to a file.'''
        n = len(self.colors)
        s = patch_size

        # This offset is transformed to "data" coordinates (inches)
        left_offset = (-s * 1.5) - (x_offset / self.dpi)

        # Create grid to plot the artists
        grid = np.concatenate((
            np.zeros(n).reshape(n, 1),
            np.arange(-n, 1)[1:].reshape(n, 1)
        ), axis=1)

        plt.text(left_offset, 1.1, 'Legend', family='sans-serif',
            size=14, weight='bold', color='#ffffff')

        patches = []
        for i in range(n):
            # Add a rectangle
            rect = mpatches.Rectangle(grid[i] - [0, 0], s, s, ec='none')
            patches.append(rect)
            self.__label__(grid[i], self.labels[i], x_offset)

        collection = PatchCollection(patches, alpha=alpha)

        # Space the patches and the text labels
        collection.set_offset_position('data')
        collection.set_offsets(np.array([
            [left_offset, 0]
        ]))

        collection.set_facecolors(self.colors)
        #collection.set_edgecolor('#ffffff') # Draw color for box outlines

        self.axis.add_collection(collection)

        plt.axis('equal')
        plt.axis('off')
        plt.savefig(self.file_path, facecolor=self.bg_color, dpi=self.dpi,
            pad_inches=0)

        return self.file_path


if __name__ == '__main__':
    from fluxpy.mediators import *
    from fluxpy.models import *
    output_path = '/home/kaendsle/Desktop/'
    kml = KMLView(Grid3DMediator(), KrigedXCO2Matrix, 'xco2')
    files = kml.static_3d_grid_view({}, output_path, color='RdBu3')
    kmz = KMZView(output_path, files)
    kmz.render()

    #legend = Legend((2, 5), DivergingColors('RdBu3', COLORS.get('RdBu3')).legend_entries(), output_path, 'RdBu3')
    #legend = Legend((2, 5), DivergingColors('BrBG11').legend_entries(), output_path, 'BrBG11')
    #legend.render()




