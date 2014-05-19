import sys
import csv
import datetime
import os
import unittest
import pandas as pd
import numpy as np
import h5py
from lxml import etree
from fluxpy.colors import DivergingColors

class TestColors(unittest.TestCase):
    '''Tests the colors module'''

    base_string = "['rgb(165,0,38)','rgb(215,48,39)','rgb(244,109,67)','rgb(253,174,97)','rgb(254,224,144)','rgb(255,255,191)','rgb(224,243,248)','rgb(171,217,233)','rgb(116,173,209)','rgb(69,117,180)','rgb(49,54,149)']"
    base_array = [
        'rgb(165,0,38)',
        'rgb(215,48,39)',
        'rgb(244,109,67)',
        'rgb(253,174,97)',
        'rgb(254,224,144)',
        'rgb(255,255,191)',
        'rgb(224,243,248)',
        'rgb(171,217,233)',
        'rgb(116,173,209)',
        'rgb(69,117,180)',
        'rgb(49,54,149)'
    ]

    def test_diverging_color_scale(self):
        '''Tests that DivergingColors scales can be set up correctly'''
        scale = DivergingColors('test', base=self.base_string)
        self.assertEqual(scale.base, self.base_array)
        self.assertEqual(scale.rgb2hex(255, 255, 255), '#ffffff')

    def test_hex_color_conversion(self):
        scale = DivergingColors('test', base=self.base_string)
        self.assertEqual(scale.hex_colors(), [
            '#a50026',
            '#d73027',
            '#f46d43',
            '#fdae61',
            '#fee090',
            '#ffffbf',
            '#e0f3f8',
            '#abd9e9',
            '#74add1',
            '#4575b4',
            '#313695'
        ])

    def test_divering_styles(self):
        scale = DivergingColors('test', base=self.base_string)
        self.assertEqual([etree.tostring(i) for i in scale.kml_styles(alpha=0.5)], [
            '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test+5"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7f2600a5</color></PolyStyle></Style>',
            '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test+4"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7f2730d7</color></PolyStyle></Style>',
            '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test+3"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7f436df4</color></PolyStyle></Style>',
            '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test+2"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7f61aefd</color></PolyStyle></Style>',
            '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test+1"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7f90e0fe</color></PolyStyle></Style>',
            '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test+0"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7fbfffff</color></PolyStyle></Style>',
            '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test-1"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7ff8f3e0</color></PolyStyle></Style>',
            '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test-2"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7fe9d9ab</color></PolyStyle></Style>',
            '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test-3"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7fd1ad74</color></PolyStyle></Style>',
            '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test-4"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7fb47545</color></PolyStyle></Style>',
            '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test-5"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7f953631</color></PolyStyle></Style>'
        ])


if __name__ == '__main__':
    unittest.main()


