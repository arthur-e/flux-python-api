import ast
import sys
import csv
import datetime
import os
import unittest
import subprocess
import pandas as pd
import numpy as np
import h5py
from pymongo import MongoClient
from fluxpy import DB
from fluxpy.models import KrigedXCO2Matrix, SpatioTemporalMatrix, XCO2Matrix
from fluxpy.mediators import Grid3DMediator, Grid4DMediator, Unstructured3DMediator, DB

class TestManage(unittest.TestCase):
    '''Tests manage.py command line functionality'''
    
    db = MongoClient()[DB]
    
    def load_test_data(self):
        # remove any stale sample data and reload
        cmd = 'python ../../manage.py remove -n casa_gfed_load_test'
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        cmd = '''python ../../manage.py load -p casagfed2004.mat -n casa_gfed_load_test -m SpatioTemporalMatrix'''
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        
    def test_load_command(self):
        '''
        Tests that command line manage.py load utility properly loads data and 
        transfers config_file override options to database
        '''
    
        # remove any stale test data
        cmd = 'python ../../manage.py remove -n casa_gfed_load_test'
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
    
        # load some sample data, check for expected standard output information
        cmd = '''python ../../manage.py load -p casagfed2004.mat -n casa_gfed_load_test -m SpatioTemporalMatrix -o "title=MyData;timestamp=2010-10-10T00:00:00"'''
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        self.assertGreater(len(result.split('Upload complete!')),1) 
        
        # now check metadata to see if it loaded correctly
        document = self.db['metadata'].find({'_id': 'casa_gfed_load_test'})
        
        self.assertGreater(document.count(),0)
        self.assertEqual(document[0]['title'], 'MyData')
        self.assertEqual(document[0]['dates'][0], '2010-10-10T00:00:00')
        
        # now remove
        cmd = 'python ../../manage.py remove -n casa_gfed_load_test'
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)

    def test_db_tools(self):
        '''
        commands to test:
      
        # test all iterations of db command:
        python manage.py db -l collections
        python manage.py db -l collections -x
        python manage.py db -l metadata
        python manage.py db -l coord_index
        
        python manage.py db -n casa_gfed_2004
        
        python manage.py db -a
        '''
        
        self.load_test_data()
        
        # check that the test dataset is listed w/ the appropriate number of records
        cmd = 'python ../../manage.py db -l collections -x'
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        self.assertGreater(len(result.split('casa_gfed_load_test (8 records)')),1)
        
        # check that the metadata table lists the test dataset
        cmd = 'python ../../manage.py db -l metadata'
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        self.assertGreater(len(result.split('casa_gfed_load_test')),1)
        
        # check that the coord_index table lists the test dataset
        cmd = 'python ../../manage.py db -l coord_index'
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        self.assertGreater(len(result.split('casa_gfed_load_test')),1)

        # check that the metadata is returned as expected
        cmd = 'python ../../manage.py db -n casa_gfed_load_test'                   
        result = ast.literal_eval(subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).replace('\n',''))
        meta = self.db['metadata'].find({'_id': 'casa_gfed_load_test'})[0]
        self.assertDictEqual(result, meta)
        
        # check that audit utility returns... anything
        cmd = 'python ../../manage.py db -a'
        result = subprocess.check_output(cmd, shell=True)
        self.assertGreater(len(result.split('audit complete')),1)
        
        # now remove
        cmd = 'python ../../manage.py remove -n casa_gfed_load_test'
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        
    def test_remove_command(self):
        '''
        Finally, test the 'remove' utility, ensuring collection has been purged from metadata as well
        '''
        
        self.load_test_data()
        
        # check that command results indicate successful removal
        cmd = 'python ../../manage.py remove -n casa_gfed_load_test'
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        self.assertGreater(len(result.split('casa_gfed_load_test" successfully removed')),1)
        
        # check that data was in fact removed
        self.assertEqual('casa_gfed_load_test' in self.db.collection_names(), False)
        
        for cname in ['metadata', 'coord_index']:
            tmp = [t['_id'] for t in list(self.db[cname].find())]
            self.assertEqual('casa_gfed_load_test' in tmp, False)
        
    def test_rename_command(self):
        '''Test the rename utility'''

        self.load_test_data()
        
        # check that command results indicate successful renaming
        cmd = 'python ../../manage.py rename -n casa_gfed_load_test -r fancypants'
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        self.assertGreater(len(result.split('casa_gfed_load_test" to "fancypants"')),1)
        
        # check that database includes the new name but not the old name
        self.assertEqual('casa_gfed_load_test' in self.db.collection_names(), False)
        self.assertEqual('fancypants' in self.db.collection_names(), True)
        
        for cname in ['metadata', 'coord_index']:
            tmp = [t['_id'] for t in list(self.db[cname].find())]
            self.assertEqual('casa_gfed_load_test' in tmp, False)
            self.assertEqual('fancypants' in tmp, True)
        
        # now clean up by removing
        cmd = 'python ../../manage.py remove -n fancypants'
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        
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
            timestamp='2004-06-30T00:00:00', var_name='casa_gfed_2004',span=10800)
         
        df = flux.describe()
        self.assertEqual(df['bbox'], (-166.5, 10.5, -50.5, 69.5))
        self.assertEqual(df['bboxmd5'], '6f3e33c145010bc74c5ccd3ba772f504')
        self.assertEqual(df['dates'], ['2004-06-30T00:00:00', '2004-06-30T21:00:00'])
        self.assertEqual(df['gridded'], True)
        self.assertEqual(df['grid'], {'units': 'degrees', 'x': 1.0, 'y': 1.0})
        self.assertEqual(df['steps'], [10800])
     
    def test_model_extract(self):
        '''Should extract a DataFrame in an SpatioTemporalMatrix model instance'''
        flux = SpatioTemporalMatrix(os.path.join(self.path, 'casagfed2004.mat'),
            timestamp='2004-06-30T00:00:00', var_name='casa_gfed_2004')
 
        df = flux.extract()
        self.assertEqual(df.shape, (2635, 8))
        self.assertEqual(str(df.columns[1]), '2004-06-30 03:00:00')
        self.assertEqual(df.index.values[1], (-165.5, 61.5))
 
    def test_save_to_db(self):
        '''Should successfully save proper data representation to database'''
        flux = SpatioTemporalMatrix(os.path.join(self.path, 'casagfed2004.mat'),
            timestamp='2004-06-30T00:00:00', var_name='casa_gfed_2004')
 
        self.mediator.save('test3', flux)
        query = self.mediator.client[self.mediator.db_name]['test3'].find({
            '_id': datetime.datetime(2004, 6, 30, 0, 0, 0),
        })
        self.assertEqual(len(query[0]['values']), 2635)
        self.assertEqual(query[0]['values'][0], 0.08)
 
        # Test the mediator's summarize() method
        summary = self.mediator.summarize('test3')
 
        self.assertEqual(summary.keys(), ['values'])
        #print summary['values'].keys()
        self.assertEqual(summary['values'].keys(), [
            'std', 'max', 'min', 'median', 'mean'
        ])
 
     
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
        self.assertEqual(query[0]['properties']['value'], 386.79)
 
 
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
 
        self.assertEqual(summary.keys(), ['errors', 'values'])
        self.assertEqual(summary['values'].keys(), [
            'std', 'max', 'min', 'median', 'mean'
        ])


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


