#!/usr/bin/python

import sys, getopt
from fluxpy.models import *
from fluxpy.mediators import *

usage = """
Usage:
    load.py -i <inputfile> [OPTIONAL ARGUMENTS]
    
Required argument:
    -i, --ifile          Input file in Matlab (*.mat) or HDF5 (*.h5 or *.mat) format 

Optional arguments:
    -c, --config_file    Specify location of json config file. By default, uses
                         input file w/ .json extension.

These optional args can be used to override specifications of the config file:
    -n, --var_name       The name of the variable in the hierarchical file
                         that stores the data
    -t, --timestamp      An ISO 8601 timestamp for the first observation


In the following example, the program will look for a config file
at ~/mydata/data_casa_gfed_3hrly.json and overwrite the timestamp and var_name
specifications in that file with those provided as command line args:

    load.py -i ~/mydata/data_casa_gfed_3hrly.mat -t 2003-12-22T03:00:00 -n casa_gfed_2004

"""

def main(argv):
    kwargs ={
        'path': '',
        'timestamp': None,
        'var_name': None,
        'config_file': None
        }

    try:
        opts, args = getopt.getopt(argv,'hi:t:n:c:',['help','ifile=','timestamp=','var_name=','config_file='])
    except getopt.GetoptError:
        print usage
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print usage
            sys.exit()
        elif opt in ('-i', '--ifile'):
            kwargs['path'] = arg
        elif opt in ('-t', '--timestamp'):
            kwargs['timestamp'] = arg
        elif opt in ('-n', '--var_name'):
            kwargs['var_name'] = arg
        elif opt in ('-c', '--config_file'):
            print 'ooo'
            kwargs['config_file'] = arg

    # remove the empty args from kwargs
    kwargs = {k: v for k, v in kwargs.items() if v}
    
    # and load the data
    inst = SpatioTemporalMatrix(**kwargs)
    mediator = Grid4DMediator().save(inst.var_name, inst)

if __name__ == "__main__":
   main(sys.argv[1:])