import os
import numpy as np
import pandas as pd

concat_args = {}
if int(pd.__version__.split('.')[1]) >= 23:
    concat_args['sort'] = False

yields_in = 'data/raw/nass'
planting_seasons = 'data/processed/planting_seasons.csv'
weather_in = 'data/processed/weather'
yields_out = 'data/processed/yields'

cropindex_dict = {'Corn For Grain': 11,
                  'Sorghum For Grain': 12,
                  'Soybeans': 21,
                  'Wheat Winter All': 31,
                  'Wheat Durum': 32,
                  'Wheat Other Spring': 33,
                  'Barley': 34,
                  'Oats': 35,
                  'Rice': 41,
                  'Cotton Upland': 51,
                  'Cotton Pima': 52}

df_seasons = pd.read_csv(planting_seasons)

dfs = []

files_yield = sorted([f for f in os.listdir(yields_in) if not f.startswith('.')])
files_weather = sorted([f for f in os.listdir(weather_in) if not f.startswith('.')])

files = [f for f in files_yield if f in files_weather]

for f in files:
    df = pd.read_csv(os.path.join(yields_in, f))

    df = df.rename({'state_fips_code': 'stfips', 'Harvested': 'harvested', 'Yield': 'yield'}, axis=1)
    df['fips'] = 1000 * df.stfips + df.county_code

    df['cropindex'] = np.where(df.commodity.isin(cropindex_dict),
                               df.commodity.map(cropindex_dict), np.nan)
    df['crop'] = np.floor(df.cropindex / 10)
    df['subcrop'] = df.cropindex % 10

    # drop NA
    df = df[~df.cropindex.isna()]

    df = df[['crop', 'subcrop', 'cropindex', 'year', 'fips', 'harvested', 'yield', 'stfips']]

    df_weather = pd.read_csv(os.path.join(weather_in, f))

    df = df.merge(df_weather, on=['fips', 'year'], how='left')
    df = df.merge(df_seasons, on='fips', how='inner')

    df.to_csv(os.path.join(yields_out, f), index=False)
    dfs += [df]

df_all = pd.concat(dfs, **concat_args)
df_all.to_csv(os.path.join(yields_out, 'all_counties.csv'), index=False)