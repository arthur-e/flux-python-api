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

import requests

def lint_geojson(path='http://localhost:8080/fluxvis/api/casa-gfed.geojson?time=2003-12-22T03:00:00'):
    endpoint = 'http://geojsonlint.com/validate'
    geojson = requests.get(path)
    the_request = requests.post(endpoint, data=geojson.content)

    print the_request.content


if __name__ == '__main__':
    if len(sys.argv) > 1:
        lint_geojson(sys.argv[1])

    else:
        lint_geojson()
