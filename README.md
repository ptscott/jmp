This code downloads and cleans crop yield data for P.T. Scott’s paper "Dynamic Discrete Choice Estimation of Agricultural Land Use."


*** Running on HPC
- batch jobs can not be run from /archive/ directories. Standard practice is to run everything in a /scratch/ directory
- /scratch/ directories are automatically purged if not used in 60 days


*** Change Log
1_data_scraping.py
- Added try except statement when retrieving nass_url
- weather data reads dropbox url via official dropbox API
- ACCESS_TOKEN variable must be refreshed every few days to access dropbox API. This can be done by creating an empty app on the dropbox developer page, and creating an access token with sharing.read persmissions accessed on the "permissions" tab for a given dropbox app.

2_cdl_grids.py
- in clean_image function, variable name was changed to prevent conflict with PIL library method name

3_spatial_merge.R
- changed CRS projection when rasterizing TIF files


*** 0_run_all.sh

Runs all code in order, via slurm.

*** 1_data_scraping.py

Downloads NASS, CropScape, and weather data.

*** 2_cdl_grids.py

Generate sampling grids for CropScape data, accounting for both 30m and 56m datasets.

*** 3_spatial_merge.R

Do all the spatial processing.

*** 4_planting_season.py

Determine planting season (winter or summer) for each county based on seasons of predominant crops.

*** 5_weather.py

Impute weather data over the sampling grid.

*** 6_county_yields.py

Merge all data into final dataset.
