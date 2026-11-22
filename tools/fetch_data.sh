#!/bin/sh
# Downloads the source data the level builder needs (about 150 MB). Run inside tools/.
set -e
NE=https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson
for f in ne_50m_admin_0_countries ne_50m_lakes ne_50m_rivers_lake_centerlines ne_50m_populated_places_simple \
         ne_50m_geography_regions_polys ne_50m_glaciated_areas ne_10m_admin_1_states_provinces \
         ne_10m_rivers_lake_centerlines ne_10m_lakes ne_10m_roads ne_10m_populated_places_simple \
         ne_10m_geography_regions_polys ne_10m_glaciated_areas ne_10m_urban_areas; do
  [ -f $f.geojson ] || curl -sL -o $f.geojson $NE/$f.geojson
done
[ -f topo.nc ] || curl -sL -o topo.nc https://github.com/fatiando-data/earth-topography-10arcmin/releases/download/v1/earth-topography-10arcmin.nc
python3 - <<'PY'
import netCDF4 as nc, numpy as np
d=nc.Dataset('topo.nc')
np.savez('topo.npz',t=np.array(d.variables['topography'][:],dtype=np.int16),lon=np.array(d.variables['longitude'][:]),lat=np.array(d.variables['latitude'][:]))
PY
echo done
