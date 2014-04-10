from fluxpy.models import *
from fluxpy.mediators import *

if __name__ == '__main__':

#    # To import the 2004 CASA GFED run...
    path = '/net/nas3/data/gis_lab/project/NASA_ACOS_Visualization/Data/from_Vineet/data_casa_gfed_3hrly.mat'
    inst = SpatioTemporalMatrix(path, timestamp='2003-12-22T03:00:00',
        var_name='casa_gfed_2004')
    mediator = Grid4DMediator().save('casa_gfed_2004', inst)

    # To import the sample uncertainty scenarios...
#    path = '/ws4/idata/fluxvis/casa_gfed_inversion_results/1.zerofull_casa_1pm_10twr/Month_Uncert1.mat'
#    inst = CovarianceMatrix(path, timestamp='2008-01', span='1M')
