"""
Utilities for S3 data transfer
"""

import boto
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

def delete_file_from_s3(filename, bucket_name='usgs-mmh-ndvi'):
    connection = boto.connect_s3()
    bucket = connection.get_bucket(bucket_name, validate=False)
    key = bucket.get_key(filename)
    bucket.delete_key(key.name)

def delete_old_keys_from_s3(max_age, bucket_name='usgs-mmh-ndvi', subdirectory='', bad_substring=''):
    if subdirectory[-1] is not '/':
        subdirectory += '/'
    connection = boto.connect_s3()
    bucket = connection.get_bucket(bucket_name, validate=False)
    today = datetime.now()
    date_format = '%Y-%m-%dT%H:%M:%S.%fZ'
    for key in bucket.get_all_keys():
        in_subdirectory = subdirectory in key.name and subdirectory is not key.name
        key_modified = datetime.strptime(key.last_modified, date_format)
        older_than_max_age = today - key_modified >= max_age
        if in_subdirectory and older_than_max_age and bad_substring in key.name:
            key.delete()

def list_dir_s3(directory, bucket_name):
    connection = boto.connect_s3()
    bucket = connection.get_bucket(bucket_name, validate=False)
    keys = bucket.get_all_keys()
    filenames = [k.name for k in keys if directory in k.name]
    filenames = filenames.remove(directory)
    filenames = [fn.replace(directory, '') for fn in filenames]
    return filenames

def download_data_from_s3(filename, bucket_name='usgs-mmh-ndvi'):
    connection = boto.connect_s3()
    bucket = connection.get_bucket(bucket_name, validate=False)
    key = bucket.new_key(filename)
    key.get_contents_to_filename(filename)

def save_data_to_s3(data, filename=None, bucket_name='usgs-mmh-ndvi'):
    connection = boto.connect_s3()
    bucket = connection.get_bucket(bucket_name, validate=False)
    if not filename:
        d = datetime.now()
        filename = 'tmp_' + d.isoformat() + '.pk'
    key = bucket.new_key(filename)
    data.to_pickle(filename)
    key.set_contents_from_filename(filename)
    key.set_canned_acl('public-read')

def save_file_to_s3(infilename, outfilename, bucket_name='usgs-mmh-ndvi'):
    connection = boto.connect_s3()
    bucket = connection.get_bucket(bucket_name, validate=False)
    key = bucket.new_key(outfilename)
    key.set_contents_from_filename(infilename)
    key.set_canned_acl('public-read')
