'''
For generating specific, derived outputs from spatio-temporal data. If a class
here has the render() method on one of its instances, the method is expected
to return a string or sequence of strings where each string is a file system 
path (either a directory or a file).
'''

import datetime, os, sys, re, math, warnings
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from zipfile import ZipFile, ZIP_DEFLATED
from matplotlib.collections import PatchCollection
from pykml.factory import nsmap
from pykml.factory import KML_ElementMaker as KML
from pykml.factory import GX_ElementMaker as GX
from lxml import etree
from shapely.geometry import Point
from fluxpy import DB, DEFAULT_PATH, RESERVED_COLLECTION_NAMES
from fluxpy.colors import COLORS, DivergingColors, SequentialColors

class AbstractGridView:
    '''
    An abstract class of gridded outputs.
    '''
    alpha = 1.0
    colors = dict([(n, SequentialColors(n)) for n in COLORS.keys()])
    filename_pattern = '%s_%d.kml' # Must have %s and %d format strings in name
    legend_size = (2.5, 5.0) # Size of the legend in inches

    def __init__(self, mediator, model, collection_name):
        self.mediator = mediator
        self.model = model
        self.collection_name = collection_name
        self.field_units = dict(zip(model.columns, model.units))

    def __breakpoints__(self, series, bins):
        if not isinstance(bins, int):
            raise TypeError('Integer bins argument expected')

        steps = 10 
        ll = 0 # Lower limit

        # If there is an odd number of bins...
        if bins % 2 > 0:
            ll = 5

        # We'll move the decimal place left by one (1) for these calculations...
        bps = range(-(bins * 5), 0, steps)
        bps.extend(range(ll, (bins * 5), steps))
        bps.append(bins * 5)
        bps = map(lambda x: (x * 0.1 * series.std()) + series.mean(), bps)
        bps[0] = -np.inf
        bps.pop()
        bps.append(np.inf)

        assert len(bps) - 1 == bins, 'The correct number of breakpoints could not be calculated'
        return bps

    def __description__(self, keys):
        # Remove plurals
        field_names = [s.rstrip('s') for s in keys if s is not None]

        # KML Placemark description template
        desc_tpl = '<h3>{{x}}, {{y}}</h3><h4>{k1}: %s {u1}<h4>'.format(x='{x}',
                y='{y}', k1=field_names[0], u1=self.field_units[keys[0]])

        # Sets up a new format string with field names and units e.g. "Value: {value} ppm"
        if len(keys) > 1:
            desc_tpl += '<h4>{k2}: %s {u2}<h4>'.format(k2=field_names[1],
                u2=self.field_units[keys[1]])

            desc_tpl = desc_tpl % ('{%s}' % keys[0], '{%s}' % keys[1])

        else:
            desc_tpl = desc_tpl % ('{%s}' % keys[0])

        return desc_tpl

    def __labels__(self, breakpoints, units='', fmt='%.1f'):
        bps = [bp for bp in breakpoints if np.isfinite(bp)]
        labels = [('</= ' + fmt) % bps[0]]

        i = 1
        while i < len(bps):
            labels.append(('(' + fmt + ' - ' + fmt + ']') % (bps[i - 1], bps[i]))
            i += 1

        labels.append(('> ' + fmt) % bps[-1])

        return [('%s ' + units) % s for s in labels]

    def __legend__(self, dimensions, style, path, x_fraction=0.1, y_fraction=0.95):
        dim = map(str, dimensions)

        # Note: KML does not use SVG, matplotlib drawing orientation; instead,
        #   fractional position is measured from the bottom left corner
        return KML.ScreenOverlay(
            KML.name('Legend'),
            KML.overlayXY(x=str(x_fraction), y=str(y_fraction), xunits='fraction', yunits='fraction'),
            KML.screenXY(x='0', y='1', xunits='fraction', yunits='fraction'),
            KML.rotationXY(x='0', y='0', xunits='fraction', yunits='fraction'),
            KML.Icon(KML.href(os.path.basename(path))),
            KML.size(x=dim[0], y=dim[1], xunits='pixels', yunits='pixels'))

    def __style__(self, label):
        return '#%s' % str(label)

    def __square_bounds__(self, coords, altitude=None):
        # For this gridded product, assume square cells; get grid cell resolution
        gridres = self.model.gridres.get('x')

        # Get the rectangular bounds of the model cell at the grid resolution
        if not any(map(lambda x: np.isnan(x), coords)):
            bounds = map(str, Point(coords).buffer(gridres, 4).bounds)

        else:
            return None # Skip NaNs

        # Coordinates should be specified counter-clockwise
        # (https://developers.google.com/kml/documentation/kmlreference#polygon)
        # Permute corner creation from bounds; bounds=(minx, miny, maxx, maxy)
        coords = ((bounds[0], bounds[3]), (bounds[0], bounds[1]),
            (bounds[2], bounds[1]), (bounds[2], bounds[3]),
            (bounds[0], bounds[3]))

        if altitude is not None:
            coords = map(lambda c: (c[0], c[1], str(altitude)), coords)

        return ' '.join(map(lambda c: ','.join(c), coords))

    def __tour__(self):
        # Define a variable for the Google Extensions namespace URL string
        gxns = '{' + nsmap['gx'] + '}'

        tour = GX.Tour(KML.name('Play me!'), GX.Playlist())

        tour.Playlist.append(
            GX.FlyTo(
            GX.duration(5),
            GX.flyToMode('smooth'),
            KML.LookAt(
                KML.longitude(-45),
                KML.latitude(-43),
                KML.altitude(0),
                KML.heading(355),
                KML.tilt(55),
                KML.range(6000000.0),
                KML.altitudeMode('absolute'))))

        tour.Playlist.append(
            GX.FlyTo(
            GX.duration(10),
            GX.flyToMode('smooth'),
            KML.LookAt(
                KML.longitude(-80),
                KML.latitude(63),
                KML.altitude(0),
                KML.heading(345),
                KML.tilt(45),
                KML.range(10000000.0),
                KML.altitudeMode('absolute'))))

        tour.Playlist.append(
            GX.FlyTo(
            GX.duration(10),
            GX.flyToMode('smooth'),
            KML.LookAt(
                KML.longitude(-131),
                KML.latitude(63),
                KML.altitude(0),
                KML.heading(345),
                KML.tilt(35),
                KML.range(20000000.0),
                KML.altitudeMode('absolute'))))

        tour.Playlist.append(
            GX.FlyTo(
            GX.duration(5),
            GX.flyToMode('smooth'),
            KML.LookAt(
                KML.longitude(53),
                KML.latitude(25),
                KML.altitude(0),
                KML.heading(270),
                KML.tilt(35),
                KML.range(20000000.0),
                KML.altitudeMode('absolute'))))

        tour.Playlist.append(
            GX.FlyTo(
            GX.duration(10),
            GX.flyToMode('smooth'),
            KML.LookAt(
                KML.longitude(140),
                KML.latitude(-4),
                KML.altitude(0),
                KML.heading(0),
                KML.tilt(55),
                KML.range(10000000.0),
                KML.altitudeMode('absolute'))))

        return tour

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

    def __style__(self, score, color):
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


class KMZWrapper:
    '''
    Generates a Zipped KML; a ZIP archive with KML files and dependencies (e.g.
    image overlays, icons) inside.
    '''
    kml_kmz_matcher = re.compile(r'.+\.(kml|kmz)$')

    def __init__(self, output_path, kml_file):
        self.output_path = output_path
        self.file_path = os.path.dirname(kml_file)
        self.kml_file = kml_file

    def __add_path__(self, path):
        if self.kml_kmz_matcher.match(path) is None:
            self.archive.write(os.path.join(self.file_path, path),
                os.path.basename(path))

    def render(self, output_path='./output.kmz'):
        self.output_path = output_path

        with ZipFile(self.output_path, 'w', ZIP_DEFLATED) as self.archive:
            self.archive.write(self.kml_file, os.path.basename(self.kml_file))

            for path in os.listdir(self.file_path):
                self.__add_path__(path)

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


class StaticKMLView(AbstractGridView):
    '''
    Writes out KML files from spatio-temporal data provided by a Mediator.
    '''

    def render(self, query, output_path, keys=('values', 'errors'),
            bins=3, color='BrBG11', vscale=1000, vpow=2, cutoffs=(None, 1.2)):
        '''
        Generates a KML view of gridded, 3D data using up to two fields,
        given by the dictionary keys, in the connected data e.g. the first
        field will be used to encode color and the second field to encode the
        KML Polygon extrusion height. Assumes that each grid cell has a
        single longitude-latitude pair describing its centroid. The keys
        argument is a sequence of strings representing field names to use for
        these symbols, in order: the polygon style, the altitude.
        '''
        file_paths = [] # Remember all files that may need to be bundled in KMZ
        scale = self.colors.get(color)

        if not os.path.exists(output_path):
            raise ValueError('The specified output_path does not exist or cannot be read')

        if bins > 9:
            raise ValueError('Cannot have more than 9 bins in sequential scales')

        # Get field names
        f1, f2 = keys

        # Get the <description> element template
        desc_tpl = self.__description__(keys)

        # Execute the query
        dfs = self.__query__(query)

        # Parse out the identifier and the DataFrame
        i = 0 # Iterate through the returned DataFrames
        for ident, df in dfs.items():
            placemarks = [] # Initial container

            # Get breakpoints, labels based on the requested number of bins
            breakpoints = self.__breakpoints__(df[f1], bins)
            labels = self.__labels__(breakpoints, self.field_units[f1])

            # Bin each value based on the breakpoints; format the labels
            df['bin'] = pd.cut(df[f1], breakpoints, labels=labels)

            if not isinstance(scale, DivergingColors):
                labels = labels[::-1] # Reverse

            # Generate a legend graphic and get the <ScreenOverlay> element for such a graphic
            legend = Legend(self.legend_size, zip(scale.hex_colors(), labels),
                output_path, ident)

            # Iterate through the rows of the Data Frame
            for j, series in df.iterrows():

                if f2 is not None:
                    coords = self.__square_bounds__((series['x'], series['y']),
                        math.pow(series[f2] * vscale, vpow)) # Altitude

                else:
                    coords = self.__square_bounds__((series['x'], series['y']))

                if coords is None:
                    continue

                placemarks.append(KML.Placemark(
                    KML.description(desc_tpl.format(**dict(series))),
                    KML.styleUrl('#%s' % series['bin']),
                    KML.Polygon(
                        KML.extrude(1),
                        KML.altitudeMode('absolute'),
                        KML.outerBoundaryIs(
                            KML.LinearRing(
                                KML.coordinates(*coords))))))

            preamble = list(scale.kml_styles(labels, outlines=False, alpha=self.alpha))
            preamble.append(KML.name(self.collection_name))

            # Add the legends and the <Folder> element with <Placemarks>
            preamble.extend([
                self.__tour__(),
                # Calculate the legend image dimensions based on its size in inches and the DPI
                self.__legend__(map(lambda x: x * legend.dpi, self.legend_size),
                    color, legend.file_path),
                KML.Folder(KML.name(ident), *placemarks)
            ])

            doc = KML.Document(*preamble)

            output_name = os.path.join(output_path, self.filename_pattern % (ident, i))
            with open(output_name, 'wb') as stream:
                stream.write(etree.tostring(doc))

            file_paths.append((output_name, legend.render(x_offset=150)))

            i += 1

        return file_paths


class ScoredKMLView(AbstractScoreView):
    '''
    Writes out KML files from spatio-temporal data provided by a Mediator
    where the values represented in the KML are standard scores (z scores).
    '''
    colors = dict([(n, DivergingColors(n)) for n in COLORS.keys()])

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

    def render(self, query, output_path, keys=('values', 'errors'),
            color='dBrBG11', vscale=100000):
        '''
        Generates a KML view of gridded, 3D data with standard scores (z scores)
        using up to two fields, given by the dictionary keys, in the connected 
        data e.g. the first field will be used to encode color and the second
        field to encode the KML Polygon extrusion height. Assumes that each grid
        cell has a single longitude-latitude pair describing its centroid.
        '''
        file_paths = [] # Remember all files that may need to be bundled in KMZ
        scale = self.colors.get(color)

        if not os.path.exists(output_path):
            raise ValueError('The specified output_path does not exist or cannot be read')

        # Get field names
        f1, f2 = map(lambda x: 'z%s' % x, keys)

        # Get the <description> element template
        desc_tpl = self.__description__(keys)

        # Execute the query
        dfs = self.__query__(query)

        # Parse out the identifier and the DataFrame
        i = 0 # Iterate through the returned DataFrames
        for ident, df in dfs.items():
            placemarks = [] # Initial container

            # Calculate z scores for the values
            df[f1] = s1 = self.__scores__(df[keys[0]]).apply(math.ceil)
            df[f2] = s2 = self.__scores__(df[keys[1]]).apply(lambda x: math.ceil(x) + 1 if x > 0 else 1)

            # Get z score labels
            labels = self.__labels__(scale.score_length, len(s1.unique()) > len(scale))

            if not isinstance(scale, DivergingColors):
                labels = labels[::-1] # Reverse

            # Generate a legend graphic and get the <ScreenOverlay> element for such a graphic
            legend = Legend(self.legend_size, zip(scale.hex_colors(), labels),
                output_path, color)

            # Iterate through the rows of the Data Frame
            for j, series in df.iterrows():

                coords = self.__square_bounds__((series['x'], series['y']),
                    (series[f2] * vscale)) # Altitude

                placemarks.append(KML.Placemark(
                    KML.description(desc_tpl.format(**dict(series))),
                    KML.styleUrl(self.__style__(series[f1], color)),
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


if __name__ == '__main__':
    from fluxpy.mediators import *
    from fluxpy.models import *
    output_path = '/home/kaendsle/Desktop/'

    #kml = ScoredKMLView(Grid3DMediator(), KrigedXCO2Matrix, 'xco2')
    #files = kml.render({}, output_path, color='dBrBG11')

    kml = StaticKMLView(Grid3DMediator(), KrigedXCO2Matrix, 'xco2')
    files = kml.render({
        '_id': datetime.datetime.strptime('2009-06-15T00:00:00', '%Y-%m-%dT%H:%M:%S')
    }, output_path, bins=3, color='BuGn3')

    kmz = KMZWrapper(output_path, files.pop()[0])
    kmz.render(os.path.join(output_path, 'static_3d_grid_sequential_3_bins.kmz'))

    #legend = Legend((2, 5), DivergingColors('dRdBu3', COLORS.get('dRdBu3')).legend_entries(), output_path, 'dRdBu3')
    #legend = Legend((2, 5), DivergingColors('dBrBG11').legend_entries(), output_path, 'dBrBG11')
    #legend.render()




