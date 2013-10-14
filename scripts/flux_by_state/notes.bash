# Get the Natural Earth dataset (1:50m cultural without large lakes)
wget http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/50m/cultural/ne_50m_admin_1_states_provinces_lakes.zip
unzip ne_50m_admin_1_states_provinces_lakes.zip

# Extract just American states, except Hawaii and D.C. which won't have model cells intesecting their geometry
ogr2ogr -f "ESRI Shapefile" -where "sr_adm0_a3 IN ('USA')" us_states.shp ne_50m_admin_1_states_provinces_lakes.shp

# Remove the old stuff
rm ne_50m_admin_1_states_provinces_lakes.*

# Convert to GeoJSON
ogr2ogr -f "GeoJSON" -where "postal NOT IN ('HI','DC')" us_states.json us_states.shp

# Simplify to 10^-6 (0.000001) steradians, which is acceptable for this display
# See: http://en.wikipedia.org/wiki/Steradian#SI_multiples
topojson --id-property su_a3 -s 0.000001 -p name=NAME -o us_states.topo.json us_states.json

# Make a GeoJSON copy with reduced precision
geojson --precision 3 us_states.topo.json
