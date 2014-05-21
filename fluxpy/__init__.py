import sys, site

############################
# Virtual environment setup
ALLDIRS = [
    '/usr/local/project/flux-python-api/',
    '/usr/local/pythonenv/fluxvis-env/lib/python2.7/site-packages/',
]

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

DB = 'fluxvis'
DEFAULT_PATH = '/ws4/idata/fluxvis/casa_gfed_inversion_results/'
ISO_8601 = '%Y-%m-%dT%H:%M:%S%z'
RESERVED_COLLECTION_NAMES = (
    'coord_index',
    'metadata',
    'summary_stats'
)
