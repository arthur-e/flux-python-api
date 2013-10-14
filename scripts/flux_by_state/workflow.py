'''
Functions from the workflow for reproducing the carbon flux by U.S. State dataset.
'''
import datetime, json, csv, ipdb
from shapely import wkt
from shapely.geometry import shape
from pymongo import MongoClient

client = MongoClient() # Defaults: MongoClient('localhost', 27017)
DB = 'fluxvis'
COLLECTION = 'casa_gfed_3hrly'
INDEX_COLLECTION = 'coord_index'
FLUX_PRECISION = 2

def get_state_cells(path='/usr/local/project/flux-python-api/scripts/flux_by_state/us_states.json'):
    '''
    Returns an associative array (dictionary) of U.S. State : Model cells mappings;
    a list of the cells, by their indices, that intersect each state's geometry.
    '''
    # This associative array will associate states with the many model cells
    #   their geometry intersects
    state_assoc = {}

    # Create a number of Point objects
    cells = client[DB][INDEX_COLLECTION].find_one()['i']
    cells = [wkt.loads('POINT(%s %s)' % (c[0], c[1])) for c in cells]

    with open(path, 'rb') as stream:
        states = json.loads(stream.read())

    for state in states['features']:
        # Create a new list to hold features
        state_assoc.setdefault(state['properties']['postal'], [])

        # Get the MultiPolygon geometry for the state
        geom = shape(state['geometry'])

        i = 0
        while i < len(cells):
            if geom.intersects(cells[i]):
                state_assoc[state['properties']['postal']].append(i)

            i += 1

    return state_assoc


def hourly_flux_by_state(start='2003-12-22T03:00:00', end='2004-12-22T03:00:00', aggr='net'):
    '''
    Calculates the net (or something else) 3-hourly flux per U.S. State.
    '''
    states = get_state_cells()
    fluxes_by_state = dict.fromkeys(states, [])

    cursor = client[DB][COLLECTION].find({
        '$and': [
            {'_id': {'$gte': datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%S')}},
            {'_id': {'$lte': datetime.datetime.strptime(end, '%Y-%m-%dT%H:%M:%S')}},
        ]
    })

    # Iterate through the states and their intersected model cells
    for state, indices in states.items():
        fluxes_in_time = []
        for window in cursor:
            # Get those fluxes which are indicated by their cell indices
            fluxes = [window['values'][i] for i in indices]

            if aggr == 'net' or aggr == 'mean':
                flux = reduce(lambda x, y: x + y, fluxes)

                if aggr == 'mean':
                    flux = flux / len(fluxes)

            elif aggr == 'positive':
                flux = reduce(lambda x, y: x + y if x > 0 else 0, fluxes)

            elif aggr == 'negative':
                flux = reduce(lambda x, y: x + y if x < 0 else 0, fluxes)

            fluxes_in_time.append(round(flux, FLUX_PRECISION))

        fluxes_by_state[state] = fluxes_in_time
        cursor.rewind()

    return fluxes_by_state        


if __name__ == '__main__':
    get_state_cells()
