import numpy as np
import matplotlib.colors as colors
from scipy.io import loadmat
import json

from osgeo import ogr, osr
from geojson import Polygon

from datetime import datetime

def convert_mat_to_aoi_bbox(filename, buf=1000, source_epsg=32611, target_epsg=4326):
    mat = loadmat(filename)
    x = mat['xb']
    y = mat['yb']

    xmax = x.max() + buf
    xmin = x.min() - buf
    ymax = y.max() + buf
    ymin = y.min() - buf
    # XXX: OGR/Planet API expects ring of points defining polygon
    bbox = [(xmax, ymax), (xmax, ymin), (xmin, ymin), (xmin, ymax), (xmax, ymax)]
    
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for p in bbox:
        ring.AddPoint(p[0], p[1])

    polygon = ogr.Geometry(ogr.wkbPolygon) 
    polygon.AddGeometry(ring)

    source = osr.SpatialReference()
    source.ImportFromEPSG(source_epsg)
    target = osr.SpatialReference()
    target.ImportFromEPSG(target_epsg)
    transform = osr.CoordinateTransformation(source, target)
    polygon.Transform(transform)

    for i in range(0, polygon.GetGeometryCount()):
        point = polygon.GetGeometryRef(i)
        point.FlattenTo2D()

    aoi = polygon.ExportToJson()

    return aoi

def print_json(data):
    print(json.dumps(data, indent=2))

def rfc3339(date_obj):
    # XXX: Assumes date_obj is UTC +0
    # TODO : TZ conversion
    rfc_fmt = '%Y-%m-%dT%H:%M:%SZ'
    return datetime.strftime(date_obj, rfc_fmt)


class MidpointNormalize(colors.Normalize):
    """
    Taken from Planet tutorial by Dana Bauer and others
    https://github.com/planetlabs/notebooks/blob/master/jupyter-notebooks/ndvi/ndvi_planetscope.ipynb

    Original Credit: Joe Kington, http://chris35wills.github.io/matplotlib_diverging_colorbar/
    """
    def __init__(self, vmin=None, vmax=None, midpoint=None, clip=False):
        self.midpoint = midpoint
        colors.Normalize.__init__(self, vmin, vmax, clip)

    def __call__(self, value, clip=None):
        # I'm ignoring masked values and all kinds of edge cases to make a
        # simple example...
        x, y = [self.vmin, self.midpoint, self.vmax], [0, 0.5, 1]
        return np.ma.masked_array(np.interp(value, x, y), np.isnan(value))

