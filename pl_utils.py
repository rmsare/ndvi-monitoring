"""
Utilitie functions using the Planet APIs
"""

import os, sys
import rasterio
import numpy as np
import matplotlib.pyplot as plt

from skimage.io import imread
import json, requests, time, zipfile

from settings import PL_API_KEY
from utils import *

def activate_asset(asset):
    asset_url = asset['_links']['_self']
    activation_url = asset['_links']['activate']
    res = session.get(activation_url)

    if res.status_code == 204:
        return 
    if res.status_code == 401:
        print("User does not have permissions to download asset")
    else:
        activated = False
        while not activated:
            check_status = session.get(asset_url)
            if check_status.json()['status'] == 'active':
                activated = True
            else:
                time.sleep(1)

    return res.status_code

def clip_asset(item_id, aoi_polygon):
    clip_payload = {
        'aoi' : aoi_polygon,
        'targets' : [
            {
                'item_id' : item_id,
                'item_type' : "PSScene4Band",
                'asset_type' : "analytic"
            }
        ]
    }

    request = requests.post('https://api.planet.com/compute/ops/clips/v1', auth=(PL_API_KEY, ''), json=clip_payload)
    clip_url = request.json()['_links']['_self']

    clip_succeeded = False
    while not clip_succeeded:
        check_state_request = requests.get(clip_url, auth=(PL_API_KEY, ''))
        
        if check_state_request.json()['state'] == 'succeeded':
            clip_download_url = check_state_request.json()['_links']['results'][0]
            clip_succeeded = True
        else:
            time.sleep(1)

    return clip_download_url

def configure_filter(aoi_polygon, datetime_min, datetime_max):
    date_filter = {
        "type" : "DateRangeFilter",
        "field_name" : "acquired",
        "config" : {
            "lte" : rfc3339(datetime_max),
            "gte" : rfc3339(datetime_min)
        }
    }

    cloud_filter = {
        "type" : "RangeFilter",
        "field_name" : "cloud_cover",
        "config" : {
            "lte" : 0.25,
            "gte" : 0
        }
    }

    geom_filter = {
        "type" : "GeometryFilter",
        "field_name" : "geometry",
        "config" : aoi_polygon 
        
    }
    
    and_filter = {
        "type" : "AndFilter",
        "config" : [date_filter, cloud_filter, geom_filter]
        }

    return and_filter

def download_pl(url, filename=None):
    res = requests.get(url, stream=True, auth=(PL_API_KEY, ""))

    if not filename:
        filename = url.split('=')[1][:10]
    if not os.path.exists(filename):
        with open(filename, 'wb') as f:
            for chunk in res.iter_content(chunk_size=1024):
                f.write(chunk)
                f.flush()

    return filename

def download_clip(url, scene_id, data_dir):
    res = requests.get(url, stream=True, auth=(PL_API_KEY, ""))

    with open(data_dir + 'data/' + scene_id + '.zip', 'wb') as f:
        for data in res.iter_content(chunk_size=1024):
            f.write(data)
            f.flush()
    
    zipped = zipfile.ZipFile(data_dir + 'data/' + scene_id + '.zip')
    zipped.extractall(data_dir + 'data/' + scene_id)
    os.remove(data_dir + 'data/' + scene_id + '.zip')

    return data_dir + 'data/' + scene_id
