import os
from PIL import Image
from PIL.TiffTags import TAGS
import numpy as np
import pandas as pd
import csv
import shutil

cdl_in = 'data/raw/cropscape' # where the CDL data starts
#cdl_out = 'data/processed/cropscape' # where to put processed CDL data
grid_out = 'data/processed/grids'
if os.path.exists(grid_out):
    shutil.rmtree(grid_out)
os.makedirs(grid_out)

# PIL loads the TIF files with mismatch between image size
# and tile boundaries. This function re-crops the image to fix this.
def clean_image(im, size=None):
    cols, rows = im.size

    max_cols = max([tile[1][2] for tile in im.tile])
    max_rows = max([tile[1][3] for tile in im.tile])

    size = (max_cols, max_rows)

    if size == None:
        im_cropped = im.crop((0, 0, cols, rows))
    else:
        im_cropped = im.crop((0, 0, size[0], size[1]))
        if size[0] != cols or size[1] != rows:
            print('-\texpected size', size, 'different from actual size', (cols, rows))

    im_cropped.tag = im.tag

    return im_cropped

# turn off image size warning
Image.MAX_IMAGE_PIXELS = None

fips_codes = {'al': 1, 'ak': 2, 'az': 4, 'ar': 5, 'ca': 6, 'co': 8, 'ct': 9,
              'de': 10, 'dc': 11, 'fl': 12, 'ga': 13, 'hi': 15, 'id': 16,
              'il': 17, 'in': 18, 'ia': 19, 'ks': 20, 'ky': 21, 'la': 22,
              'me': 23, 'md': 24, 'ma': 25, 'mi': 26, 'mn': 27, 'ms': 28,
              'mo': 29, 'mt': 30, 'ne': 31, 'nv': 32, 'nh': 33, 'nj': 34,
              'nm': 35, 'ny': 36, 'nc': 37, 'nd': 38, 'oh': 39, 'ok': 40,
              'or': 41, 'pa': 42, 'ri': 44, 'sc': 45, 'sd': 46, 'tn': 47,
              'tx': 48, 'ut': 49, 'vt': 50, 'va': 51, 'wa': 53, 'wv': 54,
              'wi': 55, 'wy': 56}

# -----------------------------------------------------------------------------
# get sampling centroids for 30/56m grids

print()
print('processing CDL data')
print()

# get all TIF files
tif_list = []
for path, _, files in os.walk(cdl_in):
    for file in [f for f in files if f.endswith('_albers.tif')]:
        if not file.startswith('.'):
            tif_list += [os.path.join(path, file)]

tifs = {}

# organize files by state and cell size (30m or 56m)
for file in tif_list:
    cellsize = int(file[-24: -22])
    state = file[-18: -16]

    assert cellsize in [30, 56]

    if state not in tifs:
        tifs[state] = {30: [], 56: []}

    tifs[state][cellsize] += [file]

# get sampling offsets for states with both grids
states = sorted(tifs.keys())

offsets = {}

for state in states:
    offsets[state] = {}

    if len(tifs[state][30]) >= 1 and len(tifs[state][56]) >= 1:
        print(state.upper(), 'has 30m and 56m grids')

        file_30 = tifs[state][30][0]
        file_56 = tifs[state][56][0]

        im_30 = clean_image(Image.open(file_30))
        im_56 = clean_image(Image.open(file_56))

        im_meta_30 = {TAGS[key]: im_30.tag[key] for key in im_30.tag.keys()}
        im_meta_56 = {TAGS[key]: im_56.tag[key] for key in im_56.tag.keys()}

        im_30.close()
        im_56.close()

        # get relevant scale parameters for both grids
        ncols_30, nrows_30 = im_30.size
        cellsize_30 = int(im_meta_30['ModelPixelScaleTag'][0])
        xllcorner_30 = int(im_meta_30['ModelTiepointTag'][3])
        yulcorner_30 = int(im_meta_30['ModelTiepointTag'][4])
        yllcorner_30 = yulcorner_30 - 30 * nrows_30

        ncols_56, nrows_56 = im_56.size
        cellsize_56 = int(im_meta_56['ModelPixelScaleTag'][0])
        xllcorner_56 = int(im_meta_56['ModelTiepointTag'][3])
        yulcorner_56 = int(im_meta_56['ModelTiepointTag'][4])
        yllcorner_56 = yulcorner_56 - 56 * nrows_56

        assert cellsize_30 == 30
        assert cellsize_56 == 56

        # use scale parameters to compute lower left centroids
        #xshift = xllcorner_30 - xllcorner_56
        #yshift = yllcorner_30 - yllcorner_56
        xshift = (xllcorner_30 + 15) - (xllcorner_56 + 28)
        yshift = (yllcorner_30 + 15) - (yllcorner_56 + 28)

        # we can only find exact centroid matches if shifts are even
        xshift += xshift % 2
        yshift += yshift % 2

        # Calculate how many steps to take in each direction before first sample point.
        # We want to find dx_30, dx_56, dy_30, and dy_56 that satisfy
        # xllcorner_56 + 56 * dx_56 ≡ xllcorner_30 + 30 * dx_30 (mod 840).
        # The following expressions satisfy this congruence.
        dx_56 = (7 * xshift // 2) % 15
        dy_56 = (7 * yshift // 2) % 15
        dx_30 = (13 * xshift // 2) % 28
        dy_30 = (13 * yshift // 2) % 28

        assert (56 * dx_56 - xshift) % 30 == 0
        assert (56 * dy_56 - yshift) % 30 == 0
        assert (30 * dx_30 + xshift) % 56 == 0
        assert (30 * dy_30 + yshift) % 56 == 0

        offsets[state][30] = (nrows_30, ncols_30, dx_30, dy_30, xllcorner_30, yllcorner_30)
        offsets[state][56] = (nrows_56, ncols_56, dx_56, dy_56, xllcorner_56, yllcorner_56)

    elif len(tifs[state][30]) >= 1:
        print(state.upper(), 'only has 30m grids')

        file = tifs[state][30][0]
        im = clean_image(Image.open(file))
        im_meta = {TAGS[key]: im.tag[key] for key in im.tag.keys()}
        im.close()

        ncols, nrows = im.size
        cellsize = int(im_meta['ModelPixelScaleTag'][0])
        xllcorner = int(im_meta['ModelTiepointTag'][3])
        yulcorner = int(im_meta['ModelTiepointTag'][4])
        yllcorner = yulcorner - 30 * nrows

        assert cellsize == 30

        offsets[state][30] = (nrows, ncols, 0, 0, xllcorner, yllcorner)
        offsets[state][56] = (None, None, None, None, None, None)

    elif len(tifs[state][56]) >= 1:
        print(state.upper(), 'only has 56m grids')

        file = tifs[state][56][0]
        im = clean_image(Image.open(file))
        im_meta = {TAGS[key]: im.tag[key] for key in im.tag.keys()}
        im.close()

        ncols, nrows = im.size
        cellsize = int(im_meta['ModelPixelScaleTag'][0])
        xllcorner = int(im_meta['ModelTiepointTag'][3])
        yulcorner = int(im_meta['ModelTiepointTag'][4])
        yllcorner = yulcorner - 56 * nrows

        assert cellsize == 56

        offsets[state][56] = (nrows, ncols, 0, 0, xllcorner, yllcorner)
        offsets[state][30] = (None, None, None, None, None, None)

    else:
        print(state, 'has no grids...........')
        offsets[state][30] = (None, None, None, None, None, None)
        offsets[state][56] = (None, None, None, None, None, None)

print()

# -----------------------------------------------------------------------------
# output grid files

for state in states:
    print('processing grid for', state.upper())

    if len(tifs[state][30]) >= 1:
        cellsize = 30
    elif len(tifs[state][56]) >= 1:
        cellsize = 56
    else:
        continue

    dn = 840 // cellsize
    nrows, ncols, dx, dy, xllcorner, yllcorner = offsets[state][cellsize]

    # read and check image file
    file = tifs[state][cellsize][0]
    im = clean_image(Image.open(file), size=(ncols, nrows))

    im_meta = {TAGS[key]: im.tag[key] for key in im.tag.keys()}
    assert (ncols, nrows) == im.size # only true after crop!
    assert int(im_meta['ModelPixelScaleTag'][0]) == cellsize
    assert int(im_meta['ModelTiepointTag'][3]) == xllcorner
    assert int(im_meta['ModelTiepointTag'][4]) == yllcorner + cellsize * nrows

    # create grid
    crop_cover = np.array(im)

    grid = [('x', 'y')]

    x0 = xllcorner + cellsize * dx + cellsize // 2
    y0 = yllcorner + cellsize * dy + cellsize // 2

    i_start = (nrows - dy - 1) % dn

    for i in range(i_start, nrows, dn):
        for j in range(dx, ncols, dn):
            if crop_cover[i, j] != 0:
                grid_x = x0 + (j - dx) * cellsize
                grid_y = y0 + (nrows - dy - 1 - i) * cellsize
                grid += [(grid_x, grid_y)]

    state_code = str(fips_codes[state])
    

    # output to csv
    with open(os.path.join(grid_out, state_code + '.csv'), 'w') as f:
        writer = csv.writer(f)
        writer.writerows(grid)

'''
# -----------------------------------------------------------------------------
# import TIFs, resample, and output to csv

for state in tifs:
    print('processing', state.upper())
    for cellsize in [30, 56]:
        nrows, ncols, dx, dy, xllcorner, yllcorner = offsets[state][cellsize]
        dn = 840 // cellsize

        for file in tifs[state][cellsize]:
            im = clean_image(Image.open(file), size=(ncols, nrows))

            # check file
            im_meta = {TAGS[key]: im.tag[key] for key in im.tag.keys()}
            assert (ncols, nrows) == im.size # only true after crop!
            assert int(im_meta['ModelPixelScaleTag'][0]) == cellsize
            assert int(im_meta['ModelTiepointTag'][3]) == xllcorner
            assert int(im_meta['ModelTiepointTag'][4]) == yllcorner

            # resample image
            crop_cover = np.array(im)

            x0 = xllcorner + cellsize * dx + cellsize // 2
            y0 = yllcorner + cellsize * dy + cellsize // 2

            samples = [('x', 'y' , 'z')]

            i_start = (nrows - dy - 1) % dn

            for i in range(i_start, nrows, dn):
                for j in range(dx, ncols, dn):
                    samples += [(x0 + (j - dx) * cellsize,
                                 y0 + (nrows - dy - 1 - i) * cellsize,
                                 crop_cover[i, j])]

            # output to csv
            year = file[-15: -11]
            with open(os.path.join(cdl_out, state + '_' + year + '.csv'), 'w') as f:
                writer = csv.writer(f)
                writer.writerows(samples)

            im.close()
'''