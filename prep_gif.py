import os
import numpy as np
import rasterio
import subprocess

import matplotlib.colors as colors
import matplotlib.pyplot as plt

from datetime import datetime
from shutil import copyfile
from xml.dom import minidom

from ndvi import *
from utils import *

def plot_ndvi(filename):
    with rasterio.open(filename) as src:

        ndvi = src.read(1)

    fig = plt.figure()
    ax = fig.add_subplot(111)

    vmin = -0.25
    vmax = 0.75
    mid = 0.1

    cmap = plt.cm.RdYlGn
    cax = ax.imshow(ndvi, cmap=cmap, clim=(vmin, vmax), norm=MidpointNormalize(midpoint=mid, vmin=vmin, vmax=vmax))
    ax.axis('off')
    plt.xlim(315, 580)
    plt.ylim(295, 635)
    ax.invert_yaxis()
    
    label_string = datetime.strptime(filename[5:20], '%Y%m%d_%H%M%S').strftime('%m/%d/%Y %H:%M')
    ax.set_title(label_string, fontsize=18)
    cbar = fig.colorbar(cax, orientation='horizontal', shrink=0.5)
    cbar.set_label('NDVI', fontsize=14)

    plt.savefig(filename[:-4] + '.png', dpi=200, bbox_inches='tight', pad_inches=0.1)
    plt.close()

def save_ndvi_tiff(filename, metadata_filename):
    ndvi = calculate_ndvi(filename, metadata_filename)

    with rasterio.open(filename) as data:
        ndvi_raster = rasterio.open('ndvi.tif', 'w', driver=data.driver, height=data.height, width=data.width, count=1, dtype=rasterio.float64, crs=data.crs, transform=data.transform)
        ndvi_raster.write(ndvi, 1)
        ndvi_raster.close()

def move_files_to_gif(aoi):
    os.chdir(aoi)
    if 'gif' not in os.listdir('.'):
        os.mkdir('gif')
    os.chdir('data/')
    files = os.listdir('.')
    for f in files: 
        if 'ndvi_clip.tif' not in os.listdir(f):
            os.chdir(f)
            for g in os.listdir('.'):
                if 'AnalyticMS_clip.tif' in g:
                    img_file = g
                if 'metadata' in g:
                    metadata_file = g
            save_ndvi_tiff(img_file, metadata_file)

            tiff_file = 'ndvi.tif'
            shapefile = 'shp/' + aoi + '.shp'
            clip_tiff_by_shapefile(tiff_file, shapefile)
            os.chdir('..')

        timestamp = f[0:15]
        fn = '../gif/ndvi_' + timestamp + '.tif'
        if not os.path.exists(fn):
            copyfile(f + '/ndvi_clip.tif', fn)
    os.chdir('../..')

if __name__ == "__main__":
    data_dir = '/media/rmsare/GALLIUMOS/ndvi/'
    curdir = os.getcwd()
    os.chdir(data_dir)

    aois = ['redsck', 'ssf', 'chair12', 'chair14']
    for aoi in aois:
        print("Processing site: {}".format(aoi.upper()))
        move_files_to_gif(aoi)
        os.chdir(aoi + '/gif/')
        for f in os.listdir('.'):
            fn = f[:-4] + '.png'
            if not os.path.exists(fn):
                plot_ndvi(f)
    os.chdir(curdir)
