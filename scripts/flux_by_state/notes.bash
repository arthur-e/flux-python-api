# Get the Natural Earth dataset
wget http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_admin_1_states_provinces.zip
unzip ne_10m_admin_1_states_provinces.zip

# Extract just American states
ogr2ogr -f "ESRI Shapefile" -where "adm0_a3 IN ('USA')" us_states.shp ne_10m_admin_1_states_provinces.shp

# Convert to GeoJSON
ogr2ogr -f "GeoJSON" us_states.json us_states.shp

# Simplify to 10^-5 (0.00001) steradians, which is acceptable for this display
# See: http://en.wikipedia.org/wiki/Steradian
topojson --id-property su_a3 -s 0.00001 -p name=NAME -o us_states.topo.json us_states.json

# Make a GeoJSON copy with reduced precision
geojson --precision 3 us_states.topo.json
