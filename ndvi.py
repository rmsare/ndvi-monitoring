import os, sys
from shutil import rmtree
import rasterio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from skimage.io import imread
import json, requests, time, zipfile

from datetime import datetime, timedelta

from xml.dom import minidom

from requests.exceptions import ConnectionError

from settings import PL_AOIS, PL_API_KEY
from pl_utils import * 
from s3utils import *
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
    #mask = np.where(np.logical_and(band_nir == 0, band_red == 0))
    #ndvi[mask] = np.nan

    return ndvi

def calculate_ndvi_timeseries(shape_file, images_dir):
    dates = []
    mean = []
    sd = []

    for f in os.listdir(images_dir):
        for temp in os.listdir(images_dir + f):
            if 'AnalyticMS_clip.tif' in temp:
                tiff_file = temp 
            if 'metadata' in temp:
                metadata_file = temp 

        image = load_image(images_dir + f + '/' + tiff_file, images_dir + f + '/' + metadata_file)
        if quality_check(image):
            dates.append(datetime.strptime(tiff_file[0:15], "%Y%m%d_%H%M%S"))
            fn = clip_tiff_by_shapefile(images_dir + f + '/' + tiff_file, shape_file)
            ndvi = calculate_ndvi(fn, images_dir + f + '/' + metadata_file)
            mean.append(np.nanmean(ndvi))
            sd.append(np.nanstd(ndvi))
            os.remove(fn)
        else:
            print(tiff_file + " failed quality check!")

    data = pd.DataFrame(data={'m' : mean, 'sd' : sd}, index=dates)
    pd.to_pickle(data, images_dir + '../timeseries.pk')

    return data

def update_ndvi_timeseries(data, results_dir):
    if os.path.exists(results_dir + 'timeseries.pk'):
        old_data = pd.read_pickle(results_dir + 'timeseries.pk')
        data = old_data.append(data)
        data = data.drop_duplicates()
        data.to_pickle(results_dir + 'timeseries.pk')
    else:
        data.to_pickle(results_dir + 'timeseries.pk')

def download_and_plot_scene(feature, results_dir):
    if not os.path.exists(results_dir):
        os.mkdir(results_dir)
        os.mkdir(results_dir + 'npy/')
        os.mkdir(results_dir + 'img/')
        os.mkdir(results_dir + 'data/')
        os.mkdir(results_dir + 'ts/')

    scene_id = feature['id']
    if scene_id not in os.listdir(results_dir + 'data/'):
        date_string = feature['properties']['acquired'] 
        print("Processing image acquired on " + date_string + " ({:d}/{:d})".format(i+1, n_scenes))
        assets_url = feature['_links']['assets']
        res = session.get(assets_url)
        assets = res.json()
        
        scene = assets['analytic']
        #print("Clipping scene to area of interest...")
        clip_url = clip_asset(scene_id, aoi_polygon)
        if clip_url:
            #print("Downloading clipped scene data...")
            scene_path = download_clip(clip_url, scene_id, results_dir)

            files = sorted(os.listdir(scene_path))
            scene_filename = os.path.join(scene_path, files[1])
            metadata_filename = os.path.join(scene_path, files[2])
            
            #print("Saving image of scene...")
            image = load_image(scene_filename, metadata_filename)
            plot_image(image, scene_id) 

            #print("Calculating NDVI...")
            ndvi = calculate_ndvi(scene_filename, metadata_filename)
            plot_ndvi(ndvi, scene_id, results_dir) 
            
            np.save(results_dir + 'npy/ndvi_' + scene_id + '.npy', ndvi)
            np.save(results_dir + 'npy/img_' + scene_id + '.npy', image)

def plot_image(image, label_string):
    fig = plt.figure()
    ax = fig.add_subplot(111)

    ax.imshow(image)
    ax.axis('off')
    ax.set_title(label_string, fontsize=12)
    
    filename = results_dir + 'img/img_' + label_string + '.png'
    plt.savefig(filename, dpi=200, bbox_inches='tight', pad_inches=0.5)
    plt.close()
    #save_file_to_s3(filename, filename)

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
    
    filename = results_dir + 'img/ndvi_' + label_string + '.png'
    plt.savefig(filename, dpi=200, bbox_inches='tight', pad_inches=0.5)
    plt.close()
    #save_file_to_s3(filename, filename)

def plot_ndvi_timeseries(data, label_string, results_dir):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    
    plt.errorbar(data.index, data.m, 2*data.sd, linestyle='None', color='r', marker='s', capsize=2)
    ax.grid('on', linestyle=':')
    ax.set_title(label_string, fontsize=14)
    ax.set_ylabel('NDVI', fontsize=12)
    
    filename = results_dir + 'ts/ndvi_ts_' + label_string + '.png'
    fig.set_size_inches(11, 8.5)
    plt.savefig(filename, dpi=200, bbox_inches='tight', pad_inches=0.5)
    plt.close()
    #save_file_to_s3(filename, filename)

def quality_check(img, thresh=0.25):
    # XXX: really crude quality check (for incomplete images with lots of blank space...)
    npixels = np.prod(img.shape[0:2])
    nblanks = len(np.where(img == 0.0)[0]) / 3.
    if nblanks / npixels > thresh:
        return False
    else:
        return True

def save_ndvi_tiff(filename, metadata_filename):
    ndvi = calculate_ndvi(filename, metadata_filename)

    with rasterio.open(filename) as data:
        ndvi_raster = rasterio.open('ndvi.tif', 'w', driver=data.driver, height=data.height, width=data.width, count=1, dtype=rasterio.float64, crs=data.crs, transform=data.transform)
        ndvi_raster.write(ndvi, 1)
        ndvi_raster.close()

def save_all_tiffs(images_dir):
    for f in os.listdir(images_dir):
        for temp in os.listdir(images_dir + f):
            if 'clip.tif' in temp and 'udm' not in temp:
                tiff_file = temp 
            if 'metadata' in temp:
                metadata_file = temp 
        os.chdir(images_dir + f)
        save_ndvi_tiff(tiff_file, metadata_file)
        os.chdir('..')

if __name__ == "__main__":
    URL = "https://api.planet.com/data/v1"
    search_url = "{}/quick-search".format(URL)
    session = requests.Session()
    session.auth = (PL_API_KEY, "")

    aois = PL_AOIS  
    time_window_length = 365 / 2 # days

    for aoi in aois:
        print("Processing images for site: " + aoi.upper())
        base_dir = '/media/rmsare/GALLIUMOS/ndvi/'
        results_dir = base_dir + aoi + '/'
        aoi_filename = 'polygons/' + aoi + '.json'
        shape_filename = 'shp/' + aoi + '.shp'
        with open(aoi_filename, 'r') as file_obj:
            aoi_polygon = json.load(file_obj) 

        datetime_max = datetime.utcnow() 
        datetime_min = datetime.utcnow() - timedelta(days=time_window_length)
        
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

        print("Downloading assets...")
        for i, feature in enumerate(geojson['features']):
            try:
                download_and_plot_scene(feature, results_dir)
            except (ConnectionError, KeyError, ValueError) as e:
                failed.append(feature)
                print("Error: " + str(e))
                print("Failed to process image acquired on " + feature['properties']['acquired'])

        print("Calculating average NDVI timeseries...")
        data = calculate_ndvi_timeseries(shape_filename, results_dir + 'data/')
        plot_ndvi_timeseries(data, aoi.upper(), results_dir)
        update_ndvi_timeseries(data, results_dir)
        
