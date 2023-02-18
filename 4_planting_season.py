import os
import numpy as np
import pandas as pd

spatial_in = 'data/processed/spatial'
ers_in = 'data/processed/ers_regions.csv'
file_out = 'data/processed/planting_seasons.csv'

WINTER_CUTOFF = 0.1

CROPS = {'winter': [24,   # Winter Wheat
                    26,   # Dbl Crop WinWht/Soybeans
                    27,   # Rye
                    225,  # Dbl Crop WinWht/Corn
                    236,  # Dbl Crop WinWht/Sorghum
                    238], # Dbl Crop WinWht/Cotton
         'summer': [1,    # Corn
                    2,    # Cotton
                    3,    # Rice
                    4,    # Sorghum
                    5,    # Soybeans
                    6,    # Sunflower
                    10,   # Peanuts
                    11,   # Tobacco
                    23,   # Spring Wheat
                    41,   # Sugarbeets
                    42,   # Dry Beans
                    43,   # Potatoes
                    44,   # Other Crops
                    45,   # Sugarcane
                    46,   # Sweet Potatoes
                    47,   # Misc Vegs & Fruits
                    48,   # Watermelons
                    49,   # Onions
                    50,   # Cucumbers
                    51,   # Chick Peas
                    52,   # Lentils
                    53,   # Peas
                    54,   # Tomatoes
                    55,   # Caneberries
                    56,   # Hops
                    57]}  # Herbs

assert len(set(CROPS['summer']) & set(CROPS['winter'])) == 0

dfs = []
files = [f for f in os.listdir(spatial_in) if f.endswith('.csv')]
files.sort()

for f in files:
    df = pd.read_csv(os.path.join(spatial_in, f), encoding='ISO-8859-1')
    df['fips'] = df['fips.state'] * 1000 + df['fips.county']

    # drop grid points that were in other states (there are only a few)
    df = df[df['fips.state'] == int(f[:-4])]
    
    years = []

    for col in [c for c in df.columns if c.startswith('cdl')]:
        year = col.split('.')[1]

        if np.mean(df['cdl.' + year].isna()) <= .1:
            years += [year]

            df['winter_' + year] = np.where(df[col].isin(CROPS['winter']), 1, 0)
            df['summer_' + year] = np.where(df[col].isin(CROPS['summer']), 1, 0)

    # collapse winter and summer totals by county
    df = df.groupby('fips').sum().reset_index()
    df['winter_county'] = 1

    if len(years) == 0:
        df.winter_county = np.nan

    for year in years:
        w = df['winter_' + year]
        s = df['summer_' + year]
        winter_share = w / (w + s)

        df.winter_county = np.where(winter_share < WINTER_CUTOFF,
                                    0, df.winter_county)

    df['winter_county'] = df.winter_county.astype(int)
    df = df[~df.fips.isnull()][['fips', 'winter_county']]

    dfs += [df]

df_all = pd.concat(dfs)

ers_regions = pd.read_csv(ers_in)

# region 9 only has 3 counties with winter plantings
# re-code them as summer since that's too small of a group
df_all = df_all.merge(ers_regions, on='fips', how='inner')
df_all.winter_county = np.where(df_all.region == 9, 0, df_all.winter_county)

df_all = df_all[['fips', 'winter_county']]
df_all.to_csv(file_out, index=False)