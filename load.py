#!/usr/bin/python

import sys, getopt
from fluxpy.models import *
from fluxpy.mediators import *

usage = """
load.py -i <inputfile> -t <ISO 8601 timestamp> -n <variable name>

Example:
load.py -i ~/mydata/data_casa_gfed_3hrly.mat -t '2003-12-22T03:00:00' -n 'casa_gfed_2004'
"""

def main(argv):
    inputfile = ''
    timestamp = ''
    var_name = ''

    try:
        opts, args = getopt.getopt(argv,'hi:t:n:',['ifile=','timestamp=','name='])
    except getopt.GetoptError:
        print usage
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print usage
            sys.exit()
        elif opt in ('-i', '--ifile'):
            inputfile = arg
        elif opt in ('-t', '--timestamp'):
            timestamp = arg
        elif opt in ('-n', '--name'):
            var_name = arg
        
    #print 'Input file is "', inputfile
    #print 'Timestamp is "', timestamp
    #print 'var_name is ', var_name
   
    inst = SpatioTemporalMatrix(inputfile, timestamp=timestamp,var_name=var_name)
    mediator = Grid4DMediator().save(var_name, inst)

if __name__ == "__main__":
   main(sys.argv[1:])