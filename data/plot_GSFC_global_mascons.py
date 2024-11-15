#!/usr/bin/env python
u"""
plot_GSFC_global_mascons.py
Written by Tyler Sutterley (09/2024)
Creates a series of GMT-like plots of GSFC GRACE mascon data for the globe in a
    Plate Carree (Equirectangular) projection

PYTHON DEPENDENCIES:
    numpy: Scientific Computing Tools For Python
        https://numpy.org
        https://numpy.org/doc/stable/user/numpy-for-matlab-users.html
    h5py: Python interface for Hierarchal Data Format 5 (HDF5)
        https://h5py.org
    matplotlib: Python 2D plotting library
        http://matplotlib.org/
        https://github.com/matplotlib/matplotlib
    cartopy: Python package designed for geospatial data processing
        https://scitools.org.uk/cartopy
    pyshp: Python read/write support for ESRI Shapefile format
        https://github.com/GeospatialPython/pyshp

UPDATE HISTORY:
    Updated 09/2024: added newer GSFC mascons for RL06v2.0
    Updated 04/2023: added newer GSFC mascons for RL06v2.0
    Updated 01/2023: single implicit import of gravity toolkit
    Updated 10/2022: adjust colorbar labels for matplotlib version 3.5
        added links to newer GSFC mascons Release-6 Version 2.0
    Updated 05/2022: added links to newer GSFC mascons Release-6 Version 2.0
    Updated 02/2022: added links to newer GSFC mascons Release-6 Version 1.0
    Updated 01/2022: added links to newer GSFC mascons Release-6 Version 1.0
    Updated 10/2021: numpy int and float to prevent deprecation warnings
        using time conversion routines for converting to and from months
    Updated 03/2021: added parameters for GSFC mascons Release-6 Version 1.0
    Updated 02/2021: use adjust_months function to fix special months cases
    Updated 12/2020: using utilities from time module
    Updated 10/2020: use argparse to set command line parameters
    Updated 09/2020: copy matplotlib colormap to prevent deprecation warning
    Updated 04/2020: remove depreciated latex portions
    Updated 04/2019: set cap style of cartopy geoaxes outline patch
    Updated 03/2019: replacing matplotlib basemap with cartopy
    Forked 07/2018 from plot_global_grid_all.py
    Forked 07/2018 from previous version of plot_global_grid_movie.py
    Updated 02/2017: direction="in" for matplotlib2.0 color bar ticks
    Forked 12/2015
"""
from __future__ import print_function

import sys
import os
import h5py
import copy
import argparse
import numpy as np
import matplotlib
import matplotlib.font_manager
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.patches as patches
from matplotlib.collections import PatchCollection
from matplotlib.offsetbox import AnchoredText
import cartopy.crs as ccrs
import gravity_toolkit as gravtk
from read_cpt import read_cpt

#-- rebuild the matplotlib fonts and set parameters
matplotlib.font_manager._load_fontmanager()
matplotlib.rcParams['axes.linewidth'] = 1.5
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Helvetica']
matplotlib.rcParams['mathtext.default'] = 'regular'

#-- plot mascon program
def plot_mascon(base_dir, parameters):
    #-- output directory setup
    DIRECTORY = os.path.expanduser(parameters['DIRECTORY'])
    if not os.access(DIRECTORY, os.F_OK):
        os.makedirs(DIRECTORY)

    #-- import GRACE file
    #-- set the GRACE directory
    VERSION = parameters['DREL']
    grace_dir = os.path.join(base_dir,parameters['PROC'],
        parameters['DREL'],parameters['DSET'])
    #-- GRACE HDF5 file
    grace_file = {}
    grace_file['v02.4'] = 'GSFC.glb.200301_201607_v02.4.hdf'
    # grace_file['rl06v1.0'] = 'gsfc.glb_.200204_202009_rl06v1.0_obp-ice6gd.h5'
    # grace_file['rl06v1.0'] = 'gsfc.glb_.200204_202107_rl06v1.0_obp-ice6gd.h5'
    grace_file['rl06v1.0'] = 'GSFC.glb_.200204_202110_RL06v1.0_OBP-ICE6GD_0.h5'
    # grace_file['rl06v2.0'] = 'gsfc.glb_.200204_202112_rl06v2.0_obp-ice6gd.h5'
    # grace_file['rl06v2.0'] = 'gsfc.glb_.200204_202207_rl06v2.0_obp-ice6gd.h5'
    # grace_file['rl06v2.0'] = 'gsfc.glb_.200204_202211_rl06v2.0_obp-ice6gd.h5'
    # grace_file['rl06v2.0'] = 'gsfc.glb_.200204_202312_rl06v2.0_obp-ice6gd.h5'
    # grace_file['rl06v2.0'] = 'gsfc.glb_.200204_202403_rl06v2.0_obp-ice6gd.h5'
    grace_file['rl06v2.0'] = 'gsfc.glb_.200204_202406_rl06v2.0_obp-ice6gd.h5'
    #-- valid date string (HDF5 attribute: 'days since 2002-01-00T00:00:00')
    date_string = 'days since 2002-01-01T00:00:00'
    epoch,to_secs = gravtk.time.parse_date_string(date_string)
    #-- read the HDF5 file
    with h5py.File(os.path.join(grace_dir,grace_file[VERSION]),'r') as fileID:
        nmas,nt = fileID['solution']['cmwe'].shape
        cmwe = fileID['solution']['cmwe'][:,:].copy()
        lat_center = fileID['mascon']['lat_center'][:].flatten()
        lon_center = fileID['mascon']['lon_center'][:].flatten()
        lat_span = fileID['mascon']['lat_span'][:].flatten()
        lon_span = fileID['mascon']['lon_span'][:].flatten()
        julian = 2452275.5 + fileID['time']['ref_days_middle'][:].flatten()
        MJD = gravtk.time.convert_delta_time(
            to_secs*fileID['time']['ref_days_middle'][:].flatten(),
            epoch1=epoch, epoch2=(1858,11,17,0,0,0), scale=1.0/86400.0)
    #-- sign to convert from center to patch
    lon_sign=np.array([-0.5,-0.3,-0.1,0.1,0.3,0.5,0.5,0.3,0.1,-0.1,-0.3,-0.5,-0.5])
    lat_sign=np.array([-0.5,-0.5,-0.5,-0.5,-0.5,-0.5,0.5,0.5,0.5,0.5,0.5,0.5,-0.5])
    #-- convert to -180:180
    gt180, = np.nonzero(lon_center > 180)
    lon_center[gt180] -= 360.0

    #-- convert Julian days to calendar days
    cal_date = gravtk.time.convert_julian(MJD + 2400000.5)
    #-- calculate the GRACE month (Apr02 == 004)
    #-- https://grace.jpl.nasa.gov/data/grace-months/
    #-- Notes on special months (e.g. 119, 120) below
    grace_month = gravtk.time.calendar_to_grace(cal_date['year'],
        month=cal_date['month'])
    #-- calculating the month number of 'Special Months' with accelerometer
    #-- shutoffs is more complicated as days from other months are used
    grace_month = gravtk.time.adjust_months(grace_month)

    #-- use a mean range for the static field to remove
    MEAN = np.zeros((nmas))
    if (parameters['MEAN'].title() != 'None'):
        START,END = np.array(parameters['MEAN'].split(','),dtype=np.int64)
        ind, = np.nonzero((grace_month >= START) & (grace_month <= END))
        for i in range(nmas):
            MEAN[i] = np.mean(cmwe[i,ind])

    #-- read CPT or use color map
    if (parameters['CPT_FILE'].title() != 'None'):
        #-- cpt file
        cpt = read_cpt(os.path.expanduser(parameters['CPT_FILE']))
        cmap = colors.LinearSegmentedColormap('cpt_import', cpt)
    else:
        #-- colormap
        cmap = copy.copy(eval(parameters['COLOR_MAP']))

    #-- grey color map for bad values
    cmap.set_bad('w',0.5)

    #-- setup Plate Carree map
    projection = ccrs.PlateCarree()
    fig,ax1 = plt.subplots(num=1, figsize=(5.5,3.5),
        subplot_kw=dict(projection=projection))

    #-- set transparency ALPHA
    ALPHA = np.float64(parameters['ALPHA'])
    if (parameters['BOUNDARY'].title() == 'None'):
        #-- contours
        PRANGE = np.array(parameters['PRANGE'].split(','),dtype=np.float64)
        levels = np.arange(PRANGE[0],PRANGE[1]+PRANGE[2],PRANGE[2])
        norm = colors.Normalize(vmin=PRANGE[0],vmax=PRANGE[1])
    else:
        #-- boundary between contours
        levels = np.array(parameters['BOUNDARY'].split(','),dtype=np.float64)
        norm = colors.BoundaryNorm(levels,ncolors=256)

    #-- polygon and colors
    poly_list = []
    data = np.zeros((nmas))
    #-- for each shape entity
    for i in range(nmas):
        if (lat_center[i] == 90.0):#-- NH polar mascon
            points = np.zeros((10,2))
            points[:,0] = lon_center[i] + np.linspace(0,360,10)
            points[:,1] = lat_center[i] - lat_span[i]*np.ones((10))
        if (lat_center[i] == -90.0):#-- SH polar mascon
            points = np.zeros((10,2))
            points[:,0] = lon_center[i] + np.linspace(0,360,10)
            points[:,1] = lat_center[i] + lat_span[i]*np.ones((10))
        else:
            #-- extract lat/lon coordinates for mascon
            points = np.zeros((13,2))
            points[:,0] = lon_center[i] + lon_sign*lon_span[i]
            points[:,1] = lat_center[i] + lat_sign*lat_span[i]
        #-- add mascon lat/lon to polygon list
        poly_list.append(patches.Polygon(list(zip(points[:,0],points[:,1]))))
    #-- add patch collection with color map
    p = PatchCollection(poly_list,cmap=cmap,alpha=ALPHA)
    p.set_array(data)
    p.set_edgecolor(cmap(norm(data)))
    p.set_norm(norm)
    ax1.add_collection(p)

    #-- draw coastlines
    ax1.coastlines('50m', linewidth=0.5)

    #-- Add horizontal colorbar for GRACE magnitude and adjust size
    #-- add extension triangles to upper and lower bounds
    #-- pad = distance from main plot axis
    #-- shrink = percent size of colorbar
    #-- aspect = lengthXwidth aspect of colorbar
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax1, extend='both', extendfrac=0.0375,
        orientation='horizontal', pad=0.025, shrink=0.925,
        aspect=23, drawedges=False)
    #-- rasterized colorbar to remove lines
    cbar.solids.set_rasterized(True)
    #-- Add label to the colorbar
    CBTITLE = ' '.join(parameters['CBTITLE'].split('_'))
    cbar.ax.set_title(CBTITLE, fontsize=13, rotation=0, y=-1.65, va='top')
    if (parameters['CBUNITS'].title() != 'None'):
        CBUNITS = ' '.join(parameters['CBUNITS'].split('_'))
        cbar.ax.set_xlabel(CBUNITS, fontsize=13, rotation=0, va='center')
        cbar.ax.xaxis.set_label_coords(1.075, 0.5)
    #-- Set the tick levels for the colorbar
    cbar.set_ticks(levels)
    cbar.set_ticklabels([parameters['CBFORMAT'].format(ct) for ct in levels])
    #-- ticks lines all the way across
    cbar.ax.tick_params(which='both',width=1,length=15,labelsize=13,
        direction='in')

    #-- set x and y limits
    ax1.set_xlim(-180,180)
    ax1.set_ylim(-90,90)
    #-- axis = equal
    ax1.set_aspect('equal', adjustable='box')
    #-- no ticks on the x and y axes
    ax1.get_xaxis().set_ticks([])
    ax1.get_yaxis().set_ticks([])

    #-- add date label (year-calendar month e.g. 2002-01)
    time_text = ax1.text(0.02, 0.015, '', transform=fig.transFigure,
        color='k', size=18, ha='left', va='baseline', usetex=True)

    #-- stronger linewidth on frame
    ax1.spines['geo'].set_linewidth(2.0)
    ax1.spines['geo'].set_capstyle('projecting')
    #-- adjust subplot within figure
    fig.subplots_adjust(left=0.02,right=0.98,bottom=0.05,top=0.98)

    #-- replace data and contours to create figure frames
    dpi = np.int64(parameters['FIGURE_DPI'])
    format = parameters['FIGURE_FORMAT']
    #-- for each date
    for t,mon in enumerate(grace_month):
        #-- data for time with mean removed
        data = cmwe[:,t] - MEAN
        #-- set colors for patch
        p.set_array(data)
        p.set_edgecolor(cmap(norm(data)))
        #-- add date label (year-calendar month e.g. 2002-01)
        args = (cal_date['year'][t], cal_date['month'][t])
        time_text.set_text(r'\textbf{{{0:4.0f}--{1:02.0f}}}'.format(*args))
        #-- output to file
        args = (parameters['PROC'],VERSION,mon,format)
        FIGURE_FILE = '{0}-{1}-{2:003d}.{3}'.format(*args)
        plt.savefig(os.path.join(DIRECTORY,FIGURE_FILE), dpi=dpi, format=format)
    #-- clear all figure axes
    plt.cla()
    plt.clf()
    plt.close()

#-- PURPOSE: help module to describe the optional input parameters
def usage():
    print('\nHelp: {}'.format(os.path.basename(sys.argv[0])))
    print(' -D X, --directory=X\tWorking data directory\n')

#-- This is the main part of the program that calls the individual modules
def main():
    #-- Read the system arguments listed after the program
    parser = argparse.ArgumentParser(
        description="""Creates a series of GMT-like plots of GSFC GRACE mascon
            data on a global Plate Carr\u00E9e (Equirectangular) projection
            """
    )
    #-- command line parameters
    parser.add_argument('parameters',
        type=lambda p: os.path.abspath(os.path.expanduser(p)), nargs='+',
        help='Parameter files containing specific variables for each analysis')
    #-- working data directory
    parser.add_argument('--directory','-D',
        type=lambda p: os.path.abspath(os.path.expanduser(p)),
        default=os.getcwd(),
        help='Working data directory')
    args = parser.parse_args()

    #-- for each input parameter file
    for parameter_file in args.parameters:
        #-- keep track of progress
        print(os.path.basename(parameter_file))
        #-- variable with parameter definitions
        parameters = {}
        #-- Opening parameter file and assigning file ID number (fid)
        fid = open(os.path.expanduser(parameter_file), 'r')
        #-- for each line in the file will extract the parameter (name and value)
        for fileline in fid:
            #-- Splitting the input line between parameter name and value
            part = fileline.split()
            #-- filling the parameter definition variable
            parameters[part[0]] = part[1]
        #-- close the parameter file
        fid.close()
        #-- run plot program with parameters
        plot_mascon(args.directory, parameters)
        #-- clear parameters
        parameters = None

#-- run main program
if __name__ == '__main__':
    main()
