import requests
import io
import os
import shutil
import pandas as pd
import tarfile
import csv
import dropbox

from dropbox.exceptions import AuthError

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

concat_args = {}
if int(pd.__version__.split('.')[1]) >= 23:
    concat_args['sort'] = False

nass_dir = 'data/raw/nass'
cropscape_dir = 'data/raw/cropscape'
weather_dir = 'data/raw/weather'

states = ['AK', 'AL', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI',
          'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI',
          'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC',
          'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT',
          'VT', 'VA', 'WA', 'WV', 'WI', 'WY']

##############################################################################
#   NASS Data
##############################################################################

API_KEY = 'A94CCCA1-3080-303A-B3EF-5E5590AD21EE'

def get_nass_url(commodity, variable, state):
    url = 'http://quickstats.nass.usda.gov/api/api_GET/?'
    url += f'key={API_KEY}&'
    url += 'source_desc=SURVEY&'

    url += f'commodity_desc={commodity}&'
    url += f'statisticcat_desc={variable}&'

    url += f'state_alpha={state}&'
    url += 'agg_level_desc=COUNTY&'

    url += 'year__GE=1950&'
    url += 'format=csv'

    return url

commodities = ['SOYBEANS', 'SORGHUM', 'BARLEY', 'CORN',
               'OATS', 'WHEAT', 'COTTON', 'RICE']
variables = ['AREA PLANTED', 'AREA HARVESTED', 'YIELD', 'PRODUCTION']

for s in states:
    # download data
    dfs = []
    invalid_queries = []

    for c in commodities:
        for v in variables:
            try:
                data = requests.get(get_nass_url(c, v, s))
                data.raise_for_status()
                dfs += [pd.read_csv(io.StringIO(data.text), thousands=',', delimiter = ',', engine='python',on_bad_lines='skip')]
            except:
                invalid_queries += [(c, v, s)]

    print(s, 'had', len(invalid_queries), 'invalid queries')

    if len(dfs) > 0:
        df = pd.concat(dfs, **concat_args).reset_index(drop=True)
        # clean data
        df = df[['commodity_desc', 'class_desc', 'util_practice_desc',
            'statisticcat_desc', 'unit_desc', 'state_fips_code',
            'state_alpha', 'state_name', 'county_code', 'county_name',
            'year', 'Value']]
            
        df.Value = pd.to_numeric(df.Value.map(str).str.replace(',', ''), errors='coerce')

        #df = df[df.county_code != 998] # Alaska only has county 998!

        df['commodity'] = ''

        df.loc[df.commodity_desc == 'OATS', 'commodity'] = 'Oats'
        df.loc[df.commodity_desc == 'BARLEY', 'commodity'] = 'Barley'
        df.loc[df.commodity_desc == 'SOYBEANS', 'commodity'] = 'Soybeans'
        df.loc[df.commodity_desc == 'RICE', 'commodity'] = 'Rice'

        df.loc[(df.commodity_desc == 'WHEAT') &
               (df.class_desc == 'WINTER'), 'commodity'] = 'Wheat Winter All'
        df.loc[(df.commodity_desc == 'WHEAT') &
               (df.class_desc == 'SPRING, DURUM'), 'commodity'] = 'Wheat Durum'
        df.loc[(df.commodity_desc == 'WHEAT') &
               (df.class_desc == 'SPRING, (EXCL DURUM)'), 'commodity'] = 'Wheat Other Spring'
        df.loc[(df.commodity_desc == 'WHEAT') &
               (df.class_desc == 'ALL CLASSES'), 'commodity'] = 'Wheat All'

        df.loc[(df.commodity_desc == 'CORN') &
               (df.util_practice_desc == 'GRAIN'), 'commodity'] = 'Corn For Grain'
        df.loc[(df.commodity_desc == 'CORN') &
               (df.util_practice_desc == 'SILAGE'), 'commodity'] = 'Corn For Silage'
        df.loc[(df.commodity_desc == 'CORN') &
               (df.util_practice_desc == 'FORAGE'), 'commodity'] = 'Corn For Forage'
        df.loc[(df.commodity_desc == 'CORN') &
               (df.util_practice_desc == 'ALL UTILIZATION PRACTICES'), 'commodity'] = 'Corn All'

        df.loc[(df.commodity_desc == 'SORGHUM') &
               (df.util_practice_desc == 'GRAIN'), 'commodity'] = 'Sorghum For Grain'
        df.loc[(df.commodity_desc == 'SORGHUM') &
               (df.util_practice_desc == 'SILAGE'), 'commodity'] = 'Sorghum For Silage'
        df.loc[(df.commodity_desc == 'SORGHUM') &
               (df.util_practice_desc == 'ALL UTILIZATION PRACTICES'), 'commodity'] = 'Sorghum All'

        df.loc[(df.commodity_desc == 'HAY') &
               (df.class_desc == 'ALFALFA'), 'commodity'] = 'Hay Alfalfa (Dry)'
        df.loc[(df.commodity_desc == 'HAY') &
               (df.class_desc == '(EXCL ALFALFA)'), 'commodity'] = 'Hay Other (Dry)'
        df.loc[(df.commodity_desc == 'HAY') &
               (df.class_desc == 'ALL CLASSES'), 'commodity'] = 'Hay All (Dry)'

        df.loc[(df.commodity_desc == 'COTTON') &
               (df.class_desc == 'UPLAND'), 'commodity'] = 'Cotton Upland'
        df.loc[(df.commodity_desc == 'COTTON') &
               (df.class_desc == 'PIMA'), 'commodity'] = 'Cotton Pima'
        df.loc[(df.commodity_desc == 'COTTON') &
               (df.class_desc == 'ALL CLASSES'), 'commodity'] = 'Cotton All'

        stat_dict = {'AREA PLANTED': 'Planted All Purposes',
                     'AREA HARVESTED': 'Harvested',
                     'YIELD': 'Yield',
                     'PRODUCTION': 'Production'}
        unit_dict = {'ACRES': 'acres', 'BU': 'bushel', 'TONS': 'tons',
                     'BU / ACRE': 'bushel', 'TONS / ACRE': 'tons'}

        df['variable'] = df.statisticcat_desc.map(stat_dict)

        df = df[df.unit_desc.isin(unit_dict)]
        df['unit'] = df.unit_desc.map(unit_dict)

        assert len(df[df.commodity == '']) == 0

        df = df[(df.commodity != '') & (~df.Value.isna())]

        df = df.drop_duplicates()

        # reshape long to wide and output
        idx = ['commodity', 'state_fips_code', 'state_name', 'county_code', 'county_name', 'year']
        df_wide = df.pivot_table(index=idx, columns='variable', values='Value',
                                 aggfunc=sum).reset_index()
        df_wide_units = df.pivot_table(index=idx, columns='variable', values='unit',
                                       aggfunc=lambda x: [str(v) for v in x][0]).reset_index()
        cols = ['Harvested', 'Planted All Purposes', 'Production', 'Yield']
        df_wide_units = df_wide_units.rename({c: c + '_unit' for c in cols}, axis=1)
        df_wide = df_wide.merge(df_wide_units, on=idx)

        assert df_wide.state_fips_code.nunique() == 1
        state_fips = int(df_wide.state_fips_code.unique()[0])

        df_wide.to_csv(os.path.join(nass_dir, f'{state_fips}.csv'), index=False)

##############################################################################
#   CropScape Data
##############################################################################

if os.path.exists(cropscape_dir + '_temp'):
    shutil.rmtree(cropscape_dir + '_temp')
if os.path.exists(cropscape_dir):
    shutil.rmtree(cropscape_dir)

os.makedirs(cropscape_dir + '_temp')
os.makedirs(cropscape_dir)

# crop distribution 1997 to 2019
for year in range(1997, 2022):
    os.makedirs(os.path.join(cropscape_dir, str(year)))

    url = f'https://nassgeodata.gmu.edu/nass_data_cache/tar/{year}_cdls.tar.gz'
    data = requests.get(url, verify=False)
    if data.status_code == 200:
       with open(os.path.join(cropscape_dir + '_temp', f'{year}.tar.gz'), 'wb') as f:
              f.write(data.content)

       tar = tarfile.open(os.path.join(cropscape_dir + '_temp', f'{year}.tar.gz'), 'r:gz')
       tar.extractall(os.path.join(cropscape_dir, str(year)))
       tar.close()

shutil.rmtree(cropscape_dir + '_temp')

##############################################################################
#   Columbia weather data
##############################################################################




ACCESS_TOKEN = 'sl.BYAiOoeO9cQRRWIrTZKZj1j7wd7d4e_i2jeiCNXdodpD9u6ZXv1P5ngbisyNeCIIYVUVLAMIY9ST3fCYV3XBNU_L7IE7hdiLGyVp2HBoYA-4azaZdozjCeloyzTjiYGuL-gadpE'


dropbox_base_url = 'https://www.dropbox.com/sh/fe844ythm9xhz25/AABMmYzeY44zP_CwuNa1BOgoa'

dropbox_user = dropbox.dropbox_client.Dropbox(ACCESS_TOKEN)


if os.path.exists(weather_dir + '_temp'):
    shutil.rmtree(weather_dir + '_temp')
if os.path.exists(weather_dir):
    shutil.rmtree(weather_dir)

os.makedirs(weather_dir + '_temp')
os.makedirs(weather_dir)

# weather 1951 to 2019
for year in range(1951, 2020):
    os.makedirs(os.path.join(weather_dir, str(year)))


    md, response = dropbox_user.sharing_get_shared_link_file(dropbox_base_url, '/year{0}.tgz'.format(year))

    if response.status_code == 200:
        with open(os.path.join(weather_dir + '_temp', f'{year}.tgz'), 'wb') as f:
            for chunk in response.iter_content(chunk_size=4*1024*1024):  # or whatever chunk size you want
                f.write(chunk)

        tar = tarfile.open(os.path.join(weather_dir + '_temp', f'{year}.tgz'), 'r:gz')
        tar.extractall(os.path.join(weather_dir, str(year)))
        tar.close()

shutil.rmtree(weather_dir + '_temp')

# download grid info
grid_crosswalk_path = 'https://www.dropbox.com/s/aul3wy67f1gu46v/linkGridnumberFIPS.dta?dl=1'
grid_area_path = 'https://www.dropbox.com/s/t9ay0zn37lbw870/cropArea.dta?dl=1'

df_grid_crosswalk = pd.read_stata(io.BytesIO(requests.get(grid_crosswalk_path).content))
df_grid_area = pd.read_stata(io.BytesIO(requests.get(grid_area_path).content))

df_grid = df_grid_crosswalk.merge(df_grid_area, on='gridNumber')
df_grid = df_grid[['gridNumber', 'fips', 'cropArea']]
df_grid.to_csv(os.path.join(weather_dir, 'grid_info.csv'))
