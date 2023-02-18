import sys
import os
import numpy as np
import pandas as pd

weather_in = 'data/raw/weather'
grid_file = 'data/raw/weather/grid_info.csv'
weather_out = 'data/processed/weather'

# read state_fips parameter
if len(sys.argv) >= 2:
    state_fips = sys.argv[1]
else:
    state_fips = '19'

# impute degree days from sinusoidal fit
def impute_degree_day(tmin, tmax, degree):
    if tmax <= degree:
        return 0
    elif tmin >= degree:
        if tmin == degree:
            return 0
        return (tmax + tmin) / 2 - degree
    else:
        theta = np.arcsin(min(max((2 * degree - tmin - tmax) / (tmax - tmin), -1), 1))
        return ((tmax - tmin) / 2 * (np.cos(theta) - np.sin(theta) * (np.pi / 2 - theta))) / np.pi

impute_degree_day = np.vectorize(impute_degree_day)

# get weather files
f_list = []
for path, _, files in os.walk(weather_in):
    for file in [f for f in files if f.endswith('.dta')]:
        if not file.startswith('.'):
            f_list += [os.path.join(path, file)]

def get_fips(f):
    return int(f.split('fips')[1].split('.')[0]) // 1000

f_list = [f for f in f_list if get_fips(f) == int(state_fips)]
f_list.sort()
print(len(f_list), 'files found for state', state_fips)

if len(f_list) >= 1:
    dfs = []

    for f in f_list:
        df = pd.read_stata(f)

        df['year'] = df.dateNum.dt.year
        df['month'] = df.dateNum.dt.month

        # separate spring-summer (March-August) and winter-fall (Sept-Feb) weather variables
        assert df.month.min() >= 1 and df.month.max() <= 12
        df['season'] = np.where((df.month >= 3) & (df.month <= 8), 'summer', 'winter')

        # make sure end-of-year months are associated with the growing season for the following year
        df.year = np.where(df.month >= 9, df.year + 1, df.year)

        # degree days above 10C/30C
        df['dd10'] = impute_degree_day(df.tMin, df.tMax, 10)
        df['dd30'] = impute_degree_day(df.tMin, df.tMax, 30)

        # precipitation-temperature interactions
        df['ddr10'] = df.prec * df.dd10
        df['ddr30'] = df.prec * df.dd30

        # collapse by year
        df_annual = df.groupby(['gridNumber', 'year', 'season']).sum().reset_index()
        df_annual = df_annual[['gridNumber', 'year', 'season', 'dd10', 'dd30',
                               'prec', 'ddr10', 'ddr30']]

        dfs += [df_annual]

    df = pd.concat(dfs)
    df = df.groupby(['gridNumber', 'year', 'season']).sum().reset_index()

    # merge in FIPS data, re-weight, and collapse to county
    grid_fips = pd.read_csv(grid_file)

    df = df.merge(grid_fips, on='gridNumber', how='inner')

    group_vars = ['fips', 'year', 'season']
    collapse_vars = ['dd10', 'dd30', 'prec', 'ddr10', 'ddr30']
    weight_var = 'cropArea'

    df['weight'] = df[weight_var]
    for var in collapse_vars:
        df[var] *= df.weight

    df_county = df.groupby(group_vars).sum().reset_index()
    for var in collapse_vars:
        df_county[var] /= df_county.weight

    df_county = df_county[group_vars + collapse_vars]

    df_county.to_csv(os.path.join(weather_out, state_fips + '.csv'), index=False)
else:
    print('state', state_fips, 'does not exist')
