#! /usr/bin/Rscript
# Adrian Torchiana, Paul Scott
# spatially merge CDL files, slopes, and counties

# file locations
co_file <- 'data/raw/counties/tl_2010_us_county10.shp'
pr_file <- 'data/raw/protected/PADUS1_4Combined.shp'
cdl_dir <- 'data/raw/cropscape'
grid_dir <- 'data/processed/grids'
srtm_dir <- 'data/raw/srtm'
raster_dir <- 'data/raw/raster'
output_dir <- 'data/processed/spatial'

# variables
neighbor.distance <- 5

proj4_latlon <- '+proj=longlat +datum=WGS84'
proj4_albers <- '+proj=aea +lat_0=23 +lon_0=-96 +lat_1=29.5 +lat_2=45.5 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs +type=crs
'

# first install each package with install.packages('packagename')
library(maptools)
library(plyr)
library(raster)
library(rgdal)
library(sp)
library(stringr)
library(foreach)
library(ggplot2)



# command line options
args <- commandArgs(trailingOnly=TRUE)
if (length(args) == 1) {
    state.fips <- args[1]
} else {
  state.fips <- '19' # iowa
  state.fips <- '6'
}

fname <- paste(state.fips, '.csv', sep='')

# grid of points
grid <- read.csv(paste(grid_dir, fname, sep='/'), stringsAsFactors=FALSE)
grid$id <- seq.int(nrow(grid))

# define points as data frame
coords_albers <- c('x', 'y')
coords <- c('lon', 'lat')
#grid.pts <- SpatialPointsDataFrame(coords=grid[, coords], data=grid, proj4string=CRS(proj4_latlon))
grid.pts <- SpatialPointsDataFrame(coords=grid[, coords_albers], data=grid, proj4string=CRS(proj4_albers))
grid.pts <- spTransform(grid.pts, CRS(proj4_latlon))
coords_latlon <- coordinates(grid.pts)
grid.pts$lon <- coords_latlon[, 'x']
grid.pts$lat <- coords_latlon[, 'y']

# county shape file
#counties <- readShapeSpatial(co_file, proj4string=CRS(proj4_latlon))
counties <- readOGR(co_file)
counties$fips.state <- as.numeric(as.character(counties$STATEFP10))  # Careful converting factors
counties$fips.county <- as.numeric(as.character(counties$COUNTYFP10))
counties$name <- as.character(counties$NAMELSAD10)
counties.48 <- counties[counties$fips.state < 60 &  # Samoa, Guam, Puerto Rico
                        counties$fips.state != 2 &  # Alaksa
                        counties$fips.state != 15, ]  # Hawaii
stopifnot(length(unique(counties.48$fips.state)) == 48 + 1)  # 48 states plus DC
counties.48 <- spTransform(counties.48, CRS(proj4_latlon))

message('Overlaying counties')
grid.counties.48.overlay <- over(grid.pts, counties.48)
grid.pts <- spCbind(grid.pts, grid.counties.48.overlay[, c('fips.state', 'fips.county', 'name')])

#######################
### PROTECTED AREAS ###
#######################

# protected areas shapefile from USGS
protected <- readOGR(pr_file)


protected <- spTransform(protected, CRS(proj4_latlon))
message('Overlaying protected areas')
grid.prot.overlay <- over(grid.pts, protected)
grid.pts <- spCbind(grid.pts, grid.prot.overlay[, 'd_GAP_Sts'])
# saving the GAP Status, but what's important is whether
# a point falls within one of these shape files or not
# there are no missing values of this variable, so it will do

head(grid.pts)
rm(protected)

#################
### Neighbors ###
#################

message(nrow(grid.pts), ' rows and ', ncol(grid.pts), ' columns')
message('Removing points outside lower 48')
in.lower.48 <- !is.na(grid.pts$fips.state) & !is.na(grid.pts$fips.county)
grid.pts <- grid.pts[in.lower.48, ]
message('Now ', nrow(grid.pts), ' rows and ', ncol(grid.pts), ' columns')
stopifnot(nrow(grid.pts) > 0)

## Neighboring points used in slope and aspect calculations
degree.deltas <- c(neighbor.distance, 0, -neighbor.distance) / (60 * 60)
neighbor.deltas <- expand.grid(lon=degree.deltas, lat=degree.deltas)
neighbor.labels <- expand.grid(lon=c('E', '', 'W'), lat=c('N', '', 'S'))
neighbor.deltas$label <- sprintf('%s%s', neighbor.labels$lat, neighbor.labels$lon)
neighbor.deltas <- neighbor.deltas[neighbor.deltas$lat != 0 | neighbor.deltas$lon != 0, ]
stopifnot(nrow(neighbor.deltas) == 8)  # Neighbors to NW, N, NE, E, SE, S, SW, W
grid.neighbors <- data.frame(id=rep(grid.pts$id, rep(8, nrow(grid.pts))))
grid.neighbors$lon <- rep(grid.pts$lon, rep(8, nrow(grid.pts))) + rep(neighbor.deltas$lon, nrow(grid.pts))
grid.neighbors$lat <- rep(grid.pts$lat, rep(8, nrow(grid.pts))) + rep(neighbor.deltas$lat, nrow(grid.pts))
grid.neighbors$label <- rep(neighbor.deltas$label, nrow(grid.pts))
grid.neighbors <- SpatialPointsDataFrame(coords=grid.neighbors[, coords], data=grid.neighbors,
                                       proj4string=CRS(proj4_latlon))
stopifnot(nrow(grid.neighbors) == 8 * nrow(grid.pts))

##################
### Land cover ###
##################
get.raster.variable <- function(filename) {
    message('Loading ', filename)
    raster.object <- raster(filename)
    grid.pts.reproj <- spTransform(grid.pts, CRS(projection(raster.object)))
    extracted.variable <- extract(raster.object, grid.pts.reproj)
    stopifnot(length(extracted.variable) == nrow(grid.pts))
    return(extracted.variable)
}

# import CDL for 1997-2015, 2017
cdl.files <- list.files(cdl_dir, recursive=TRUE)
cdl.files <- cdl.files[str_detect(cdl.files, '^[0-9]{4}/([A-Z]{2}/)?cdl_[0-9]{2}m_r_[a-z]{2}_[0-9]{4}_albers.tif$')]
message('Found ', length(cdl.files), ' CDL files matching regex')
cdl.years <- sort(unique(str_extract(cdl.files, '[0-9]{4}')))
message('CDL years : ', paste(cdl.years, collapse=', '))
for (year in cdl.years) {
    year.regex <- sprintf('_%s_albers.tif$', year)
    year.files <- cdl.files[str_detect(cdl.files, year.regex)]  # Should find several states for given year
    message('Found ', length(year.files), ' CDL file(s) for ', year)
    varname <- sprintf('cdl.%s', year)
    raster.values <- rep(NA, nrow(grid.pts))  # Contains values for all states seen so far
    for (file in year.files) {
        filename <- file.path(cdl_dir, file)
        raster.values.state <- get.raster.variable(filename)  # Will be NA for points outside of state
        raster.values[!is.na(raster.values.state) & raster.values.state != 0] <- raster.values.state[!is.na(raster.values.state) & raster.values.state != 0]
    }
    grid.pts@data[, varname] <- raster.values
}

# CDL 2016
filename <- file.path(cdl_dir, '2016/2016_30m_cdls.img')
raster.values.2016 <- get.raster.variable(filename)
raster.values[!is.na(raster.values.2016) & raster.values.2016 != 0] <- raster.values.2016[!is.na(raster.values.2016) & raster.values.2016 != 0]
grid.pts@data[, sprintf('cdl.2016')] <- raster.values
##################
### Topography ###
##################

aspect <- function(dz.dx, dz.dy) {
    stopifnot(length(dz.dx) == 1 && length(dz.dy) == 1)
    if (dz.dy == 0) {
        if (dz.dx == 0) return(NA)
        return(pi * (1.5 - 1*(dz.dx < 0)))
    }
    aspect <- atan(dz.dx / dz.dy)
    return(aspect + (dz.dy > 0) * pi + (dz.dy < 0 && dz.dx >0)*2*pi)
}

message('Assigning altitudes using getData(\'alt\', country=\'USA\') from raster package')
tryCatch({
    altitudes <- getData('alt', country='USA', path=raster_dir)  # Returns a list of rasters
    stopifnot(is.list(altitudes) && length(altitudes) == 4)
    grid.pts$altitude <- extract(altitudes[[1]], grid.pts)  # First element of altitudes covers 48 + DC
})

message('Assigning altitudes from SRTM files')
grid.pts$srtm.altitude <- NA  # Will be populated (where possible) with values from SRTM files
grid.pts$srtm.filepath <- ''  # Path to SRTM file containing the point
grid.pts$srtm.cellnumber <- NA  # Cellnumber in corresponding SRTM file
grid.neighbors$srtm.altitude <- NA
srtm.files <- list.files(srtm_dir)
srtm.files <- srtm.files[str_detect(srtm.files, '^N[0-9]{2}W[0-9]{3}\\.hgt$')]

# make list of srtm files in bounding rectangle
# this should work for finding the cells which cover the data as a rectangle
# in the lower 48 states, but data outside the lower 48 will break it
gridmat <- grid.pts@data
minlat <- min(gridmat[,'lat'])
minlon <- min(gridmat[,'lon'])
maxlat <- max(gridmat[,'lat'])
maxlon <- max(gridmat[,'lon'])

nmin <- floor(minlat)-1
nmax <- ceiling(maxlat)+1
wmin <- -floor(maxlon)-1
wmax <- -ceiling(minlon)+1

lappend <- function (lst, ...){
  lst <- c(lst, list(...))
  return(lst)
}

srtm.files <- list()
for (w in wmin:wmax ) {
    for (n in nmin:nmax ) {
        if (n<10) {
            nstr <- paste('0', toString(n), sep='')
        }
        else {
            nstr <- toString(n)
        }
        if (w<100) {
            wstr <- paste('0', toString(w), sep='')
        }
        else {
            wstr <- toString(w)
        }
        srtmfile <- paste('N', nstr, 'W', wstr, '.hgt', sep='')
        srtm.files <- lappend(srtm.files,srtmfile)
    }
}
srtm.files <- unlist(srtm.files)

message('Reading ', length(srtm.files), ' SRTM files')
expected.file.size <- 25934402  # 2 * 3601^2 bytes


head(srtm.files)

for (file in srtm.files) {
    path <- file.path(srtm_dir, file)
    file.size <- file.info(path)$size
    message('SRTM file ', path)
    if (!file.exists(path)) {
        message('SRTM file ', path, ' is missing; skipping')
        next
    } else if (file.size != expected.file.size) {
        message('SRTM file ', path, ' has unexpected size; skipping')
        message('actual=', format(file.size, big.mark=','),
                ' expected=', format(expected.file.size, big.mark=','), ' bytes')
        next
    } else {
        message('Reading altitude from ', path)
    }
    file.conn <- file(path, 'rb')
    vec <- readBin(file.conn, 'integer', n=3601*3601, size=2, signed=TRUE, endian='big')
    close(file.conn)
    vec <- ifelse(vec == -32768, NA, vec)  # '16-bit signed integers [...] with data voids indicated by -32768'
    stopifnot(length(vec) == 3601 * 3601)
    mat <- matrix(vec, nrow=3601, ncol=3601, byrow=TRUE)
    lat.bottom <- str_extract(file, '^N[0-9]{2}')
    lat.bottom <- as.integer(substr(lat.bottom, 2, 3))
    lon.left <- str_extract(file, 'W[0-9]{3}')
    lon.left <- as.integer(substr(lon.left, 2, 4))
    srtm.raster <- raster(mat, xmn=-lon.left, xmx=(-lon.left + 1), ymn=lat.bottom, ymx=(lat.bottom + 1),
                          crs=CRS(proj4_latlon))
    ## plot(srtm.raster)  # Sanity check
    extracted.values <- extract(srtm.raster, grid.pts, cellnumbers=TRUE)  # NAs for points outside current raster
    cellnumbers <- extracted.values[, 1]
    altitudes <- extracted.values[, 2]
    stopifnot(length(altitudes) == nrow(grid.pts))
    grid.pts$srtm.altitude[!is.na(altitudes)] <- altitudes[!is.na(altitudes)]
    grid.pts$srtm.cellnumber[!is.na(cellnumbers)] <- cellnumbers[!is.na(cellnumbers)]
    grid.pts$srtm.filepath[!is.na(altitudes)] <- path
    neighbor.altitudes <- extract(srtm.raster, grid.neighbors)
    grid.neighbors$srtm.altitude[!is.na(neighbor.altitudes)] <- neighbor.altitudes[!is.na(neighbor.altitudes)]
}
message('Fraction of grid.pts with non-NA srtm.altitude: ', round(mean(!is.na(grid.pts$srtm.altitude)), 4))
unique.srtm.cells <- length(unique(sprintf('%s %s', grid.pts$srtm.filepath, grid.pts$srtm.cellnumber)))  # Includes NAs
message('Unique SRTM cells relative to number of grid.pts: ', unique.srtm.cells, ' / ', nrow(grid.pts),
        ' = ', round(unique.srtm.cells / nrow(grid.pts), 4))

message('Calculating slope and aspect')
stopifnot(nrow(grid.neighbors) == 8 * nrow(grid.pts))
grid.pts$slope <- NA
grid.pts$aspect <- NA
temp <- foreach (i = 1:nrow(grid.pts), .combine=rbind) %dopar% {
    neighbors <- grid.neighbors[grid.neighbors$id == grid.pts$id[i], ]
    stopifnot(nrow(neighbors) == 8)
    altitudes <- as.data.frame(t(neighbors$srtm.altitude))
    names(altitudes) <- neighbors$label
    stopifnot(dim(altitudes) == c(1, 8))
    altitudes[is.na(altitudes)] <- grid.pts$srtm.altitude[i]
    if (any(is.na(altitudes))) {
        slope_val <- NA
        aspect_val <- NA
    } else {
      size.x <- neighbor.distance * cos(grid.pts$lat[i]* pi / 180) * 111.3 * 1000 / (60 * 60)
      dz.dx <- -(((altitudes$NW - altitudes$NE) + 2 * (altitudes$W - altitudes$E) + (altitudes$SW - altitudes$SE)) /
                 (8 * size.x))
      size.y <- neighbor.distance * 111.6 * 1000 / (60 * 60)
      dz.dy <- (((altitudes$NW - altitudes$SW) + 2 * (altitudes$N - altitudes$S) + (altitudes$NE - altitudes$SE)) /
                (8 * size.y))
      slope_val <- atan(sqrt(dz.dx^2 + dz.dy^2))
      aspect_val <- aspect(dz.dx, dz.dy)
    }
    c(slope_val, aspect_val)
}

grid.pts$slope <- temp[, 1]
grid.pts$aspect <- temp[, 2]

##############
### Output ###
##############

write.csv(grid.pts@data, file=paste(output_dir, fname, sep='/'), row.names=FALSE)
