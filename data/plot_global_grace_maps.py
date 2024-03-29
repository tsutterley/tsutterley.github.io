#!/usr/bin/env python
u"""
plot_global_grace_maps.py
Written by Tyler Sutterley (01/2023)
Creates a series of GMT-like plots of GRACE data for the globe in a Plate Carree
    (Equirectangular) projection

PYTHON DEPENDENCIES:
    numpy: Scientific Computing Tools For Python
        https://numpy.org
        https://numpy.org/doc/stable/user/numpy-for-matlab-users.html
    netCDF4: Python interface to the netCDF C library
        https://unidata.github.io/netcdf4-python/netCDF4/index.html
    h5py: Python interface for Hierarchal Data Format 5 (HDF5)
        https://www.h5py.org/
    matplotlib: Python 2D plotting library
        http://matplotlib.org/
        https://github.com/matplotlib/matplotlib
    cartopy: Python package designed for geospatial data processing
        https://scitools.org.uk/cartopy

UPDATE HISTORY:
    Updated 01/2023: single implicit import of gravity toolkit
    Updated 10/2022: adjust colorbar labels for matplotlib version 3.5
    Updated 10/2021: numpy int and float to prevent deprecation warnings
        using time conversion routines for converting to and from months
    Updated 03/2021: added correction for glacial isostatic adjustment (GIA)
    Updated 12/2020: added more love number options
    Updated 10/2020: use argparse to set command line parameters
    Updated 09/2020: can set months parameters to None to use defaults
        use gravity toolkit utilities to set path to load Love numbers
        copy matplotlib colormap to prevent future deprecation warning
    Updated 05/2020 for public release
    Updated 04/2020: using the harmonics class for spherical harmonic operations
        updated load love numbers read function.  remove depreciated latex part
    Updated 03/2020: switched to destripe_harmonics for filtering harmonics
    Updated 10/2019: changing Y/N flags to True/False
    Updated 07/2019: replace C30 with coefficients from SLR
    Updated 04/2019: set cap style of cartopy geoaxes outline patch
    Updated 03/2019: replacing matplotlib basemap with cartopy
    Updated 12/2018: added parameter CBEXTEND for colorbar extension triangles
    Updated 08/2018: using full release string (RL05 instead of 5)
    Updated 02/2017: direction="in" for matplotlib2.0 color bar ticks
    Forked 12/2015
"""
from __future__ import print_function

import sys
import os
import copy
import argparse
import numpy as np
import matplotlib
import matplotlib.font_manager
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
import cartopy.crs as ccrs
import gravity_toolkit as gravtk
from read_cpt import read_cpt

#-- rebuilt the matplotlib fonts and set parameters
matplotlib.font_manager._load_fontmanager()
matplotlib.rcParams['axes.linewidth'] = 1.5
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Helvetica']
matplotlib.rcParams['mathtext.default'] = 'regular'

#-- PURPOSE: import GRACE files for a given months range
def read_grace_harmonics(base_dir, parameters):
    #-- GRACE/GRACE-FO data processing center
    PROC = parameters['PROC']
    #-- GRACE/GRACE-FO data Release
    DREL = parameters['DREL']
    #-- GRACE/GRACE-FO dataset
    DSET = parameters['DSET']
    #-- find GRACE/GRACE-FO months for a dataset
    grace_months = gravtk.grace_find_months(base_dir, PROC, DREL, DSET=DSET)
    #-- maximum degree and order
    LMAX = np.int64(parameters['LMAX'])
    if (parameters['MMAX'].title() == 'None'):
        MMAX = np.copy(LMAX)
    else:
        MMAX = np.int64(parameters['MMAX'])
    #-- replace low degree harmonics with coefficients from SLR
    SLR_C20 = parameters['SLR_C20']
    SLR_21 = parameters['SLR_21']
    SLR_22 = parameters['SLR_22']
    SLR_C30 = parameters['SLR_C30']
    SLR_C40 = parameters['SLR_C40']
    SLR_C50 = parameters['SLR_C50']
    #-- Degree 1 correction
    DEG1 = parameters['DEG1']
    #-- least squares model geocenter from known coefficients
    MODEL_DEG1 = parameters['MODEL_DEG1'] in ('Y','y')
    #-- ECMWF jump corrections
    ATM = parameters['ATM'] in ('Y','y')
    #-- Pole Tide corrections from Wahr et al. (2015)
    POLE_TIDE = parameters['POLE_TIDE'] in ('Y','y')
    #-- Date Range and missing months
    #-- first month to run
    if (parameters['START'].title() == 'None'):
        start_mon = np.copy(grace_months['start'])
    else:
        start_mon = np.int64(parameters['START'])
    #-- final month to run
    if (parameters['END'].title() == 'None'):
        end_mon = np.copy(grace_months['end'])
    else:
        end_mon = np.int64(parameters['END'])
    #-- GRACE/GRACE-FO missing months
    if (parameters['MISSING'].title() == 'None'):
        missing = np.copy(grace_months['missing'])
    else:
        missing = np.array(parameters['MISSING'].split(','),dtype=np.int64)
    #-- reading GRACE months for input range with grace_input_months.py
    #-- replacing low-degree harmonics with SLR values if specified
    #-- include degree 1 (geocenter) harmonics if specified
    #-- correcting for Pole-Tide and Atmospheric Jumps if specified
    return gravtk.grace_input_months(base_dir, PROC, DREL, DSET, LMAX,
        start_mon, end_mon, missing, SLR_C20, DEG1, MMAX=MMAX, SLR_21=SLR_21,
        SLR_22=SLR_22, SLR_C30=SLR_C30, SLR_C40=SLR_C40, SLR_C50=SLR_C50,
        MODEL_DEG1=MODEL_DEG1, POLE_TIDE=POLE_TIDE, ATM=ATM)

#-- plot grid program
def plot_grid(base_dir, parameters):
    #-- output directory setup
    DIRECTORY = os.path.expanduser(parameters['DIRECTORY'])
    if not os.access(DIRECTORY, os.F_OK):
        os.makedirs(DIRECTORY)

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

    #-- dataset parameters
    LMIN = np.int64(parameters['LMIN'])
    LMAX = np.int64(parameters['LMAX'])
    if (parameters['MMAX'].title() == 'None'):
        MMAX = np.copy(LMAX)
    else:
        MMAX = np.int64(parameters['MMAX'])
    RAD = np.float64(parameters['RAD'])
    UNITS = np.int64(parameters['UNITS'])

    #-- read the GRACE/GRACE-FO data for the date range
    grace_Ylms = gravtk.harmonics().from_dict(
        read_grace_harmonics(base_dir,parameters)
    )
    #-- use a mean file for the static field to remove
    if (parameters['MEAN_FILE'].title() == 'None'):
        grace_Ylms.mean(apply=True)
    else:
        #-- data form for input mean file (ascii, netCDF4, HDF5)
        mean_Ylms = gravtk.harmonics().from_file(parameters['MEAN_FILE'],
            format=parameters['MEANFORM'], date=False)
        grace_Ylms.subtract(mean_Ylms)

    #-- filter harmonics for correlated striping errors
    if parameters['DESTRIPE'] in ('Y','y'):
        grace_Ylms = grace_Ylms.destripe()

    #-- Glacial Isostatic Adjustment file to read
    GIA = parameters['GIA'] if (parameters['GIA'].title() != 'None') else None
    GIA_FILE = os.path.expanduser(parameters['GIA_FILE'])
    #-- input GIA spherical harmonic datafiles
    GIA_Ylms_rate = gravtk.gia(lmax=LMAX).from_GIA(GIA_FILE,
        GIA=GIA, mmax=MMAX)
    # calculate the monthly mass change from GIA
    # monthly GIA calculated by gia_rate*time elapsed
    GIA_Ylms = GIA_Ylms_rate.drift(grace_Ylms.time, epoch=2007.0)
    GIA_Ylms.month[:] = np.copy(grace_Ylms.month)

    #-- Gaussian smoothing
    if (RAD != 0):
        wt = 2.0*np.pi*gravtk.gauss_weights(RAD, LMAX)
    else:
        wt = np.ones((LMAX+1))

    #-- degree spacing (if dlon != dlat: dlon,dlat)
    #-- input degree spacing
    DDEG = np.squeeze(np.array(parameters['DDEG'].split(','),dtype=np.float64))
    dlon,dlat = (DDEG,DDEG) if (np.ndim(DDEG) == 0) else (DDEG[0],DDEG[1])
    #-- Input Degree Interval
    INTERVAL = np.int64(parameters['INTERVAL'])
    if (INTERVAL == 1):
        #-- (-180:180,+90:-90)
        nlon = np.int64((360.0/dlon)+1.0)
        nlat = np.int64((180.0/dlat)+1.0)
        glon = -180.0 + dlon*np.arange(0,nlon)
        glat = -90.0 + dlat*np.arange(0,nlat)
    elif (INTERVAL == 2):
        #-- (Degree spacing)/2
        glon = np.arange(-180.0+dlon/2.0,180.0+dlon/2.0,dlon)
        glat = np.arange(-90.0+dlat/2.0,90.0+dlat/2.0,dlat)
        nlon = len(glon)
        nlat = len(glat)

    #-- Computing plms for converting to spatial domain
    theta = (90.0 - glat)*np.pi/180.0
    PLM, dPLM = gravtk.plm_holmes(LMAX,np.cos(theta))

    #-- read load love numbers
    hl,kl,ll = gravtk.load_love_numbers(LMAX, REFERENCE='CF')

    #-- Setting units factor for output
    #-- dfactor computes the degree dependent coefficients
    if (UNITS == 1):
        #-- 1: cmH2O, centimeters water equivalent
        dfactor = gravtk.units(lmax=LMAX).harmonic(hl,kl,ll).cmwe
    elif (UNITS == 2):
        #-- 2: mmGH, mm geoid height
        dfactor = gravtk.units(lmax=LMAX).harmonic(hl,kl,ll).mmGH
    elif (UNITS == 3):
        #-- 3: mmCU, mm elastic crustal deformation
        dfactor = gravtk.units(lmax=LMAX).harmonic(hl,kl,ll).mmCU
    elif (UNITS == 4):
        #-- 4: micGal, microGal gravity perturbations
        dfactor = gravtk.units(lmax=LMAX).harmonic(hl,kl,ll).microGal
    elif (UNITS == 5):
        #-- 5: Pa, equivalent surface pressure in Pascals
        dfactor = gravtk.units(lmax=LMAX).harmonic(hl,kl,ll).Pa
    else:
        raise ValueError(('UNITS is invalid:\n1: cmH2O\n2: mmGH\n3: mmCU '
            '(elastic)\n4:microGal\n5: Pa\n6: cmCU (viscoelastic)'))

    #-- setup Plate Carree projection
    fig, ax1 = plt.subplots(num=1, nrows=1, ncols=1, figsize=(5.5,3.5),
        subplot_kw=dict(projection=ccrs.PlateCarree()))

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

    #-- add place holder for figure image
    im = ax1.imshow(np.zeros((nlat,nlon)), interpolation='nearest',
        cmap=cmap, norm=norm, extent=(-180,180,-90,90), origin='lower',
        alpha=ALPHA, transform=ccrs.PlateCarree(), animated=True)
    #-- draw coastlines
    ax1.coastlines('50m', linewidth=0.5)

    #-- Add horizontal colorbar and adjust size
    #-- extend = add extension triangles to upper and lower bounds
    #-- options: neither, both, min, max
    #-- pad = distance from main plot axis
    #-- shrink = percent size of colorbar
    #-- aspect = lengthXwidth aspect of colorbar
    cbar = plt.colorbar(im, ax=ax1, extend=parameters['CBEXTEND'],
        extendfrac=0.0375, orientation='horizontal', pad=0.025,
        shrink=0.925, aspect=23, drawedges=False)
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
    figure_dpi = np.int64(parameters['FIGURE_DPI'])
    figure_format = parameters['FIGURE_FORMAT']
    #-- for each input file
    for t,grace_month in enumerate(grace_Ylms.month):
        #-- convert harmonics to truncated, smoothed coefficients of output unit
        Ylms = grace_Ylms.index(t)
        Ylms.subtract(GIA_Ylms.index(t))
        Ylms.convolve(dfactor*wt)
        #-- convert spherical harmonics to output spatial grid
        data = gravtk.harmonic_summation(Ylms.clm, Ylms.slm, glon, glat,
            LMIN=LMIN, LMAX=LMAX, MMAX=MMAX, PLM=PLM).T
        #-- set image
        im.set_data(data)
        #-- add date label (year-calendar month e.g. 2002-01)
        year,month = gravtk.time.grace_to_calendar(grace_month)
        date_label = r'\textbf{{{0:4d}--{1:02d}}}'.format(year, month)
        time_text.set_text(date_label)
        #-- output to file
        args = (parameters['PROC'],parameters['DREL'],grace_month,figure_format)
        FIGURE_FILE = '{0}-{1}-{2:003d}.{3}'.format(*args)
        plt.savefig(os.path.join(DIRECTORY,FIGURE_FILE),
            dpi=figure_dpi, format=figure_format)
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
        description="""Creates a series of GMT-like plots of GRACE data on a
            global Plate Carr\u00E9e (Equirectangular) projection
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
        plot_grid(args.directory, parameters)
        #-- clear parameters
        parameters = None

#-- run main program
if __name__ == '__main__':
    main()
