#!/usr/bin/python

import sys, getopt, copy, pprint, traceback, ast
from pymongo import MongoClient
from fluxpy import models
from fluxpy import mediators
from fluxpy.mediators import *

usage_hdr = """
manage.py [COMMAND] [REQUIRED ARGS FOR COMMAND] [OPTIONAL ARGS FOR COMMAND]

Commands:

    load                Loads data
    
    remove              Removes data
    
    rename              Renames data collections
    
    db                  Database diagnostic tools, incl. listing all
                        collections, viewing collection metadata, etc.
"""

usage_load = """
manage.py load

    Usage:
        manage.py load -p <filepath> -m <model> -n <collection_name> [OPTIONAL ARGS]
        
    Required arguments:
    
        -p, --path               Directory path of input file in Matlab (*.mat)
                                 or HDF5 (*.h5 or *.mat) format 
                                 
        -n, --collection_name    Provide a unique name for the dataset by which
                                 it will be identified in the MongoDB
        
        -m, --model              fluxpy/models.py model associated with the
                                 input dataset  
    
    Optional arguments:
    
        -c, --config_file        Specify location of json config file. By
                                 default, seeks input file w/ .json extension.
    
        -o, --options            Use to override specifications in the config file.
                                 Syntax: -o "parameter1=value1;parameter2=value2;parameter3=value3"
                                 e.g.: -o "title=MyData;gridres={'units':'degrees,'x':1.0,'y':1.0}"
    
    Examples:
    
        python manage.py load -p ./data_casa_gfed.mat -m SpatioTemporalMatrix -n casa_gfed_2004
    
    In the following example, the program will look for a config file
    at ~/data_casa_gfed.json and overwrite the timestamp and var_name
    specifications in that file with those provided as command line args:
    
        python manage.py load -p ./data_casa_gfed.mat -m SpatioTemporalMatrix -n casa_gfed_2004 -o "timestamp=2003-12-22T03:00:00;var_name=casa_gfed_2004"
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

usage_rename = """
manage.py rename

    Usage:
        manage.py rename -n <collection_name> -r <new_name>
        
    Required arguments:
        -n, --collection_name    Collection name to be removed (MongoDB identifier)
        -r, --new_name           New name for the collection       
    
    Example:
        python manage.py rename -n casa_gfed_2004 -r casa_2004
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

usage_all = ('\n' + '-'*30).join([usage_hdr,usage_load,usage_remove,usage_rename,usage_db])

# map of valid options (and whether or not they are required) for each command
# -one current naivete: this setup assumes all boolean options are not required, which just happens to be the case (for now)
commands = {
        'load' : {'path': True,
                  'model': True,
                  'mediator': False,
                  'collection_name': True,
                  'options': False,
                  'config_file': False},
            
        'remove': {'collection_name': True},
        
        'rename': {'collection_name': True,
                   'new_name': True},
        
        'db': {'list_ids': False,
               'collection_name': False,
               'include_counts': False,
               'audit': False},
        }

# lists all possible options (for ALL commands) and their corresponding short flags
# colons (:) indicate that option must be followed by an argument
options = {'help': 'h',
           'path': 'p:',
           'mediator': 'd:',
           'model': 'm:',
           'collection_name': 'n:',
           'new_name': 'r:',
           'config_file': 'c:',
           'options': 'o:',
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


def _load(path, model, collection_name, mediator=None, **kwargs):
    """
    Uploads data to MongoDB using given model and mediator
    """
    
    # parse any config options into individual kwarg entries:
    if kwargs['options']:
        tmp = kwargs['options'].split(';')
        for o in tmp:
            tmp2 = o.split('=')
            if tmp2[0] in ['timestamp','title','var_name']: # evaluate strings as strings
                kwargs[tmp2[0]] = tmp2[1]
            else: # for dict/array values, evaluate string literally
                kwargs[tmp2[0]] = ast.literal_eval(tmp2[1])
    
    # load the data/instantiate the model
    inst = getattr(models, model)(path=path,
                                  collection_name=collection_name,
                                  **kwargs)
    
    # now use mediator to save to db
    default_mediators = {'SpatioTemporalMatrix': mediators.Grid4DMediator,
                         'XCO2Matrix': mediators.Unstructured3DMediator,
                         'KrigedXCO2Matrix': mediators.Grid3DMediator,
                         }
    
    if not mediator:
        mediator = default_mediators[model]
    mediator().save(collection_name, inst, verbose=True)
    
    sys.stderr.write('\nUpload complete!\n')

def _remove(collection_name):
    """
    Removes specified collection from database as well as its corresponding
    entries in metadata and coord_index tables.
    """
    db = _open_db_connection()

    if (collection_name in db.collection_names() or
        collection_name in _return_id_list(db,'metadata') or
        collection_name in _return_id_list(db,'coord_index') or
        '_geom_' + collection_name in db.collection_names()):
        
        db[collection_name].drop()
        db['metadata'].remove({'_id': collection_name})
        db['coord_index'].remove({'_id': collection_name})
        db['_geom_' + collection_name].drop()
        
        print '\nCollection ID "{0}" successfully removed from ' \
              'database!\n'.format(collection_name)
    else:
        print '\nCollection ID "{0}" does not exist. ' \
              'Existing collections include:'.format(collection_name)
        _db(list_ids='collections')

def _rename(collection_name,new_name):
    """
    Renames specified collection with the specified new name.
    """
    print '\nRenaming collection ID "{0}" to "{1}"...'.format(collection_name,new_name)
    
    db = _open_db_connection()
    db[collection_name].rename(new_name)
    
    # update the metadata and coord_index collections
    for col in ['metadata','coord_index']:
        # this is messy b/c '_id' field cannot be renamed w/in the database
        # ...further, inserting a copy with an altered name fails bc the _id's
        #    index cannot be changed
        # ...further, we don't want to remove the entry and THEN reindex in
        #    case something fails bc the data will not be able to be recovered
        # ...so, we have to first store a copy of the collection in the db as
        #    it exists before we do anything, then do the stuff.
        
        # first create a temporary backup of the collection in case something fails
        orig_name = col + '_orig'
        for x in db[col].find():
            db[orig_name].insert(x)
        
        # now attempt the rename
        try:
            document = db[col].find_one({'_id': collection_name})
            document['_id'] = new_name
            db[col].remove({'_id': collection_name})
            db[col].insert(document)

        except:
            print 'Rename FAILED; restoring "{0}" table'.format(col)
            db[col].drop()
            for x in db[orig_name].find():
                db[col].insert(x)
            traceback.print_exc()
        
        # and finally remove the temporary backup collection
        db[orig_name].drop()
        
    print 'Complete.\n'

def _db(list_ids=None,collection_name=None,audit=None,include_counts=False):
    """
    Sub-parser for the db command- checks valid args and calls
    appropriate functions
    """
    print
    list_valid_values = ['collections','metadata','coord_index','c','m','i']
    if list_ids:
        if list_ids in list_valid_values:
            if list_ids not in ['collections','c',''] and include_counts:
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
            if c not in (RESERVED_COLLECTION_NAMES + ('system.indexes',)) and ('_geom' not in c):
                print c + (' (%i' % db[c].count() + ' records)' if include_counts else '')
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
    existing_collections = [c for c in db.collection_names() if (c not in
                            RESERVED_COLLECTION_NAMES + ('system.indexes',)) and ('_geom' not in c)]
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
                
    print '\nDatabase audit complete.\n',
    if all_good: print 'No inconsistencies found!'
    

def _open_db_connection():
    """
    Opens Mongo client connection with the local database
    """
    client = MongoClient()
    return client[DB]

if __name__ == "__main__":
   main(sys.argv[1:])