import sys
import csv
import datetime
import os
import unittest
import pandas as pd
import numpy as np
import h5py
from fluxpy.models import KrigedXCO2Matrix, SpatioTemporalMatrix, XCO2Matrix
from fluxpy.mediators import Grid3DMediator, Grid4DMediator, Unstructured3DMediator

class TestSpatioTemporalMatrixes(unittest.TestCase):
    '''Tests for proper handling of inverted CO2 surface fluxes (e.g. CASA GFED output)'''

    mediator = Grid4DMediator()
    path = '/usr/local/project/flux-python-api/fluxpy/tests/'

    @classmethod
    def setUpClass(cls):
        # Clean up: Remove the test collections and references    
        mediator = Grid3DMediator()
        for collection_name in ('test3',): 
            mediator.client[mediator.db_name].drop_collection(collection_name)
            mediator.client[mediator.db_name]['coord_index'].remove({
                '_id': collection_name
            })
            mediator.client[mediator.db_name]['metadata'].remove({
                '_id': collection_name
            })

    @classmethod
    def tearDownClass(cls):
        # Clean up: Remove the test collections and references    
        mediator = Grid3DMediator()
        for collection_name in ('test3',): 
            mediator.client[mediator.db_name].drop_collection(collection_name)
            mediator.client[mediator.db_name]['coord_index'].remove({
                '_id': collection_name
            })
            mediator.client[mediator.db_name]['metadata'].remove({
                '_id': collection_name
            })

    def test_model_instance(self):
        '''Should properly instantiate an SpatioTemporalMatrix model instance'''
        flux = SpatioTemporalMatrix(os.path.join(self.path, 'casagfed2004.mat'),
            timestamp='2004-06-30T00:00:00', var_name='test', span=10800)

        self.assertEqual(flux.var_name, 'test')
        self.assertEqual(flux.steps, [10800])
        self.assertEqual(flux.timestamp, '2004-06-30T00:00:00')

    def test_model_var_name_inference(self):
        '''Should infer the var_name in an SpatioTemporalMatrix model instance'''
        flux = SpatioTemporalMatrix(os.path.join(self.path, 'casagfed2004.mat'))

        self.assertEqual(flux.var_name, 'casa_gfed_2004')

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

        self.mediator.save('test3', flux)
        query = self.mediator.client[self.mediator.db_name]['test3'].find({
            '_id': datetime.datetime(2004, 6, 30, 0, 0, 0),
        })
        self.assertEqual(len(query[0]['values']), 10)
        self.assertEqual(query[0]['values'][0], 0.08028)

        # Test the mediator's summarize() method
        summary = self.mediator.summarize('test3')
        expected_summary = {
            'values': {
                'max': 0.26999000000000001,
                'mean': 0.14931662499999998,
                'median': 0.1513225,
                'min': 0.0,
                'std': 0.0047259989513704238
            }
        }
        
        self.assertEqual(summary, expected_summary)

    
class TestXCO2Data(unittest.TestCase):
    '''Tests for proper handling of XCO2 retrievals'''

    mediator = Unstructured3DMediator()
    path = '/usr/local/project/flux-python-api/fluxpy/tests/'

    @classmethod
    def setUpClass(cls):
        # Clean up: Remove the test collections and references    
        mediator = Grid3DMediator()
        for collection_name in ('test',): 
            mediator.client[mediator.db_name].drop_collection(collection_name)
            mediator.client[mediator.db_name]['coord_index'].remove({
                '_id': collection_name
            })
            mediator.client[mediator.db_name]['metadata'].remove({
                '_id': collection_name
            })

    @classmethod
    def tearDownClass(cls):
        # Clean up: Remove the test collections and references    
        mediator = Grid3DMediator()
        for collection_name in ('test',): 
            mediator.client[mediator.db_name].drop_collection(collection_name)
            mediator.client[mediator.db_name]['coord_index'].remove({
                '_id': collection_name
            })
            mediator.client[mediator.db_name]['metadata'].remove({
                '_id': collection_name
            })

    def test_model_instance(self):
        '''Should properly instantiate a model instance'''
        xco2 = XCO2Matrix(os.path.join(self.path, 'xco2.mat'),
            timestamp='2009-06-15')

        self.assertEqual(xco2.var_name, 'XCO2')
        self.assertEqual(xco2.steps, [86400])
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


class TestKrigedXCO2Data(unittest.TestCase):
    '''Tests for proper handling of kriged (gridded) XCO2 data'''

    mediator = Grid3DMediator()
    path = '/usr/local/project/flux-python-api/fluxpy/tests/'

    @classmethod
    def setUpClass(cls):
        # Clean up: Remove the test collections and references    
        mediator = Grid3DMediator()
        for collection_name in ('test2',): 
            mediator.client[mediator.db_name].drop_collection(collection_name)
            mediator.client[mediator.db_name]['coord_index'].remove({
                '_id': collection_name
            })
            mediator.client[mediator.db_name]['metadata'].remove({
                '_id': collection_name
            })

    @classmethod
    def tearDownClass(cls):
        # Clean up: Remove the test collections and references    
        mediator = Grid3DMediator()
        for collection_name in ('test2',): 
            mediator.client[mediator.db_name].drop_collection(collection_name)
            mediator.client[mediator.db_name]['coord_index'].remove({
                '_id': collection_name
            })
            mediator.client[mediator.db_name]['metadata'].remove({
                '_id': collection_name
            })

    def test_model_instance(self):
        '''Should properly instantiate a model instance'''
        xco2 = KrigedXCO2Matrix(os.path.join(self.path, 'kriged_xco2.mat'),
            timestamp='2009-06-15')

        self.assertEqual(xco2.var_name, 'krigedData')
        self.assertEqual(xco2.spans, [518400])
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

        # Drop the old collection; it will be recreated when inserting
        self.mediator.client[self.mediator.db_name].drop_collection('test2')
        self.mediator.client[self.mediator.db_name]['coord_index'].remove({
            '_id': 'test2'
        })
        self.mediator.client[self.mediator.db_name]['metadata'].remove({
            '_id': 'test2'
        })

        self.mediator.save('test2', xco2)
        query = self.mediator.client[self.mediator.db_name]['test2'].find({
            '_id': datetime.datetime(2009, 6, 15, 0, 0, 0),
        })
        self.assertEqual(query[0]['_span'], 518400)
        self.assertEqual(len(query[0]['values']), 14210)

        # Test the mediator's summarize() method
        summary = self.mediator.summarize('test2')
        self.maxDiff = None # Show the full diff
        expected_summary = {
            'errors': {
                'max': 1.6173,
                'mean': 0.81096864180154282,
                'median': 0.8117,
                'min': 0.20619999999999999,
                'std': 0.28630911583420193
            },
            'values': {
                'max': 391.35000000000002,
                'mean': 386.29349542575756,
                'median': 386.37,
                'min': 381.68000000000001,
                'std': 1.5496076951756685
            }
        }
        
        self.assertEqual(summary, expected_summary)


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


