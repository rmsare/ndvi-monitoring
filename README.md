# ndvi-monitoring
Scripts to produce timeseries of NDVI using images from Planet Labs' Planetscope constellation. These are in *very* early development, no guarantees!

Heavily indebted to Planet tutorials for the [Clipping API](https://github.com/planetlabs/notebooks/blob/master/jupyter-notebooks/data-api-tutorials/clip_and_ship_introduction.ipynb) and [NDVI calculation](https://github.com/planetlabs/notebooks/blob/master/jupyter-notebooks/ndvi/ndvi_planetscope.ipynb).

# TODO
- Commenting, cleanup, and refactoring to remove hacky GDAL binary calls
- Update filters to download only summer/fall months
  - ~~Alternatively, use color threhold to discard image with high % of snow cover~~
- Add QA/QC for obviously defective imagery (apply size, ~~color thresholds~~)
- Extract NDVI timeseries from survey areas, ~~neighborhood averages~~, per-pixel
- Deploy on EC2
- Detect changepoints and model seasonal trends in NDVI timeseries
