import os
import numpy as np
import matplotlib.colors as colors
from scipy.io import loadmat
import json
from xml.dom import minidom
import rasterio
import subprocess

from osgeo import ogr, osr
from geojson import Polygon

from datetime import datetime

def clip_tiff_by_shapefile(tiff_file, metadata_file, shapefile):
    out_file = tiff_file[:-4] + '_clip.tif'
    
    # XXX: hacky, eventually port to native gdal
    command = ["gdalwarp", "-dstnodata", "nan", "-cutline", shapefile, tiff_file, out_file]
    try:
        output = subprocess.check_output(command)
    except:
        print("Clipping " + tiff_file + " failed!")

    return out_file

def convert_mat_to_json(filename, outfilename, source_epsg=32611, target_epsg=4326):
    mat = loadmat(filename)
    X = mat['xb'][0]
    Y = mat['yb'][0]

    ring = ogr.Geometry(ogr.wkbLinearRing)
    for x, y in zip(X, Y):
        ring.AddPoint(x, y)

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

    aoi = json.loads(polygon.ExportToJson())

    with open(outfilename, 'w') as f:
        json.dump(aoi, f)

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

def load_image(filename, metadata_filename):
    with rasterio.open(filename) as src:
        band_blue = src.read(1)

    with rasterio.open(filename) as src:
        band_green = src.read(2)
    
    with rasterio.open(filename) as src:
        band_red = src.read(3)

    xmldoc = minidom.parse(metadata_filename)
    nodes = xmldoc.getElementsByTagName("ps:bandSpecificMetadata")

    coeff = {}
    for node in nodes:
        band_num = node.getElementsByTagName("ps:bandNumber")[0].firstChild.data
        if band_num in ['1', '2', '3', '4']:
            i = int(band_num)
            value = node.getElementsByTagName("ps:reflectanceCoefficient")[0].firstChild.data
            coeff[i] = float(value)

    band_blue = band_blue*coeff[1]
    band_green = band_green*coeff[2]
    band_red = band_red*coeff[3]

    return np.stack([band_red, band_blue, band_green], axis=-1)

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

