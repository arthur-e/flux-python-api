import unittest, os, csv, datetime
import pandas as pd
import numpy as np
import h5py
from fluxpy.legacy.transform import bulk_hdf5_to_csv
from fluxpy.mediators import Grid3DMediator, Unstructured3DMediator
from fluxpy.models import KrigedXCO2Matrix, XCO2Matrix

class TestXCO2Data(unittest.TestCase):
    '''Tests for proper handling of XCO2 retrievals'''

    mediator = Unstructured3DMediator()
    path = '/usr/local/project/flux-python-api/fluxpy/tests/'

    def test_model_instance(self):
        '''Should properly instantiate a model instance'''
        xco2 = XCO2Matrix(os.path.join(self.path, 'xco2.mat'),
            timestamp='2009-06-15')

        self.assertEqual(xco2.params.get('var_name'), 'XCO2')
        self.assertEqual(xco2.params.get('interval'), 86400000)
        self.assertEqual(xco2.params.get('range'), None)
        self.assertEqual(xco2.params.get('timestamp'), '2009-06-15')
        
    def test_model_save(self):
        '''Should create proper DataFrame from reading file data'''
        xco2 = XCO2Matrix(os.path.join(self.path, 'xco2.mat'),
            timestamp='2009-06-15')

        df1 = xco2.save()
        self.assertEqual(df1.shape, (1311, 7))

        # Should allow overrides in the save() method
        df2 = xco2.save(timestamp='2010-01-01')
        self.assertEqual(xco2.params.get('timestamp'), '2010-01-01')
            
    def test_save_to_db(self):
        '''Should successfully save proper data representation to database'''
        xco2 = XCO2Matrix(os.path.join(self.path, 'xco2.mat'),
            timestamp='2009-06-15')

        # Drop the old collection; it will be recreated when inserting
        self.mediator.client[self.mediator.db_name].drop_collection('test')
        
        self.mediator.add(xco2)
        self.assertEqual(len(self.mediator.instances), 1)
        
        #TODO self.mediator.save_to_db('test')
        

class TestKrigedXCO2Data(unittest.TestCase):
    '''Tests for proper handling of kriged (gridded) XCO2 data'''

    mediator = Grid3DMediator()
    path = '/usr/local/project/flux-python-api/fluxpy/tests/'

    def test_model_instance(self):
        '''Should properly instantiate a model instance'''
        xco2 = KrigedXCO2Matrix(os.path.join(self.path, 'kriged_xco2.mat'),
            timestamp='2009-06-15')

        self.assertEqual(xco2.params.get('var_name'), 'krigedData')
        self.assertEqual(xco2.params.get('interval'), None)
        self.assertEqual(xco2.params.get('range'), 518400000)
        self.assertEqual(xco2.params.get('timestamp'), '2009-06-15')
        
    def test_model_save(self):
        '''Should create proper DataFrame from reading file data'''
        xco2 = KrigedXCO2Matrix(os.path.join(self.path, 'kriged_xco2.mat'),
            timestamp='2009-06-15')

        df1 = xco2.save()
        self.assertEqual(df1.shape, (14210, 9))

        # Should allow overrides in the save() method
        df2 = xco2.save(timestamp='2010-01-01')
        self.assertEqual(xco2.params.get('timestamp'), '2010-01-01')
            
    def test_save_to_db(self):
        '''Should successfully save proper data representation to database'''
        xco2 = KrigedXCO2Matrix(os.path.join(self.path, 'kriged_xco2.mat'),
            timestamp='2009-06-15')

        # Drop the old collection; it will be recreated when inserting
        self.mediator.client[self.mediator.db_name].drop_collection('test')
        
        self.mediator.add(xco2)
        self.assertEqual(len(self.mediator.instances), 1)
        
        #TODO self.mediator.save_to_db('test')


class TestHDF5(unittest.TestCase):
    '''Tests HDF5 fluency and conversion utilities'''
    
    path = '/usr/local/project/flux-python-api/fluxpy/tests/'
    filename = 'temp.h5'

    def test_bulk_hdf5_to_csv(self):
        '''Should bulk convert HDF5 files to CSV files'''
        hdf_path = os.path.join(self.path, self.filename)
        csv_path = os.path.join(self.path, self.filename.split('.')[0] + '.csv')
        
        # Delete file; create a new one
        try:
            os.remove(hdf_path)
            
        except OSError:
            pass
            
        store = h5py.File(os.path.join(self.path, self.filename), 'a')
        
        # Populate the token HDF file
        data = store.create_dataset('temp', np.array([10, 10]), dtype='i')
        data[:,:] = np.arange(10)
        store.close()
        
        bulk_hdf5_to_csv(self.path, 'temp', regex='^.*\.h5')
        
        with open(csv_path) as stream:
            reader = csv.reader(stream)
            for line in reader:
                # Skip header and skip the index (first item in each row)
                if reader.line_num != 1:
                    self.assertEqual(line[1:], map(str, range(10)))

        # Clean up
        os.remove(hdf_path)
        os.remove(csv_path)

if __name__ == '__main__':
    unittest.main()
    
    
