from fluxpy.models import *
from fluxpy.mediators import *

if __name__ == '__main__':
    path = '/gis_lab/project/NASA_ACOS_Visualization/Data/from_Vineet/data_casa_gfed_3hrly.mat'
    inst = SpatioTemporalMatrix(path, timestamp='2003-12-22T03:00:00',
        var_name='casa_gfed_2004')
    mediator = Grid4DMediator().save('casa_gfed_2004', inst)
