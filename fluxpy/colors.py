'''
Ancillary tools for working with carbon science data in Python, in particular,
tools for transforming RGB color value arrays into KML styles.
'''

import math
from pykml.factory import KML_ElementMaker as KML

COLORS = { # Cynthia Brewer's color scales (colorbrewer2.org)
    'dBrBG11': ['rgb(84,48,5)','rgb(140,81,10)','rgb(191,129,45)','rgb(223,194,125)','rgb(246,232,195)','rgb(245,245,245)','rgb(199,234,229)','rgb(128,205,193)','rgb(53,151,143)','rgb(1,102,94)','rgb(0,60,48)'],
    'dRdBu3': ['rgb(239,138,98)','rgb(247,247,247)','rgb(103,169,207)']
}

class AbstractColors(object):
    def __init__(self, name, base=None):
        self.name = name.lower()

        if COLORS.get(name) is not None:
            self.base = COLORS.get(name)
        
        if base is not None:
            if isinstance(base, str):
                self.base = map(lambda s: s.strip("'"),
                    base.strip('[]()""').split("','"))
                    
            elif isinstance(base, list) or isinstance(base, tuple):
                self.base = base

    def __len__(self):
        return len(self.base)

    def hex_colors(self):
        '''Generates hexadecimal color codes for each color in the ramp'''
        return map(lambda x: self.rgb2hex(*map(int, x.strip('rgb()').split(','))),
            self.base)
            
    def kml_colors(self, alpha=1.0):
        '''Generates PyKML <Color> instances for each color in the ramp'''
        return map(lambda c: KML.color('{a}{b}{g}{r}'.format(**{
            'a': '{:02x}'.format(int(alpha * 255)),
            'r': c[1:3],
            'g': c[3:5],
            'b': c[5:7]
        })), self.hex_colors())

    def legend_entries(self):
        return zip(self.hex_colors(), self.labels())

    def rgb2hex(self, r, g, b):
        return '#{:02x}{:02x}{:02x}'.format(r, g, b)


class DivergingColors(AbstractColors):
    '''
    Represents a divergent color scale; expects an odd number of colors in
    descending order of thir associated quanitities (e.g. if "red" == 5 and
    "blue" == 1, then they should be ordered "red" first and "blue" last). This
    is because Cynthia Brewer's color scales are typically ordered "warm" to
    "cool" colors. Assumes z-scores are used to map data to color segments.
    '''
    base = COLORS.get('dBrBG11')

    def __init__(self, *args, **kwargs):
        super(DivergingColors, self).__init__(*args, **kwargs)

        # Set the score length, the number of classes about the mean supported
        # Initialize the z-score counter (for diverging color scale, the number
        #   of z-scores possible is the number of available classes minus 1
        #   divided by half)
        self.score_length = int(math.floor(len(self) * 0.5))

    def labels(self):
        '''Generate a list of text labels to use for the colors'''
        labels = []

        i = self.score_length
        for color in self.base:
            if i > 0:
                code = 'z Score: +%d' % i

            elif i == 0:
                code = 'Mean'

            else:
                code = 'z Score: %d' % i

            labels.append(code)

            i -= 1 # Counting down

        return labels
    
    def kml_styles(self, outlines=False, alpha=1.0):
        '''Generates PyKML <Style> instances for each color in the ramp'''
        styles = list()

        i = self.score_length
        for color in self.kml_colors(alpha):
            if i >= 0:
                code = '%s+%d'

            else:
                code = '%s%d'

            if outlines:
                styles.append(KML.Style(KML.PolyStyle(color),
                    id=(code % (self.name, i))))
                
            else:
                styles.append(KML.Style(KML.LineStyle(KML.width(0)),
                    KML.PolyStyle(color), id=(code % (self.name, i))))

            i -= 1 # Counting down

        return styles


