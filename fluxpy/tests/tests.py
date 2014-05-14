import csv
import datetime
import os
import unittest
import pandas as pd
import numpy as np
import h5py
#from lxml import etree
import sys
sys.path.append('/usr/local/project/flux-python-api/')
#from fluxpy.legacy.transform import bulk_hdf5_to_csv
from fluxpy.mediators import Grid4DMediator, Grid3DMediator, Unstructured3DMediator
from fluxpy.models import KrigedXCO2Matrix, XCO2Matrix, SpatioTemporalMatrix
#from fluxpy.colors import DivergingColors

class TestSpatioTemporalMatrixes(unittest.TestCase):
    '''Tests for proper handling of inverted CO2 surface fluxes (e.g. CASA GFED output)'''

    mediator = Grid4DMediator()
    path = '/usr/local/project/flux-python-api/fluxpy/tests/'

    def test_model_instance(self):
        '''Should properly instantiate an SpatioTemporalMatrix model instance'''
        flux = SpatioTemporalMatrix(os.path.join(self.path, 'casagfed2004.mat'),
            timestamp='2004-06-30T00:00:00', var_name='test', span=10800)

        self.assertEqual(flux.var_name, 'test')
        self.assertEqual(flux.step, 10800)
        self.assertEqual(flux.span, 10800)
        self.assertEqual(flux.timestamp, '2004-06-30T00:00:00')

    def test_model_var_name_inference(self):
        '''Should infer the var_name in an SpatioTemporalMatrix model instance'''
        flux = SpatioTemporalMatrix(os.path.join(self.path, 'casagfed2004.mat'))

        self.assertEqual(flux.var_name, 'test')

    def test_model_describe(self):
        '''Should produce metadata for a SpatioTemporalMatrix model instance'''
        flux = SpatioTemporalMatrix(os.path.join(self.path, 'casagfed2004.mat'),
            timestamp='2004-06-30T00:00:00', var_name='test',span=10800)
        
        df = flux.describe()
        self.assertEqual(df['bbox'], (-166.5, 60.5, -163.5, 68.5))
        self.assertEqual(df['bboxmd5'], '51d5738489b4ae4fa8623f867de527ce')
        self.assertEqual(df['dates'], ['2004-06-30T00:00:00', '2004-06-30T21:00:00'])
        self.assertEqual(df['gridded'], True)
        self.assertEqual(df['gridres'], {'units': 'degrees', 'x': 1.0, 'y': 1.0})
        self.assertEqual(df['spans'], [10800])
        self.assertEqual(df['steps'], [10800])
    
    def test_model_extract(self):
        '''Should extract a DataFrame in an SpatioTemporalMatrix model instance'''
        flux = SpatioTemporalMatrix(os.path.join(self.path, 'casagfed2004.mat'),
            timestamp='2004-06-30T00:00:00', var_name='test')

        df = flux.extract()
        self.assertEqual(df.shape, (10, 8))
        self.assertEqual(str(df.columns[1]), '2004-06-30 03:00:00')
        self.assertEqual(df.index.values[1], (-165.5, 61.5))

    def test_save_to_db(self):
        '''Should successfully save proper data representation to database'''
        flux = SpatioTemporalMatrix(os.path.join(self.path, 'casagfed2004.mat'),
            timestamp='2004-06-30T00:00:00', var_name='test')

        testname = 'test3'
        self.mediator.save(testname, flux)
        query = self.mediator.client[self.mediator.db_name][testname].find({
            '_id': datetime.datetime(2004, 6, 30, 0, 0, 0),
        })
        self.assertEqual(len(query[0]['values']), 10)
        self.assertEqual(query[0]['values'][0], 0.08)

        # test the mediator's summarize() method
        summary = self.mediator.summarize(testname)
        expected_summary = { 'max': 0.27000000000000002,
                             'mean': 0.14924999999999999,
                             'median': 0.15000000000000002,
                             'min': 0.0,
                             'std': 0.0044658511197943991}
        
        self.assertEqual(summary, expected_summary)


        # Drop the old collection; it will be recreated when inserting
        self.mediator.client[self.mediator.db_name].drop_collection(testname)
        self.mediator.client[self.mediator.db_name]['coord_index'].remove({
            '_id': testname
        })
        self.mediator.client[self.mediator.db_name]['metadata'].remove({
            '_id': testname
        })
    
class TestXCO2Data(unittest.TestCase):
    '''Tests for proper handling of XCO2 retrievals'''

    mediator = Unstructured3DMediator()
    path = '/usr/local/project/flux-python-api/fluxpy/tests/'

    def test_model_instance(self):
        '''Should properly instantiate a model instance'''
        xco2 = XCO2Matrix(os.path.join(self.path, 'xco2.mat'),
            timestamp='2009-06-15')

        self.assertEqual(xco2.var_name, 'XCO2')
        self.assertEqual(xco2.step, 86400)
        self.assertEqual(xco2.span, None)
        self.assertEqual(xco2.timestamp, '2009-06-15')
        
    def test_model_extract(self):
        '''Should create proper DataFrame from reading file data'''
        xco2 = XCO2Matrix(os.path.join(self.path, 'xco2.mat'),
            timestamp='2009-06-15')

        df1 = xco2.extract()
        self.assertEqual(df1.shape, (1311, 7))

        # Should allow overrides in the extract() method
        df2 = xco2.extract(timestamp='2010-01-01')
        self.assertEqual(xco2.timestamp, '2010-01-01')
            
    def test_save_to_db(self):
        '''Should successfully save proper data representation to database'''
        xco2 = XCO2Matrix(os.path.join(self.path, 'xco2.mat'),
            timestamp='2009-06-15')

        self.mediator.save('test', xco2)
        query = self.mediator.client[self.mediator.db_name]['test'].find({
            'timestamp': datetime.datetime(2009, 6, 16, 0, 0, 0),
        })
        self.assertEqual(query[0]['value'], 386.79)

        # Drop the old collection; it will be recreated when inserting
        self.mediator.client[self.mediator.db_name].drop_collection('test')
        self.mediator.client[self.mediator.db_name]['coord_index'].remove({
            '_id': 'test'
        })
        self.mediator.client[self.mediator.db_name]['metadata'].remove({
            '_id': 'test'
        })
        

class TestKrigedXCO2Data(unittest.TestCase):
    '''Tests for proper handling of kriged (gridded) XCO2 data'''

    mediator = Grid3DMediator()
    path = '/usr/local/project/flux-python-api/fluxpy/tests/'

    def test_model_instance(self):
        '''Should properly instantiate a model instance'''
        xco2 = KrigedXCO2Matrix(os.path.join(self.path, 'kriged_xco2.mat'),
            timestamp='2009-06-15')

        self.assertEqual(xco2.var_name, 'krigedData')
        self.assertEqual(xco2.step, None)
        self.assertEqual(xco2.span, 518400)
        self.assertEqual(xco2.timestamp, '2009-06-15')
        
    def test_model_extract(self):
        '''Should create proper DataFrame from reading file data'''
        xco2 = KrigedXCO2Matrix(os.path.join(self.path, 'kriged_xco2.mat'),
            timestamp='2009-06-15')

        df1 = xco2.extract()
        self.assertEqual(df1.shape, (14210, 9))

        # Should allow overrides in the extract() method
        df2 = xco2.extract(timestamp='2010-01-01')
        self.assertEqual(xco2.timestamp, '2010-01-01')
            
    def test_save_to_db(self):
        '''Should successfully save proper data representation to database'''
        xco2 = KrigedXCO2Matrix(os.path.join(self.path, 'kriged_xco2.mat'),
            timestamp='2009-06-15')

        testname = 'test2'
        self.mediator.save(testname, xco2)
        query = self.mediator.client[self.mediator.db_name][testname].find({
            '_id': datetime.datetime(2009, 6, 15, 0, 0, 0),
        })
        self.assertEqual(query[0]['_span'], 518400)
        self.assertEqual(len(query[0]['values']), 14210)

        # test the mediator's summarize() method
        summary = self.mediator.summarize(testname)
        expected_summary = { 'max': 0.27000000000000002,
                             'mean': 0.14924999999999999,
                             'median': 0.15000000000000002,
                             'min': 0.0,
                             'std': 0.0044658511197943991}
        
        self.assertEqual(summary, expected_summary)


        # Drop the old collection; it will be recreated when inserting
        self.mediator.client[self.mediator.db_name].drop_collection(testname)
        self.mediator.client[self.mediator.db_name]['coord_index'].remove({
            '_id': testname
        })
        self.mediator.client[self.mediator.db_name]['metadata'].remove({
            '_id': testname
        })


# class TestColors(unittest.TestCase):
#     '''Tests the colors module'''
#     
#     base_string = "['rgb(165,0,38)','rgb(215,48,39)','rgb(244,109,67)','rgb(253,174,97)','rgb(254,224,144)','rgb(255,255,191)','rgb(224,243,248)','rgb(171,217,233)','rgb(116,173,209)','rgb(69,117,180)','rgb(49,54,149)']"
#     base_array = [
#         'rgb(165,0,38)',
#         'rgb(215,48,39)',
#         'rgb(244,109,67)',
#         'rgb(253,174,97)',
#         'rgb(254,224,144)',
#         'rgb(255,255,191)',
#         'rgb(224,243,248)',
#         'rgb(171,217,233)',
#         'rgb(116,173,209)',
#         'rgb(69,117,180)',
#         'rgb(49,54,149)'
#     ]
#         
#     def test_diverging_color_scale(self):
#         '''Tests that DivergingColors scales can be set up correctly'''
#         scale = DivergingColors('test', base=self.base_string)
#         self.assertEqual(scale.base, self.base_array)
#         self.assertEqual(scale.rgb2hex(255, 255, 255), '#ffffff')
# 
#     def test_hex_color_conversion(self):
#         scale = DivergingColors('test', base=self.base_string)
#         self.assertEqual(scale.hex_colors(), [
#             '#a50026',
#             '#d73027',
#             '#f46d43',
#             '#fdae61',
#             '#fee090',
#             '#ffffbf',
#             '#e0f3f8',
#             '#abd9e9',
#             '#74add1',
#             '#4575b4',
#             '#313695'
#         ])
# 
#     def test_divering_styles(self):
#         scale = DivergingColors('test', base=self.base_string)
#         self.assertEqual([etree.tostring(i) for i in scale.kml_styles(alpha=0.5)], [
#             '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test+5"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7f2600a5</color></PolyStyle></Style>',
#             '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test+4"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7f2730d7</color></PolyStyle></Style>',
#             '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test+3"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7f436df4</color></PolyStyle></Style>',
#             '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test+2"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7f61aefd</color></PolyStyle></Style>',
#             '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test+1"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7f90e0fe</color></PolyStyle></Style>',
#             '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test+0"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7fbfffff</color></PolyStyle></Style>',
#             '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test-1"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7ff8f3e0</color></PolyStyle></Style>',
#             '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test-2"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7fe9d9ab</color></PolyStyle></Style>',
#             '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test-3"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7fd1ad74</color></PolyStyle></Style>',
#             '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test-4"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7fb47545</color></PolyStyle></Style>',
#             '<Style xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:atom="http://www.w3.org/2005/Atom" xmlns="http://www.opengis.net/kml/2.2" id="test-5"><LineStyle><width>0</width></LineStyle><PolyStyle><color>7f953631</color></PolyStyle></Style>'
#         ])


# class TestHDF5(unittest.TestCase):
#     '''Tests HDF5 fluency and conversion utilities'''
#     
#     path = '/usr/local/project/flux-python-api/fluxpy/tests/'
#     filename = 'temp.h5'
# 
#     def test_bulk_hdf5_to_csv(self):
#         '''Should bulk convert HDF5 files to CSV files'''
#         hdf_path = os.path.join(self.path, self.filename)
#         csv_path = os.path.join(self.path, self.filename.split('.')[0] + '.csv')
#         
#         # Delete file; create a new one
#         try:
#             os.remove(hdf_path)
#             
#         except OSError:
#             pass
#             
#         store = h5py.File(os.path.join(self.path, self.filename), 'a')
#         
#         # Populate the token HDF file
#         data = store.create_dataset('temp', np.array([10, 10]), dtype='i')
#         data[:,:] = np.arange(10)
#         store.close()
#         
#         bulk_hdf5_to_csv(self.path, 'temp', regex='^.*\.h5')
#         
#         with open(csv_path) as stream:
#             reader = csv.reader(stream)
#             for line in reader:
#                 # Skip header and skip the index (first item in each row)
#                 if reader.line_num != 1:
#                     self.assertEqual(line[1:], map(str, range(10)))
# 
#         # Clean up
#         os.remove(hdf_path)
#         os.remove(csv_path)

if __name__ == '__main__':
    unittest.main()
    
    
