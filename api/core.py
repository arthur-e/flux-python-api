import sys, site

############################
# Virtual environment setup
ALLDIRS = ['/usr/local/pythonenv/fluxvis-env/lib/python2.7/site-packages/']

# Remember original sys.path
prev_sys_path = list(sys.path)

# Add each new site-packages directory
for directory in ALLDIRS:
    site.addsitedir(directory)

# Reorder sys.path so new directories are at the front
new_sys_path = []
for item in list(sys.path): 
    if item not in prev_sys_path: 
        new_sys_path.append(item) 
        sys.path.remove(item) 
sys.path[:0] = new_sys_path

# End setup
############

import datetime
from pymongo import MongoClient
from bottle import route, run, abort, request, response, get

DB = 'fluxvis'
COLLECTION = 'casa_gfed_3hrly'
CORS_HOST = 'http://localhost'

client = MongoClient() # Defaults: MongoClient('localhost', 27017)

@route('/casa-gfed/stats.json', method='GET')
def casa_gfed_stats():
    response.set_header('Access-Control-Allow-Origin', CORS_HOST)
    
    query = client[DB]['summary_stats'].find_one({
        'about_collection': COLLECTION
    }, fields={ # Exclude these fields
        'about_collection': False,
        'tags': False,
        '_id': False
    })

    for each in ['timestamp_start', 'timestamp_end']:
        query[each] = datetime.datetime.strftime(query[each], '%Y-%m-%dT%H:%M:%S')

    return query;


@get('/casa-gfed.json')
def casa_gfed_by_date():
    # Use "2003-12-22T03:00:00" for testing
    datestring = request.query.time
    formatstring = request.query.timeformat or '%Y-%m-%dT%H:%M:%S'

    if len(datestring) == 0:
        abort(500, 'Bad Request')

    # Consume and reproduce the datestring in the desired format
    dateobj = datetime.datetime.strptime(datestring, formatstring)

    response.set_header('Access-Control-Allow-Origin', CORS_HOST)

    # Note: We exclude the timestamp field here because we don't know how to
    #   serialize it to JSON
    query = client[DB][COLLECTION].find_one({
        'timestamp': dateobj
    }, fields=['features'])

    query['timestamp'] = datestring

    return query


@get('/casa-gfed.geojson')
def casa_gfed_by_date_geojson():
    # Use "2003-12-22T03:00:00" for testing
    datestring = request.query.time
    formatstring = request.query.timeformat or '%Y-%m-%dT%H:%M:%S'
    collection_type = request.query.collection or 'features' # Or 'geometries'

    if len(datestring) == 0:
        abort(500, 'Bad Request')

    # Consume and reproduce the datestring in the desired format
    dateobj = datetime.datetime.strptime(datestring, formatstring)

    query = client[DB][COLLECTION].find_one({'timestamp': dateobj})

    if collection_type == 'features':
        response_body = {
            'type': 'FeatureCollection',
            'features': [{
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': each['coordinates'],
                },
                'properties': {
                    'flux': each['flux']
                }
            } for each in query['features']]
        }

    elif collection_type == 'geometries':
        response_body = {
            'type': 'GeometryCollection',
            'geometries': [{
                'type': 'Point',
                'coordinates': each['coordinates'],
                'properties': {
                    'flux': each['flux']
                }
            } for each in query['features']]
        }

    response.set_header('Access-Control-Allow-Origin', CORS_HOST)
    return response_body


