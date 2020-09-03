#!/usr/bin/env python
u"""
plot_global_grace_maps.py
Written by Tyler Sutterley (05/2020)
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
    Updated 09/2020: can set months parameters to None to use defaults
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
import getopt
import numpy as np
import matplotlib
matplotlib.rcParams['axes.linewidth'] = 1.5
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Helvetica']
matplotlib.rcParams['mathtext.default'] = 'regular'
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
from matplotlib.offsetbox import AnchoredText
import cartopy.crs as ccrs
from gravity_toolkit.grace_find_months import grace_find_months
from gravity_toolkit.grace_input_months import grace_input_months
from gravity_toolkit.harmonics import harmonics
from gravity_toolkit.units import units
from gravity_toolkit.read_love_numbers import read_love_numbers
from gravity_toolkit.plm_holmes import plm_holmes
from gravity_toolkit.gauss_weights import gauss_weights
from gravity_toolkit.ocean_stokes import ocean_stokes
from gravity_toolkit.harmonic_summation import harmonic_summation
from read_cpt import read_cpt

#-- PURPOSE: import GRACE files for a given months range
def read_grace_harmonics(base_dir, parameters):
    #-- GRACE/GRACE-FO data processing center
    PROC = parameters['PROC']
    #-- GRACE/GRACE-FO data Release
    DREL = parameters['DREL']
    #-- GRACE/GRACE-FO dataset
    DSET = parameters['DSET']
    #-- find GRACE/GRACE-FO months for a dataset
    grace_months = grace_find_months(base_dir, PROC, DREL, DSET=DSET)
    #-- maximum degree and order
    LMAX = np.int(parameters['LMAX'])
    if (parameters['MMAX'].title() == 'None'):
        MMAX = np.copy(LMAX)
    else:
        MMAX = np.int(parameters['MMAX'])
    #-- SLR C2,0
    SLR_C20 = parameters['SLR_C20']
    SLR_C30 = parameters['SLR_C30']
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
        start_mon = np.int(parameters['START'])
    #-- final month to run
    if (parameters['END'].title() == 'None'):
        end_mon = np.copy(grace_months['end'])
    else:
        end_mon = np.int(parameters['END'])
    #-- GRACE/GRACE-FO missing months
    if (parameters['MISSING'].title() == 'None'):
        missing = np.copy(grace_months['missing'])
    else:
        missing = np.array(parameters['MISSING'].split(','),dtype=np.int)
    #-- reading GRACE months for input range with grace_input_months.py
    #-- replacing SLR and Degree 1 if specified
    #-- correcting for Pole-Tide and Atmospheric Jumps if specified
    return grace_input_months(base_dir, PROC, DREL, DSET, LMAX,
        start_mon, end_mon, missing, SLR_C20, DEG1, MMAX=MMAX,
        SLR_C30=SLR_C30, MODEL_DEG1=MODEL_DEG1, POLE_TIDE=POLE_TIDE, ATM=ATM)

#-- PURPOSE: read load love numbers for the range of spherical harmonic degrees
def load_love_numbers(base_dir, LMAX, REFERENCE='CF'):
    #-- load love numbers file
    love_numbers_file = os.path.join(base_dir,'love_numbers')
    #-- LMAX of load love numbers from Han and Wahr (1995) is 696.
    #-- from Wahr (2007) linearly interpolating kl works
    #-- however, as we are linearly extrapolating out, do not make
    #-- LMAX too much larger than 696
    if (LMAX > 696):
        #-- Creates arrays of kl, hl, and ll Love Numbers
        hl = np.zeros((LMAX+1))
        kl = np.zeros((LMAX+1))
        ll = np.zeros((LMAX+1))
        hl[:697],kl[:697],ll[:697] = read_love_numbers(love_numbers_file,
            FORMAT='tuple', REFERENCE=REFERENCE)
        #-- for degrees greater than 696
        for l in range(697,LMAX+1):
            hl[l] = 2.0*hl[l-1] - hl[l-2]#-- linearly extrapolating hl
            kl[l] = 2.0*kl[l-1] - kl[l-2]#-- linearly extrapolating kl
            ll[l] = 2.0*ll[l-1] - ll[l-2]#-- linearly extrapolating ll
    else:
        #-- read arrays of kl, hl, and ll Love Numbers
        hl,kl,ll = read_love_numbers(love_numbers_file,
            FORMAT='tuple', REFERENCE=REFERENCE)
    #-- return a tuple of load love numbers
    return (hl,kl,ll)

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
        cmap = eval(parameters['COLOR_MAP'])
    #-- grey color map for bad values
    cmap.set_bad('w',0.5)

    #-- dataset parameters
    LMIN = np.int(parameters['LMIN'])
    LMAX = np.int(parameters['LMAX'])
    if (parameters['MMAX'].title() == 'None'):
        MMAX = np.copy(LMAX)
    else:
        MMAX = np.int(parameters['MMAX'])
    RAD = np.float(parameters['RAD'])
    UNITS = np.int(parameters['UNITS'])

    #-- read the GRACE/GRACE-FO data for the date range
    grace_Ylms=harmonics().from_dict(read_grace_harmonics(base_dir,parameters))
    #-- use a mean file for the static field to remove
    if (parameters['MEAN_FILE'].title() == 'None'):
        grace_Ylms.mean(apply=True)
    else:
        #-- data form for input mean file (1: ascii, 2: netcdf, 3: HDF5)
        MEANFORM = np.int(parameters['MEANFORM'])
        if (MEANFORM == 1):
            mean_Ylms=harmonics().from_ascii(parameters['MEAN_FILE'],date=False)
        if (MEANFORM == 2):
            mean_Ylms=harmonics().from_netCDF4(parameters['MEAN_FILE'],date=False)
        if (MEANFORM == 3):
            mean_Ylms=harmonics().from_HDF5(parameters['MEAN_FILE'],date=False)
        #-- remove the input mean
        grace_Ylms.subtract(mean_Ylms)

    #-- filter harmonics for correlated striping errors
    if parameters['DESTRIPE'] in ('Y','y'):
        grace_Ylms = grace_Ylms.destripe()

    #-- Gaussian smoothing
    if (RAD != 0):
        wt = 2.0*np.pi*gauss_weights(RAD,LMAX)
    else:
        wt = np.ones((LMAX+1))

    #-- degree spacing (if dlon != dlat: dlon,dlat)
    #-- input degree spacing
    DDEG = np.squeeze(np.array(parameters['DDEG'].split(','),dtype=np.float))
    if (np.ndim(DDEG) == 0):
        #-- dlon == dlat
        dlon = DDEG
        dlat = DDEG
    else:
        #-- dlon ne dlat
        dlon = DDEG[0]
        dlat = DDEG[1]

    #-- Input Degree Interval
    INTERVAL = np.int(parameters['INTERVAL'])
    if (INTERVAL == 1):
        #-- (-180:180,+90:-90)
        nlon = np.int((360.0/dlon)+1.0)
        nlat = np.int((180.0/dlat)+1.0)
        glon = -180.0 + dlon*np.arange(0,nlon)
        glat = -90.0 + dlat*np.arange(0,nlat)
    elif (INTERVAL == 2):
        #-- (Degree spacing)/2
        glon = np.arange(-180.0+dlon/2.0,180.0+dlon/2.0,dlon)
        glat = np.arange(-90.0+dlat/2.0,90.0+dlat/2.0,dlat)
        nlon = len(glon)
        nlat = len(glat)

    #-- Computing plms for converting to spatial domain
    theta = (90.0-glat)*np.pi/180.0
    PLM,dPLM = plm_holmes(LMAX,np.cos(theta))

    #-- read load love numbers
    hl,kl,ll = load_love_numbers(base_dir, LMAX, REFERENCE='CF')

    #-- Setting units factor for output
    #-- dfactor computes the degree dependent coefficients
    if (UNITS == 1):
        #-- 1: cmH2O, centimeters water equivalent
        dfactor = units(lmax=LMAX).harmonic(hl,kl,ll).cmwe
    elif (UNITS == 2):
        #-- 2: mmGH, mm geoid height
        dfactor = units(lmax=LMAX).harmonic(hl,kl,ll).mmGH
    elif (UNITS == 3):
        #-- 3: mmCU, mm elastic crustal deformation
        dfactor = units(lmax=LMAX).harmonic(hl,kl,ll).mmCU
    elif (UNITS == 4):
        #-- 4: micGal, microGal gravity perturbations
        dfactor = units(lmax=LMAX).harmonic(hl,kl,ll).microGal
    elif (UNITS == 5):
        #-- 5: Pa, equivalent surface pressure in Pascals
        dfactor = units(lmax=LMAX).harmonic(hl,kl,ll).Pa
    else:
        raise ValueError(('UNITS is invalid:\n1: cmH2O\n2: mmGH\n3: mmCU '
            '(elastic)\n4:microGal\n5: Pa\n6: cmCU (viscoelastic)'))

    #-- setup Plate Carree projection
    fig, ax1 = plt.subplots(num=1, nrows=1, ncols=1, figsize=(5.5,3.5),
        subplot_kw=dict(projection=ccrs.PlateCarree()))
    a_axis = 6378137.0#-- [m] semimajor axis of the ellipsoid
    flat = 1.0/298.257223563#-- flattening of the ellipsoid
    #-- (4pi/3)R^3 = (4pi/3)(a^2)b = (4pi/3)(a^3)(1 -f)
    rad_e = a_axis*(1.0 -flat)**(1.0/3.0)

    #-- set transparency ALPHA
    ALPHA = np.float(parameters['ALPHA'])
    if (parameters['BOUNDARY'].title() == 'None'):
        #-- contours
        PRANGE = np.array(parameters['PRANGE'].split(','),dtype=np.float)
        levels = np.arange(PRANGE[0],PRANGE[1]+PRANGE[2],PRANGE[2])
        norm = colors.Normalize(vmin=PRANGE[0],vmax=PRANGE[1])
    else:
        #-- boundary between contours
        levels = np.array(parameters['BOUNDARY'].split(','),dtype=np.float)
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
        extendfrac=0.0375, orientation='horizontal', pad=0.025, shrink=0.925,
        aspect=22, drawedges=False)
    #-- rasterized colorbar to remove lines
    cbar.solids.set_rasterized(True)
    #-- Add label to the colorbar
    CBTITLE = ' '.join(parameters['CBTITLE'].split('_'))
    cbar.ax.set_xlabel(CBTITLE, labelpad=4, fontsize=13)
    if (parameters['CBUNITS'].title() != 'None'):
        CBUNITS = ' '.join(parameters['CBUNITS'].split('_'))
        cbar.ax.set_ylabel(CBUNITS, fontsize=13, rotation=0)
        cbar.ax.yaxis.set_label_coords(1.035, 0.15)
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
    ax1.outline_patch.set_linewidth(2.0)
    ax1.outline_patch.set_capstyle('projecting')
    #-- adjust subplot within figure
    fig.subplots_adjust(left=0.02,right=0.98,bottom=0.05,top=0.98)

    #-- replace data and contours to create figure frames
    figure_dpi = np.int(parameters['FIGURE_DPI'])
    figure_format = parameters['FIGURE_FORMAT']
    #-- for each input file
    for t,grace_month in enumerate(grace_Ylms.month):
        #-- convert harmonics to truncated, smoothed coefficients of output unit
        Ylms = grace_Ylms.index(t)
        Ylms.convolve(dfactor*wt)
        #-- convert spherical harmonics to output spatial grid
        data = harmonic_summation(Ylms.clm,Ylms.slm,glon,glat,
            LMIN=LMIN,LMAX=LMAX,MMAX=MMAX,PLM=PLM).T
        #-- set image
        im.set_data(data)
        #-- add date label (year-calendar month e.g. 2002-01)
        year = np.floor(Ylms.time).astype(np.int)
        calendar_month = np.int(((grace_month-1) % 12) + 1)
        date_label = r'\textbf{{{0:4d}--{1:02d}}}'.format(year,calendar_month)
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
    optlist,arglist = getopt.getopt(sys.argv[1:],'hD:', ['help','directory='])

    #-- command line parameters
    #-- standard directory is set from the PYTHONDATA environmental variable
    base_dir = os.getcwd()
    for opt, arg in optlist:
        if opt in ('-h','--help'):
            usage()
            sys.exit()
        elif opt in ("-D","--directory"):
            base_dir = os.path.expanduser(arg)

    #-- for each input parameter file
    for parameter_file in arglist:
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
        plot_grid(base_dir, parameters)
        #-- clear parameters
        parameters = None

#-- run main program
if __name__ == '__main__':
    main()
