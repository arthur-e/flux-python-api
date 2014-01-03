import unittest, os, csv
import pandas as pd
import numpy as np
import h5py
from fluxpy.transform import bulk_hdf5_to_csv

class TestHDF5(unittest.TestCase):
    '''Tests HDF5 fluency and conversion utilities.'''
    
    path = '/usr/local/project/flux-python-api/fluxpy/tests/'
    filename = 'temp.h5'

    def test_bulk_hdf5_to_csv(self):
        '''
        Tests the bulk conversion of HDF files to CSV files.
        '''
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
