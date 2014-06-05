#!/usr/bin/python

import sys, getopt, copy, pprint
from pymongo import MongoClient
from fluxpy import models
from fluxpy.mediators import *


usage_hdr = """
manage.py [COMMAND] [REQUIRED ARGS FOR COMMAND] [OPTIONAL ARGUsS FOR COMMAND]

Commands:

    load                Loads data
    
    remove              Removes data
    
    db                  Database diagnostic tools, incl. listing all
                        collections, viewing collection metadata, etc.
"""

usage_load = """
manage.py load

    Usage:
        manage.py load -p <filepath> -m <model> -n <collection_name> [OPTIONAL ARGS]
        
    Required argument:
    
        -p, --path               Directory path of input file in Matlab (*.mat)
                                 or HDF5 (*.h5 or *.mat) format 
                                 
        -n, --collection_name    Collection name for the input file (MongoDB
                                 identifier)
        
        -m, --model              fluxpy/models.py model associated with the
                                 input dataset  
    
    Optional arguments:
    
        -c, --config_file        Specify location of json config file. By
                                 default, seeks input file w/ .json extension.
    
    These optional args can be used to override specifications of the config file:
    
        -v, --var_name           The name of the variable in the hierarchical
                                 file that stores the data
                                 
        -t, --timestamp          An ISO 8601 timestamp for the first observation
        
        -T, --title              "Pretty" name, for displaying within
                                 visualization application
    
    Examples:
    
        python manage.py load -p ~/data_casa_gfed.mat -m SpatioTemporalMatrix -n casa_gfed_2004
    
    In the following example, the program will look for a config file
    at ~/data_casa_gfed.json and overwrite the timestamp and var_name
    specifications in that file with those provided as command line args:
    
        python manage.py load -p ~/data_casa_gfed.mat -m SpatioTemporalMatrix -n casa_gfed_2004 -t 2003-12-22T03:00:00 -v casa_gfed_2004
"""

usage_remove = """
manage.py remove

    Usage:
        manage.py remove -n <collection_name>
        
    Required argument:
        -n, --collection_name    Collection name to be removed (MongoDB identifier)
        
    
    Example:
        python manage.py remove -n casa_gfed_2004
"""

usage_db = """
manage.py db

    Usage:
        manage.py db [OPTIONAL ARGUMENTS]
    
    Requires one of the following flags:
    
        -l, --list_ids           Lists collection names in the database.
        
             Optional args with -l flag:
                 collections :   lists collections
                 metadata:       lists the collections w/ metadata entries
                 coord_index:    lists the collections w/ coord_index entries
                                     
        -n, --collection_name    Collection name for which to shows metadata
        
        -a, --audit              No argument required. Performs audit of the
                                 database, reporting any collections that are
                                 missing corresponding metadata/coord_index
                                 entries and any stale metadata/coord_index
                                 entries without corresponding collections
    
    Optional argument:
    
        -x, --include_counts     Include count of records within each listed
                                 collection. Valid only with a corresponding
                                 "-l collections" flag; ignored otherwise
    
    Examples:
        
        List all collections and their number of records:
            python manage.py db -l collections -x
        
        List all the collections with metadata entries:
            python manage.py db -l metadata
        
        Show metadata for the collection with id "casa_gfed_2004":
            python manage.py db -n casa_gfed_2004 
            
        Audit the database:
            python manage.py db -a
"""

usage_all = ('\n' + '-'*30).join([usage_hdr,usage_load,usage_remove,usage_db])

# map of valid options (and whether or not they are required) for each command
# -one current naivete: this setup assumes all boolean options are not required, which just happens to be the case (for now)
commands = {
        'load' : {'path': True,
                  'model': True,
                  'collection_name': True,
                  'timestamp': False,
                  'var_name': False,
                  'config_file': False},
            
        'remove': {'collection_name': True},
        
        'db': {'list_ids': False,
               'collection_name': False,
               'include_counts': False,
               'audit': False},
        }

# lists all possible options (for ALL commands) and their corresponding short flags
# colons (:) indicate that option must be followed by an argument
options = {'help': 'h',
           'path': 'p:',
           'timestamp': 't:',
           'model': 'm:',
           'var_name': 'v:',
           'collection_name': 'n:',
           'config_file': 'c:',
           'include_counts': 'x',
           'list_ids': 'l:',
           'audit': 'a'}

# useful variables built from the options dict
opt_pairs = [('--' + o[0], '-' + o[1].rstrip(':')) for o in options.items()]
bool_opts = [o for o in options if ':' not in options[o]]
optstring_short = ''.join(options.values())
optstring_long = [k + ('=' if ':' in options[k] else '') for k in options]

def main(argv):
    """
    Parses command line options/arguments and reroutes to the appropriate
    function.
    """
    command = argv[0]
    if command not in commands:
        if command not in ['-h', '--help']:
            print "\n'{0}' is not a valid command".format(command)
            print usage_hdr
            print '\nFor detailed usage info on a specific command, use:\n' \
                  'manage.py [COMMAND] -h\n\nFor full help, use:\nmanage.py -h'
        else:
            print usage_all
        sys.exit(2)
    
    kwargs = copy.copy(commands[command])
    
    try:
        opts, args = getopt.getopt(argv[1:],optstring_short,optstring_long)
    except getopt.GetoptError, exc:
        print '\n' + exc.msg
        print "\nFor detailed usage info for the '{0}' command, use:\n" \
              "python manage.py {0} -h\n" \
              "\nFor detailed usage info for manage.py in general, use:\n" \
              "python manage.py -h\n".format(command)
        sys.exit(2)
        
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print globals()['usage_' + command]
            sys.exit()
        else:
            for item in opt_pairs:
                if opt in item:
                    kwarg = item[0].lstrip('--')
                    # set value to the arg if its an opt that requires an arg
                    # ...if not, set it as a 'True' flag
                    val = True if kwarg in bool_opts else arg
                    kwargs[kwarg] = val
    
    for kwarg in kwargs:
        if kwargs[kwarg] == True and kwarg not in bool_opts:
            print "\nRequired argument for command '{0}' is missing: --{1}" \
                  "\nFor detailed usage info, use:" \
                  "\npython manage.py -h\n".format(command,kwarg)
            sys.exit(2)
        if kwarg not in commands[command]:
            print "\nFYI: An options was provided that is invalid for " \
                  "the '{0}' command: {1}\nCommand will run but options " \
                  "will be ignored...".format(command,kwarg)
    
    # call the requested function
    globals()['_' + command](**kwargs)


def _load(path, model, collection_name, **kwargs):
    """
    Uploads data to MongoDB using given model
    """
    # remove the empty args from kwargs to prevent config_file from being
    # overwritten with 'None's
    kwargs = {k: v for k, v in kwargs.items() if v}
    
    # load the data
    inst = getattr(models, model)(path=path,
                                  collection_name=collection_name,
                                  **kwargs)
    
    # TBD: modify this to call the appropriate mediator...
    mediator = Grid4DMediator().save(collection_name, inst, verbose=True)

    sys.stderr.write('\nUpload complete!\n')

def _remove(collection_name):
    """
    Removes specified collection from database as well as its corresponding
    entries in metadata and coord_index tables.
    """
    db = _open_db_connection()

    if (collection_name in db.collection_names() or
        collection_name in _return_id_list(db,'metadata') or
        collection_name in _return_id_list(db,'coord_index')):
        db[collection_name].drop()
        db['metadata'].remove({'_id': collection_name})
        db['coord_index'].remove({'_id': collection_name})
        
        print '\nCollection ID "{0}" successfully removed from ' \
              'database!\n'.format(collection_name)
    else:
        print '\nCollection ID "{0}" does not exist. ' \
              'Existing collections include:'.format(collection_name)
        _db(list_ids='collections')

def _db(list_ids=None,collection_name=None,audit=None,include_counts=False):
    """
    Sub-parser for the db command- checks valid args and calls
    appropriate functions
    """
    print
    list_valid_values = ['collections','metadata','coord_index']
    if list_ids:
        if list_ids in list_valid_values:
            if list_ids not in ['collections',''] and include_counts:
                print 'Option -x (for including record counts) is not valid ' \
                      'for the {0} argument, ignoring.'.format(list_ids)
            _list(list_ids=list_ids,include_counts=include_counts)
        else:
            print 'Invalid argument for [-l | --list]: {0}' \
                  '\nValid values include:'.format(list_ids)
            print list_valid_values
            sys.exit(2)
    
    if collection_name:
        _show_metadata(collection_name=collection_name)
    
    if audit:
        _audit()
    print
    
def _list(list_ids='collections',include_counts=False):
    """
    Database diagnostic tool for listing collection IDs
    """
    db = _open_db_connection()

    if list_ids in ['collections','']:
        for c in db.collection_names():
            if c not in RESERVED_COLLECTION_NAMES + ('system.indexes',):
                print c + (': %i' % db[c].count() if include_counts else '')
    else:
        for id in _return_id_list(db,list_ids):
            print id

def _return_id_list(db,collection_name):
    """
    Returns list of '_id' entries for the collection name provided
    """
    return [t['_id'] for t in list(db[collection_name].find())]


def _show_metadata(collection_name=None):
    """
    Database diagnostic tool for showing metadata for a specified
    collection ID
    """
    db = _open_db_connection()
    
    # View the metadata record of a given collection (by "_id")
    document = db['metadata'].find({'_id': collection_name})
    if document.count() > 0:
        pprint.pprint ((db['metadata'].find({'_id': collection_name}))[0])
    else:
        print 'Metadata for collection ID "{0}" not found.' \
              '\nTo view a list of collection IDs having metadata, use:' \
              '\nmanage.py db -l metadata'.format(collection_name)

def _audit():
    """
    Database diagnostic tool for auditing the database. Tests for
    synchronicity between collections and the collection ID entries for
    the metadata and coord_index tables.
    """
    
    db = _open_db_connection()
    existing_collections = [c for c in db.collection_names() if c not in
                            RESERVED_COLLECTION_NAMES + ('system.indexes',)]
    all_good = True
    
    for x in ['metadata','coord_index']:
        m_entries = [m['_id'] for m in db[x].find()]
    
        for c in existing_collections:
            if c not in m_entries:
                print 'INCONSISTENCY FOUND: missing {0} entry for collection ID "{1}"'.format(x,c)                    
                all_good = False
        
        for m in m_entries:
            if m not in existing_collections:
                print 'INCONSISTENCY FOUND: stale entry for collection ID "{0}" in {1}'.format(m,x)
                all_good = False
                
    print '\nDatabase auditing complete.\n',
    if all_good: print 'No inconsistencies found!'
    

def _open_db_connection():
    """
    Opens Mongo client connection with the local database
    """
    client = MongoClient()
    return client[DB]

if __name__ == "__main__":
   main(sys.argv[1:])