import os
import re
import sys
from pymongo.errors import DuplicateKeyError
from fluxpy.models import *
from fluxpy.mediators import *

class Suite(object):
    def __init__(self):
        pass    

    def get_listing(self, path=None, regex=None):
        path = path or self.path
        regex = regex or self.file_matcher
        paths = []
        for filename in os.listdir(path):
            if regex.match(filename) is not None:
                paths.append(os.path.join(path, filename))

        return paths


class StanfordSuite(Suite):
    def __init__(self):
        pass


class StanfordKrigedXCO2(StanfordSuite):
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
        paths = self.get_listing()
        i = 1
        j = len(paths)
        for path in paths:
            instance = self.model(path)

            try:
                self.mediator.save(self.collection_name, instance)

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
        inst = SpatioTemporalMatrix(path, timestamp='2003-12-22T03:00:00',
            var_name='casa_gfed_2004', title='Surface Carbon Flux')
        mediator = Grid4DMediator().save('casa_gfed_2004', inst)

    # To import the sample uncertainty scenarios...
    elif sys.argv[1] == 'uncertainty':
        path = '/ws4/idata/fluxvis/casa_gfed_inversion_results/1.zerofull_casa_1pm_10twr/Month_Uncert1.mat'
        inst = CovarianceMatrix(path, timestamp='2008-01', span='1M')

    elif sys.argv[1] == 'kriged_xco2':
        path = '/net/nas3/data/gis_lab/project/NASA_ACOS_Visualization/Data/xco2/Kriged_20090615_20090620.mat'
        inst = KrigedXCO2Matrix(path)
        mediator = Grid3DMediator().save('test_r2_xco2', inst)


