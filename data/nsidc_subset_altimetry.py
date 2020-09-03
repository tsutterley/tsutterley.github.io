#!/usr/bin/env python
u"""
nsidc_subset_altimetry.py
Written by Tyler Sutterley (07/2018)
Program to acquire and plot subsetted NSIDC data using the Valkyrie prototype

CALLING SEQUENCE:
to use a bounding box:
    python nsidc_subset_altimetry.py --bbox=-29.25,69.4,-29.15,69.50 ILVIS2

to use start and end time:
    python nsidc_subset_altimetry.py -T 2009-04-28T12:23:51,2009-04-28T12:24:00 ILATM1B

to use a polygon:
    python nsidc_subset_altimetry.py --longitude=-48,-47.9,-48,-48 \
        --latitude=69,69,69.1,69 ILATM1B

to create a plot (note polygon is same as bounding box above)
    python nsidc_subset_altimetry.py --longitude=-29.25,-29.15,-29.15,-29.25,-29.25 \
        --latitude=69.4,69.4,69.50,69.50,69.4 --plot ILATM1B

INPUTS:
    ILATM2: Airborne Topographic Mapper Icessn Elevation, Slope, and Roughness
    ILATM1B: Airborne Topographic Mapper QFIT Elevation
    ILVIS1B: Land, Vegetation and Ice Sensor Geolocated Return Energy Waveforms
    ILVIS2: Geolocated Land, Vegetation and Ice Sensor Surface Elevation Product

COMMAND LINE OPTIONS:
    --help: list the command line options
    -D X, --directory=X: Data directory
    -B X, --bbox=X: Bounding box (lonmin,latmin,lonmax,latmax)
    --longitude=X: Polygon longitudinal coordinates (comma-separated)
    --latitude=X: Polygon latitudinal coordinates (comma-separated)
    -T X, --time=X: Time range (comma-separated start and end)
    -M X, --mode=X: Permissions mode of data
    -V, --verbose: Verbose output of transferred file
    -P, --plot: Check output with a scatter plot

UPDATE HISTORY:
    Updated 06/2018: using python3 compatible octal, input and urllib
    Written 06/2017
"""
from __future__ import print_function
import future.standard_library

import os
import sys
import time
import h5py
import shutil
import getopt
import inspect
import posixpath
import dateutil.parser
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
with future.standard_library.hooks():
    import urllib.request

#-- PURPOSE: program to acquire (and plot) subsetted NSIDC data
def nsidc_subset_altimetry(PRODUCT, filepath, BOUNDS=None, LATITUDE=None,
    LONGITUDE=None, TIME=None, VERBOSE=False, PLOT=False, MODE=0o775):
    #-- create output directory if non-existent
    os.makedirs(filepath) if not os.access(filepath, os.F_OK) else None
    #-- if using latitude and longitude points
    if LATITUDE and LONGITUDE:
        ll = ','.join(['{0:f},{1:f}'.format(ln,lt) for ln,lt in zip(LONGITUDE,LATITUDE)])
        poly_flag = '?polygon={0}'.format(ll)
    else:
        poly_flag = ''
    #-- if using bounding box
    if BOUNDS:
        #-- min_lon,min_lat,max_lon,max_lat
        bbox_flag = '?bbox={0:f},{1:f},{2:f},{3:f}'.format(*BOUNDS)
    else:
        bbox_flag = ''
    #-- if using time start and end
    if TIME:
        #-- verify that start and end times are in ISO format
        start_time = dateutil.parser.parse(TIME[0]).isoformat()
        end_time = dateutil.parser.parse(TIME[1]).isoformat()
        time_flag = '?time_range={0},{1}'.format(start_time, end_time)
    else:
        time_flag = ''

    #-- full url for subset dataset
    HOST = 'http://staging.valkyrie-vm.apps.nsidc.org'
    remote_file = '{0}{1}{2}{3}'.format(PRODUCT,poly_flag,bbox_flag,time_flag)
    #-- local file
    today = time.strftime('%Y-%m-%dT%H-%M-%S',time.localtime())
    local_file = os.path.join(filepath,'{0}_{1}.H5'.format(PRODUCT,today))
    #-- Printing files transferred if VERBOSE
    args = (posixpath.join(HOST,remote_file),local_file)
    print('{0} -->\n\t{1}\n'.format(*args)) if VERBOSE else None
    #-- Create and submit request. There are a wide range of exceptions
    #-- that can be thrown here, including HTTPError and URLError.
    request = urllib.request.Request(posixpath.join(HOST,remote_file))
    response = urllib.request.urlopen(request)
    #-- copy contents to local file using chunked transfer encoding
    #-- transfer should work properly with ascii and binary data formats
    CHUNK = 16 * 1024
    with open(local_file, 'wb') as f:
        shutil.copyfileobj(response, f, CHUNK)

    #-- check output with a scatter plot
    if PLOT:
        #-- extract X, Y and Z variables from file
        keys = {}
        keys['ILATM1B'] = ['Latitude','Longitude','Elevation']
        keys['ILVIS2'] = ['LATITUDE_LOW','LONGITUDE_LOW','ELEVATION_LOW']
        dinput = {}
        with h5py.File(local_file,'r') as fileID:
            #-- map X, Y and Z to values from input dataset
            for k,v in zip(['Y','X','Z'],keys[PRODUCT]):
                dinput[k] = fileID[v][:]
        #-- create scatter plot
        fig, ax1 = plt.subplots(num=1, figsize=(8,6))
        sc = ax1.scatter(dinput['X'], dinput['Y'], c=dinput['Z'], s=1,
            cmap=plt.cm.Spectral_r)
        #-- Add colorbar for elevation and adjust size
        #-- add extension triangles to upper and lower bounds
        #-- pad = distance from main plot axis
        #-- shrink = percent size of colorbar
        #-- aspect = lengthXwidth aspect of colorbar
        cbar = plt.colorbar(sc, ax=ax1, extend='both', extendfrac=0.0375,
            pad=0.025, drawedges=False, shrink=0.92, aspect=22.5)
        #-- rasterized colorbar to remove lines
        cbar.solids.set_rasterized(True)
        #-- Add labels to the colorbar
        cbar.ax.set_ylabel('Height Above Reference Ellipsoid', labelpad=10,
            fontsize=12)
        cbar.ax.set_xlabel('m', fontsize=12)
        cbar.ax.xaxis.set_label_coords(0.5, 1.045)
        #-- ticks lines all the way across
        cbar.ax.tick_params(which='both', width=1, direction='in',
            length=13, labelsize=12)
        #-- set x and y labels, adjust tick labels and adjust tick label size
        ax1.set_ylabel(u'Latitude [\u00B0]', fontsize=12)
        ax1.set_xlabel(u'Longitude [\u00B0]', fontsize=12)
        ax1.xaxis.set_major_formatter(ticker.FormatStrFormatter('%g'))
        ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter('%g'))
        for tick in ax1.xaxis.get_major_ticks():
            tick.label.set_fontsize(12)
        for tick in ax1.yaxis.get_major_ticks():
            tick.label.set_fontsize(12)
        #-- show the plot
        plt.show()

#-- PURPOSE: help module to describe the optional input command-line parameters
def usage():
    print('\nHelp: {0}'.format(os.path.basename(sys.argv[0])))
    print(' -D X, --directory=X\tData directory')
    print(' -B X, --bbox=X\t\tBounding box (lonmin,latmin,lonmax,latmax)')
    print(' --longitude=X\t\tPolygon longitudinal coordinates (comma-separated)')
    print(' --latitude=X\t\tPolygon latitudinal coordinates (comma-separated)')
    print(' -T X, --time=X\t\tTime range (comma-separated start and end)')
    print(' -M X, --mode=X\t\tPermissions mode of data')
    print(' -V, --verbose\t\tVerbose output of transferred file')
    print(' -P, --plot\t\tCheck output with a scatter plot\n')

#-- program that calls nsidcAltimGet with arguments listed
def main():
    #-- Read the system arguments listed after the program
    long_options = ['help','bbox=','longitude=','latitude=','time=',
        'directory=','mode=','verbose','plot']
    optlist,arglist = getopt.getopt(sys.argv[1:],'hB:T:D:M:VP',long_options)

    #-- command line parameters
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    filepath = os.path.dirname(os.path.abspath(filename))
    BOUNDS = None
    lat = None
    lon = None
    TIME = None
    VERBOSE = False
    PLOT = False
    #-- permissions mode of the output files (number in octal)
    MODE = 0o775
    for opt, arg in optlist:
        if opt in ('-h','--help'):
            usage()
            sys.exit()
        elif opt in ('-D','--directory'):
            filepath = os.path.expanduser(arg)
        elif opt in ('-B','--bbox'):
            BOUNDS = [float(i) for i in arg.split(',')]
        elif opt in ('--longitude'):
            lon = [float(i) for i in arg.split(',')]
        elif opt in ('--latitude'):
            lat = [float(i) for i in arg.split(',')]
        elif opt in ('-T','--time'):
            TIME = arg.split(',')
        elif opt in ('-V','--verbose'):
            VERBOSE = True
        elif opt in ('-M','--mode'):
            MODE = int(arg, 8)
        elif opt in ('-P','--plot'):
            PLOT = True

    #-- IceBridge Products for the NSIDC subsetter
    P = {}
    P['ILATM2'] = 'Icebridge Airborne Topographic Mapper Icessn Product'
    P['ILATM1B'] = 'Icebridge Airborne Topographic Mapper QFIT Elevation'
    P['ILVIS1B'] = 'Icebridge LVIS Geolocated Return Energy Waveforms'
    P['ILVIS2'] = 'Icebridge Land, Vegetation and Ice Sensor Elevation Product'

    #-- enter dataset to transfer (ATM, LVIS, etc) as system argument
    if not arglist:
        for key,val in P.iteritems():
            print('{0}: {1}'.format(key, val))
        raise Exception('No System Arguments Listed')

    #-- check that each data product entered was correctly typed
    keys = ','.join(sorted([key for key in P.keys()]))
    for p in arglist:
        if p not in P.keys():
            raise IOError('Incorrect Data Product Entered ({0})'.format(keys))

    #-- run the program for each argument
    for p in arglist:
        nsidc_subset_altimetry(p, filepath, BOUNDS=BOUNDS, LATITUDE=lat,
            LONGITUDE=lon, TIME=TIME, VERBOSE=VERBOSE, MODE=MODE, PLOT=PLOT)

#-- run main program
if __name__ == '__main__':
    main()
