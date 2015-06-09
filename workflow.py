import os
import re
import sys
from fluxpy.models import *
from fluxpy.mediators import *
from fluxpy.utils import Suite

class StanfordXCO2(Suite):
    '''
    '''
    collection_name = 'test'
    file_matcher = re.compile(r'^XCO2_.*\.mat$')
    model = XCO2Matrix
    path = '/net/nas3/data/gis_lab/project/NASA_ACOS_Visualization/Data/xco2/'

    def __init__(self):
        self.mediator = Unstructured3DMediator()

    def main(self):
        paths = self.get_listing()[0:10]
        for path in paths:
            instance = self.model(path)
            self.mediator.save(self.collection_name, instance)


class StanfordKrigedXCO2(Suite):
    '''
    latitude    longitude   value   error   ...
    ...         ...         ...     ...

    octave-3.2.4:8> size(krigedData)
    ans =

        12414       9
    '''
    collection_name = 'test_r2_xco2'
    file_matcher = re.compile(r'^Kriged.*\.mat$')
    model = KrigedXCO2Matrix
    path = '/net/nas3/data/gis_lab/project/NASA_ACOS_Visualization/Data/xco2/'

    def __init__(self):
        self.mediator = Grid3DMediator()

    def main(self):
        '''Does a naive bulk insert (not optimized); supports alignment'''

        sys.stderr.write('\rDefining a common grid...\n')
        grid = self.define_common_grid()

        paths = self.get_listing()
        i = 1
        j = len(paths)
        for path in paths:
            instance = self.model(path)

            try:
                self.mediator.save(self.collection_name, instance, grid)

            except AssertionError:
                sys.stderr.write('\rSkipping error in %d of %d (%s)...' % (i, j, instance.timestamp))
                i += 1
                continue

            except DuplicateKeyError:
                sys.stderr.write('\rSkipping duplicate %d of %d (%s)...' % (i, j, instance.timestamp))
                i += 1
                continue

            sys.stderr.write('\rSaving %d of %d (%s)...' % (i, j, instance.timestamp))
            i += 1

        sys.stderr.write('\rFinished saving %d records...' % j)


if __name__ == '__main__':
    # To import the 2004 CASA GFED run...
    if sys.argv[1] == 'casa_gfed_2004':
        path = '/net/nas3/data/gis_lab/project/NASA_ACOS_Visualization/Data/from_Vineet/data_casa_gfed_3hrly.mat'
        if len(sys.argv) > 2:
            path = sys.argv[2]
        inst = SpatioTemporalMatrix(path, timestamp='2003-12-22T03:00:00',
            var_name='casa_gfed_2004', title='Surface Carbon Flux')
        mediator = Grid4DMediator().save('casa_gfed_2004', inst)

    # To import the sample uncertainty scenarios...
    elif sys.argv[1] == 'uncertainty':
        path = '/ws4/idata/fluxvis/casa_gfed_inversion_results/1.zerofull_casa_1pm_10twr/Month_Uncert1.mat'
        inst = CovarianceMatrix(path, timestamp='2008-01', span='1M')

    elif sys.argv[1] == 'xco2':
        path = '/net/nas3/data/gis_lab/project/NASA_ACOS_Visualization/Data/xco2/XCO2_20090615_20090620.mat'
        inst = XCO2Matrix(path)
        mediator = Unstructured3DMediator().save('test', inst)

    elif sys.argv[1] == 'kriged_xco2':
        path = '/net/nas3/data/gis_lab/project/NASA_ACOS_Visualization/Data/xco2/Kriged_20090615_20090620.mat'
        inst = KrigedXCO2Matrix(path)
        mediator = Grid3DMediator().save('test_r2_xco2', inst)
