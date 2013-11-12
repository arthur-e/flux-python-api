'''
Functions from the workflow for reproducing the carbon flux by U.S. State dataset.
'''
import sys, datetime, json, csv
import pandas as pd
import numpy as np
from shapely import wkt
from shapely.geometry import shape
from pymongo import MongoClient

client = MongoClient() # Defaults: MongoClient('localhost', 27017)
DB = 'fluxvis'
COLLECTION = 'casa_gfed_3hrly'
INDEX_COLLECTION = 'coord_index'
FLUX_PRECISION = 2
STATES_GEOMETRY = '/usr/local/project/flux-python-api/scripts/flux_by_state/us_states.json'
STATE_AREAS = { # Square kilometers of land area
    'AL': 131426,
    'AK': 1481347,
    'AZ': 294312,
    'AR': 134856,
    'CA': 403882,
    'CO': 268627,
    'CT': 12548,
    'DE': 5060,
    'FL': 139670,
    'GA': 149976,
    'HI': 16635,
    'ID': 214314,
    'IL': 143961,
    'IN': 92895,
    'IA': 144701,
    'KS': 211900,
    'KY': 102896,
    'LA': 112825,
    'ME': 79931,
    'MD': 25314,
    'MA': 20306,
    'MI': 147121,
    'MN': 206189,
    'MS': 121488,
    'MO': 178414,
    'MT': 376979,
    'NE': 199099,
    'NV': 284448,
    'NH': 23227,
    'NJ': 19211,
    'NM': 314309,
    'NY': 122283,
    'NC': 126161,
    'ND': 178647,
    'OH': 106056,
    'OK': 177847,
    'OR': 248631,
    'PA': 116074,
    'RI': 2706,
    'SC': 77983,
    'SD': 196540,
    'TN': 106752,
    'TX': 678051,
    'UT': 212751,
    'VT': 23956,
    'VA': 102548,
    'WA': 172348,
    'WV': 62361,
    'WI': 140663,
    'WY': 251489,
}

def get_state_areas(path=STATES_GEOMETRY):
    '''
    Calculates the area (in arbitrary units) of each U.S. State.
    '''
    state_assoc = {}

    with open(path, 'rb') as stream:
        states = json.loads(stream.read())

    for state in states['features']:
        # Get the MultiPolygon geometry for the state
        geom = shape(state['geometry'])

        state_assoc[state['properties']['postal']] = geom.area

    return state_assoc


def get_state_cells(path=STATES_GEOMETRY):
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
    Calculates the net (or something else) 3-hourly flux per U.S. State. The
    flux estimates are normalized by the area. Net, total positive, and total
    negative flux estimates are "flux per unit area" while mean flux estimates
    area "mean flux per unit area."
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
        area = STATE_AREAS[state] / (1000.0 * 1000.0) # Convert sq. kilometers to sq. megameters
        fluxes_in_time = []

        for window in cursor:
            # Get those fluxes which are indicated by their cell indices
            fluxes = [window['values'][i] for i in indices]

            if aggr == 'net' or aggr == 'mean':
                flux = reduce(lambda x, y: x + y, fluxes) / area

                if aggr == 'mean':
                    flux = flux / len(fluxes)

            elif aggr == 'positive':
                flux = reduce(lambda x, y: x + y if x > 0 else 0, fluxes) / area

            elif aggr == 'negative':
                flux = reduce(lambda x, y: x + y if x < 0 else 0, fluxes) / area

            fluxes_in_time.append(round(flux, FLUX_PRECISION))

        fluxes_by_state[state] = fluxes_in_time
        cursor.rewind()

    return fluxes_by_state


def flux_by_state(start='2003-12-22T03:00:00', end='2004-12-22T03:00:00', aggr='net', interval='D'):
    '''
    Calculates the net (or something else) daily flux per U.S. State. The
    flux estimates are normalized by the area. Net, total positive, and total
    negative flux estimates are "flux per unit area" while mean flux estimates
    area "mean flux per unit area."
    '''
    states = get_state_cells()
    fluxes_by_state = dict.fromkeys(states, [])
    start_time = datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%S')

    cursor = client[DB][COLLECTION].find({
        '_id': {
            '$gte': start_time,
            '$lte': datetime.datetime.strptime(end, '%Y-%m-%dT%H:%M:%S')
        }
    }).sort([('_id', 1)])

    # Create an index of 3-hour intervals
    date_index = pd.date_range(start_time.strftime('%Y%m%d%H%M%S'),
        periods=cursor.count(), freq='3H', tz='UTC')

    # Guard against, say, net monthly aggregation when some months only have partial coverage
    if aggr not in ('mean', 'median', 'min', 'max'):
        assert interval not in ('M',), 'Net or total aggregation over the specified time scale, which has only partial coverage at some time steps, is not recommended'

    # This is the aggregator in time; functions that are array-valued
    if aggr in ('mean', 'median', 'min', 'max'):
        aggregator = aggr

    elif aggr == 'net':
        aggregator = sum

    elif aggr == 'positive':
        aggregator = lambda x: sum(map(lambda y: y if y > 0 else 0, x))

    elif aggr == 'negative':
        aggregator = lambda x: sum(map(lambda y: y if y < 0 else 0, x))

    # Iterate through the states and their intersected model cells
    for state, indices in states.items():
        area = STATE_AREAS[state] / (1000.0 * 1000.0) # Convert sq. kilometers to sq. megameters
        fluxes_in_time = []

        for window in cursor:
            # Get those fluxes which are indicated by their cell indices
            fluxes = [window['values'][i] for i in indices]

            # This is the aggregator in space; functions that are number-valued
            if aggr == 'net' or aggr == 'mean':
                flux = reduce(lambda x, y: x + y, fluxes) / area

                if aggr == 'mean':
                    flux = flux / len(fluxes)

            elif aggr == 'median':
                flux = fluxes.sort()[math.floor(len(fluxes) / 2)]

            elif aggr == 'positive':
                flux = reduce(lambda x, y: x + y if x > 0 else 0, fluxes) / area

            elif aggr == 'negative':
                flux = reduce(lambda x, y: x + y if x < 0 else 0, fluxes) / area

            elif aggr == 'max':
                flux = max(fluxes)

            elif aggr == 'min':
                flux = min(fluxes)

            fluxes_in_time.append(round(flux, FLUX_PRECISION))

        # Create a time series of just these spatially-aggregated fluxes
        series = pd.Series(fluxes_in_time, index=date_index)

        # Resample the time series, by default to the day (interval='D')
        fluxes_by_state[state] = series.resample(interval,
            how=aggregator).round(FLUX_PRECISION).tolist()

        cursor.rewind()

    return fluxes_by_state


if __name__ == '__main__':
    aggr = 'net'
    interval = 'M'
    if len(sys.argv) > 2:
        aggr = sys.argv[2]

    if len(sys.argv) > 3:
        interval = sys.argv[3]

    mapping = flux_by_state(**{
        'aggr': aggr,
        'interval': interval,
        'start': '2004-01-01T00:00:00'
    })

    header = ['id']
    header.extend(['t%d' % i for i in range(len(mapping['MI']))])

    with open(sys.argv[1], 'wb') as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        for key, value in mapping.items():
            row = [key]
            row.extend(value)
            writer.writerow(row)


