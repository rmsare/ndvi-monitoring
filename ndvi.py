import os, sys
import rasterio
import numpy as np
import matplotlib.pyplot as plt

from skimage.io import imread
import json, requests, time, zipfile

from datetime import datetime, timedelta

from xml.dom import minidom

from settings import PL_AOIS, PL_API_KEY
from pl_utils import * 
from utils import * 

np.seterr(divide='ignore', invalid='ignore')


def calculate_ndvi(filename, metadata_filename):
    with rasterio.open(filename) as src:
        band_red = src.read(3)

    with rasterio.open(filename) as src:
        band_nir = src.read(4)

    xmldoc = minidom.parse(metadata_filename)
    nodes = xmldoc.getElementsByTagName("ps:bandSpecificMetadata")

    coeff = {}
    for node in nodes:
        band_num = node.getElementsByTagName("ps:bandNumber")[0].firstChild.data
        if band_num in ['1', '2', '3', '4']:
            i = int(band_num)
            value = node.getElementsByTagName("ps:reflectanceCoefficient")[0].firstChild.data
            coeff[i] = float(value)

    band_red = band_red*coeff[3]
    band_nir = band_nir*coeff[4]

    ndvi = (band_nir.astype(float) - band_red.astype(float)) / (band_nir + band_red)

    return ndvi

def download_and_plot_scene(feature, results_dir):
    if not os.path.exists('/media/rmsare/GALLIUMOS/' + results_dir):
        os.mkdir('/media/rmsare/GALLIUMOS/' + results_dir)

    scene_id = feature['id']
    if 'img_' + scene_id + '.png' not in os.listdir('/media/rmsare/GALLIUMOS/' + results_dir):
        date_string = feature['properties']['acquired'] 
        print("Processing image acquired on " + date_string + " ({:d}/{:d})".format(i+1, n_scenes))
        assets_url = feature['_links']['assets']
        res = session.get(assets_url)
        assets = res.json()
        
        scene = assets['analytic']
        #print("Clipping scene to area of interest...")
        clip_url = clip_asset(scene_id, aoi_polygon)
        #print("Downloading clipped scene data...")
        scene_path = download_clip(clip_url, scene_id)

        files = sorted(os.listdir(scene_path))
        scene_filename = os.path.join(scene_path, files[1])
        metadata_filename = os.path.join(scene_path, files[2])
        
        #print("Saving image of scene...")
        image = load_image(scene_filename, metadata_filename)
        plot_image(image, scene_id) 

        #print("Calculating NDVI...")
        ndvi = calculate_ndvi(scene_filename, metadata_filename)
        plot_ndvi(ndvi, scene_id, results_dir) 
        
        np.save('/media/rmsare/GALLIUMOS/' + results_dir + 'ndvi_' + scene_id + '.npy', ndvi)
        np.save('/media/rmsare/GALLIUMOS/' + results_dir + 'img_' + scene_id + '.npy', image)


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

def plot_image(image, label_string):
    fig = plt.figure()
    ax = fig.add_subplot(111)

    ax.imshow(image)
    ax.axis('off')
    ax.set_title(label_string, fontsize=12)
    plt.savefig('/media/rmsare/GALLIUMOS/' + results_dir + 'img_' + label_string + '.png', dpi=200, bbox_inches='tight', pad_inches=0.5)
    plt.close()

def plot_ndvi(ndvi, label_string, results_dir):
    fig = plt.figure()
    ax = fig.add_subplot(111)

    vmin = -0.25
    vmax = 0.75
    mid = 0.1
    
    cmap = plt.cm.RdYlGn
    cax = ax.imshow(ndvi, cmap=cmap, clim=(vmin, vmax), norm=MidpointNormalize(midpoint=mid, vmin=vmin, vmax=vmax))
    ax.axis('off')
    ax.set_title(label_string, fontsize=12)
    cbar = fig.colorbar(cax, orientation='horizontal', shrink=0.5)
    cbar.set_label('NDVI')
    plt.savefig('/media/rmsare/GALLIUMOS/' + results_dir + 'ndvi_' + label_string + '.png', dpi=200, bbox_inches='tight', pad_inches=0.5)
    plt.close()


if __name__ == "__main__":
    URL = "https://api.planet.com/data/v1"
    search_url = "{}/quick-search".format(URL)
    session = requests.Session()
    session.auth = (PL_API_KEY, "")

    aois = PL_AOIS    

    for aoi in aois:
        print("Processing images for site: " + aoi.upper())
        results_dir = 'ndvi/' + aoi + '/'
        aoi_filename = 'polygons/' + aoi + '.json'
        with open(aoi_filename, 'r') as file_obj:
            aoi_polygon = json.load(file_obj) 

        datetime_max = datetime.utcnow() 
        datetime_min = datetime.utcnow() - timedelta(days=14)
        
        item_types = ["PSScene4Band"]
        and_filter = configure_filter(aoi_polygon, datetime_min, datetime_max)

        request = {
            "name" : aoi,
            "item_types" : item_types,
            "interval" : "year",
            "filter" : and_filter
        }
        
        res = session.post(search_url, json=request)
        geojson = res.json()
        n_scenes = len(geojson['features'])
        failed = []

        for i, feature in enumerate(geojson['features']):
            try:
                download_and_plot_scene(feature, results_dir)
            except (KeyError, ValueError) as e:
                failed.append(feature)
                print("Error: " + str(e))
                print("Failed to process image acquired on " + feature['properties']['acquired'])
        
