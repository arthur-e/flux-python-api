#!/usr/bin/python

import sys, getopt, copy
from pymongo import MongoClient
from fluxpy import *
#from fluxpy.mediators import *

usage = """
manage.py [COMMAND] [REQUIRED ARGUMENTS FOR COMMAND] [OPTIONAL ARGUMENTS FOR COMMAND]

Commands:

load                Loads data
remove              Removes data
list_collections    Lists collections
view_metadata       Shows various database diagnostics

------------------------------------------------------------------------
load

    Usage:
        manage.py load -p <inputfilepath> -m <model> -n <collection_name> [OPTIONAL ARGUMENTS]
        
    Required argument:
        -p, --path               Directory path of input file in Matlab (*.mat) or HDF5 (*.h5 or *.mat) format 
        -n, --collection_name    Collection name for the input file (MongoDB identifier)
        -m, --model              fluxpy/models.py model associated with the input dataset  
    
    Optional arguments:
        -c, --config_file        Specify location of json config file. By default, uses
                                 input file w/ .json extension.
    
    These optional args can be used to override specifications of the config file:
        -v, --var_name           The name of the variable in the hierarchical file
                                 that stores the data
        -t, --timestamp          An ISO 8601 timestamp for the first observation
        -T, --title              "Pretty" name, for displaying within visualization application
    
    
    In the following example, the program will look for a config file
    at ~/mydata/data_casa_gfed_3hrly.json and overwrite the timestamp and var_name
    specifications in that file with those provided as command line args:
    
        manage.py load -i ~/mydata/data_casa_gfed_3hrly.mat -t 2003-12-22T03:00:00 -n casa_gfed_2004

------------------------------------------------------------------------


"""

# map of valid options (and whether or not they are required) for each command
# -one current inelegancy: this set up assumes all boolean options are not required, which just happens to be the case (for now)
commands = {
        'load' : {
                  'path': True,
                  'model': True,
                  'collection_name': True,
                  'timestamp': False,
                  'var_name': False,
                  'config_file': False
        },
        'remove': {
                   'collection_name': True
        },
        
        'list_collections': {
                             'include_counts': False
        },
        'view_metadata': {'list_records': False,
                          'record_id': False,
                          'list_coords': False
        }
    }

# lists all possible options (for ALL commands) and their corresponding short flags
# colons (:) indicate that option must be followed by an argument
options = {
             'help': 'h',
             'path': 'p:',
             'timestamp': 't:',
             'var_name': 'v:',
             'collection_name': 'n:',
             'config_file': 'c:',
             'include_counts': 'z',
             'list_records': 'l',
             'record_id': 'i:',
             'list_coords': 'x:'
             }

def main(argv):
    command = argv[0]
    if command not in commands:
        if command not in ['-h', '--help']:
            print "'{0}' is not a valid command".format(command)
        print usage
        sys.exit(2)
    
    kwargs = copy.copy(commands[command])
    opt_pairs = [('--' + o[0], '-' + o[1].rstrip(':')) for o in options.items()]
    bool_opts = [o for o in options if ':' not in options[o]]
    
    try:
        opts, args = getopt.getopt(argv[1:],''.join(options.values()),[k + ('=' if ':' in options[k] else '') for k in options])
    except getopt.GetoptError, exc:
        print '\n' + exc.msg
        print "\nFor detailed usage info, use:\npython manage.py -h\n"
        #print usage
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print usage
            sys.exit()
        else:
            for item in opt_pairs:
                if opt in item:
                    kwarg = item[0].lstrip('--')
                    # set the value to that of the argument if its an opt that requires an arg...
                    # ...if not, set it as a 'True' flag 
                    val = True if kwarg in bool_opts else arg
                    kwargs[kwarg] = val
    
    for kwarg in kwargs:
        if kwargs[kwarg] == True and kwarg not in bool_opts:
            print "\nRequired argument for command '{0}' is missing: --{1}".format(command,kwarg)
            print "\nFor detailed usage info, use:\npython manage.py -h\n"
            sys.exit(2)
        if kwarg not in commands[command]:
            print ("\nFYI: An argument was provided that is invalid for the '{0}' command: {1}".format(command,kwarg) +
                   "\nCommand will run but argument will be ignored...")
    
    # call the requested function
    globals()['_' + command](**kwargs)


def _load(model,collection_name, *args, **kwargs):
    
    # remove the empty args from kwargs to prevent config_file from being overwritten with 'None's
    kwargs = {k: v for k, v in kwargs.items() if v}
    
    # load the data
    inst = getattr(models, kwargs['model'])(**kwargs)
    
    # TBD: modify this to call the appropriate mediator...
    mediator = Grid4DMediator().save(kwarg['collection_name'], inst)

def _remove(collection_name,**kwargs):
    db = _open_db_connection()

    if collection_name in db.collection_names():
        # if the specified collection exists, drop it as well as the corresponding entries in metadata and coord_indexes
        db[collection_name].drop()
        db['metadata'].remove({'_id': collection_name})
        db['coord_index'].remove({'_id': collection_name})
    else:
        print '\nThe specified collection ({0}) does not exist. Existing collections include:'.format(collection_name)
        _list_collections()

def _list_collections(include_counts=False,**kwargs):
    db = _open_db_connection()
    print
    for c in db.collection_names():
        if c not in RESERVED_COLLECTION_NAMES + ('system.indexes',):
            print c + (': %i' % db[c].count() if include_counts else '')
    print
    
def _view_metadata(**kwargs):
    print 'dont look at me!'
#     # List the metadata records (by "_id") 
#     met = db['metadata']
#     for m in met.find():
#         print m['_id']
#         
#     #  View the metadata record of a given collection (by "_id") 
#     print list(met.find({'_id': test_id}))
#     
#     #- List the coord_index records (by "_id")
#     coord_index_col = db['coord_index']
#     print list(coord_index_col.find({'_id': test_id}))

def _open_db_connection():
    client = MongoClient()
    return client[DB]

if __name__ == "__main__":
   main(sys.argv[1:])