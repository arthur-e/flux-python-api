import sys, site, os

sys.path = ['/usr/local/project/flux-python-api/api/'] + sys.path
os.chdir(os.path.dirname(__file__))

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

import bottle, core

bottle.debug(True)

# Do NOT use bottle.run() with mod_wsgi
application = bottle.default_app()
