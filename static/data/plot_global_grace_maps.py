#!/usr/bin/env python
"""
plot_global_grace_maps.py
Written by Tyler Sutterley (09/2026)
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
    Updated 09/2026: switch from parameter files to argparse arguments
        use upstream file logger for verbose output
        use pathlib to define and operate on paths
        place some imports behind try/except statements
        added color palette table (cpt) file reader from tools
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
import logging
import pathlib
import argparse
import warnings
import traceback
import numpy as np
import gravity_toolkit as gravtk

# attempt imports
try:
    import cartopy.crs as ccrs
except ModuleNotFoundError:
    warnings.warn("cartopy not available", ImportWarning)
try:
    import matplotlib
    import matplotlib.font_manager
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    import matplotlib.colors as colors

    # rebuild the matplotlib fonts and set parameters
    matplotlib.font_manager._load_fontmanager()
    matplotlib.rcParams["axes.linewidth"] = 1.5
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = ["Helvetica"]
    matplotlib.rcParams["mathtext.default"] = "regular"
except ModuleNotFoundError:
    warnings.warn("matplotlib not available", ImportWarning)


# PURPOSE: keep track of threads
def info(args):
    # get logger
    logger = logging.getLogger(__name__)
    logger.info(pathlib.Path(sys.argv[0]).name)
    logger.info(args)
    logger.info(f"module name: {__name__}")
    if hasattr(os, "getppid"):
        logger.info(f"parent process: {os.getppid():d}")
    logger.info(f"process id: {os.getpid():d}")


# PURPOSE: import GRACE/GRACE-FO GSM files for a given months range
def load_shm(
    base_dir,
    PROC,
    DREL,
    DSET,
    start_mon,
    end_mon,
    missing,
    LMAX,
    SLR_C20=None,
    DEG1=None,
    **kwargs,
):
    # find GRACE/GRACE-FO months for a dataset
    grace_months = gravtk.grace_find_months(base_dir, PROC, DREL, DSET=DSET)
    # Date Range and missing months
    # first month to run
    if start_mon is None:
        start_mon = np.copy(grace_months["start"])
    # final month to run
    if end_mon is None:
        end_mon = np.copy(grace_months["end"])
    # reading GRACE/GRACE-FO GSM solutions for input date range
    # replacing low-degree harmonics with SLR values if specified
    # include degree 1 (geocenter) harmonics if specified
    # correcting for Pole-Tide and Atmospheric Jumps if specified
    grace_Ylms = gravtk.grace_input_months(
        base_dir,
        PROC,
        DREL,
        DSET,
        LMAX,
        start_mon,
        end_mon,
        missing,
        SLR_C20,
        DEG1,
        **kwargs,
    )
    # returning input variables as a harmonics object
    return gravtk.harmonics().from_dict(grace_Ylms)


# plot grid program
def plot_grace(
    base_dir,
    PROC,
    DREL,
    DSET,
    LMAX,
    RAD,
    START=None,
    END=None,
    MISSING=None,
    LMIN=None,
    MMAX=None,
    LOVE_NUMBERS=0,
    REFERENCE=None,
    DESTRIPE=False,
    UNITS=None,
    GIA=None,
    GIA_FILE=None,
    ATM=False,
    POLE_TIDE=False,
    DEG1=None,
    DEG1_FILE=None,
    MODEL_DEG1=False,
    SLR_C20=None,
    SLR_21=None,
    SLR_22=None,
    SLR_C30=None,
    SLR_C40=None,
    SLR_C50=None,
    MEAN_FILE=None,
    MEANFORM=None,
    DDEG=None,
    INTERVAL=None,
    COLOR_MAP=None,
    CPT_FILE=None,
    PLOT_RANGE=None,
    BOUNDARY=None,
    ALPHA=1.0,
    CBEXTEND=None,
    CBTITLE=None,
    CBUNITS=None,
    CBFORMAT=None,
    OUTPUT_DIRECTORY=None,
    FIGURE_FORMAT=None,
    FIGURE_DPI=None,
    MODE=0o775,
):
    # get logger
    logger = logging.getLogger(__name__)
    # output directory setup
    OUTPUT_DIRECTORY = pathlib.Path(OUTPUT_DIRECTORY).expanduser().absolute()
    # verify output directory exists
    if not OUTPUT_DIRECTORY.exists():
        OUTPUT_DIRECTORY.mkdir(mode=MODE, parents=True, exist_ok=True)

    # read the GRACE/GRACE-FO data for the date range
    grace_Ylms = load_shm(
        base_dir,
        PROC,
        DREL,
        DSET,
        START,
        END,
        MISSING,
        LMAX,
        MMAX=MMAX,
        SLR_C20=SLR_C20,
        SLR_21=SLR_21,
        SLR_22=SLR_22,
        SLR_C30=SLR_C30,
        SLR_C40=SLR_C40,
        SLR_C50=SLR_C50,
        ATM=ATM,
        POLE_TIDE=POLE_TIDE,
    )
    # use a mean file for the static field to remove
    if MEAN_FILE:
        # data form for input mean file (ascii, netCDF4, HDF5)
        # using path relative to base
        mean_Ylms = gravtk.harmonics().from_file(
            base_dir.joinpath(MEAN_FILE),
            format=MEANFORM,
            date=False,
        )
        # remove the input mean
        grace_Ylms.subtract(mean_Ylms)
    else:
        grace_Ylms.mean(apply=True)

    # filter harmonics for correlated striping errors
    if DESTRIPE:
        # destriping GRACE GSM and GAD coefficients
        grace_Ylms = grace_Ylms.destripe()

    # Glacial Isostatic Adjustment file to read
    # input GIA spherical harmonic datafiles
    GIA_Ylms_rate = gravtk.gia(lmax=LMAX).from_GIA(GIA_FILE, GIA=GIA, mmax=MMAX)
    # calculate the monthly mass change from GIA
    # monthly GIA calculated by gia_rate*time elapsed
    GIA_Ylms = GIA_Ylms_rate.drift(grace_Ylms.time, epoch=2007.0)
    GIA_Ylms.month[:] = np.copy(grace_Ylms.month)

    # Gaussian smoothing
    if RAD != 0:
        wt = 2.0 * np.pi * gravtk.gauss_weights(RAD, LMAX)
    else:
        wt = np.ones((LMAX + 1))

    # degree spacing (if dlon != dlat: dlon,dlat)
    # input degree spacing
    dlon, dlat = (DDEG[0], DDEG[0]) if (len(DDEG) == 1) else (DDEG[0], DDEG[1])
    # Input Degree Interval
    if INTERVAL == 1:
        # (-180:180,+90:-90)
        nlon = np.int64((360.0 / dlon) + 1.0)
        nlat = np.int64((180.0 / dlat) + 1.0)
        glon = -180.0 + dlon * np.arange(0, nlon)
        glat = -90.0 + dlat * np.arange(0, nlat)
    elif INTERVAL == 2:
        # (Degree spacing)/2
        glon = np.arange(-180.0 + dlon / 2.0, 180.0 + dlon / 2.0, dlon)
        glat = np.arange(-90.0 + dlat / 2.0, 90.0 + dlat / 2.0, dlat)
        nlon = len(glon)
        nlat = len(glat)

    # Computing plms for converting to spatial domain
    theta = (90.0 - glat) * np.pi / 180.0
    PLM, dPLM = gravtk.plm_holmes(LMAX, np.cos(theta))

    # read load love numbers
    hl, kl, ll = gravtk.load_love_numbers(LMAX, REFERENCE="CF")

    # Setting units factor for output
    # dfactor computes the degree dependent coefficients
    if UNITS == 1:
        # 1: cmH2O, centimeters water equivalent
        dfactor = gravtk.units(lmax=LMAX).harmonic(hl, kl, ll).cmwe
    elif UNITS == 2:
        # 2: mmGH, mm geoid height
        dfactor = gravtk.units(lmax=LMAX).harmonic(hl, kl, ll).mmGH
    elif UNITS == 3:
        # 3: mmCU, mm elastic crustal deformation
        dfactor = gravtk.units(lmax=LMAX).harmonic(hl, kl, ll).mmCU
    elif UNITS == 4:
        # 4: micGal, microGal gravity perturbations
        dfactor = gravtk.units(lmax=LMAX).harmonic(hl, kl, ll).microGal
    elif UNITS == 5:
        # 5: Pa, equivalent surface pressure in Pascals
        dfactor = gravtk.units(lmax=LMAX).harmonic(hl, kl, ll).Pa
    else:
        raise ValueError(
            (
                "UNITS is invalid:\n1: cmH2O\n2: mmGH\n3: mmCU "
                "(elastic)\n4:microGal\n5: Pa\n6: cmCU (viscoelastic)"
            )
        )

    # setup Plate Carree projection
    fig, ax1 = plt.subplots(
        num=1,
        nrows=1,
        ncols=1,
        figsize=(5.5, 3.5),
        subplot_kw=dict(projection=ccrs.PlateCarree()),
    )

    # read CPT or use color map
    if CPT_FILE is not None:
        # cpt file
        cmap = gravtk.tools.from_cpt(CPT_FILE)
    else:
        # colormap
        cmap = plt.get_cmap(COLOR_MAP).copy()
    # grey color map for bad values
    cmap.set_bad("w", 0.5)

    # set normalization for colormap
    if BOUNDARY is None:
        # contours
        levels = np.arange(
            PLOT_RANGE[0],
            PLOT_RANGE[1] + PLOT_RANGE[2],
            PLOT_RANGE[2],
        )
        norm = colors.Normalize(vmin=PLOT_RANGE[0], vmax=PLOT_RANGE[1])
    else:
        # boundary between contours
        levels = np.array(BOUNDARY, dtype=np.float64)
        norm = colors.BoundaryNorm(BOUNDARY, ncolors=256)

    # add place holder for figure image
    # plot image with transparency using normalization
    im = ax1.imshow(
        np.zeros((nlat, nlon)),
        interpolation="nearest",
        cmap=cmap,
        norm=norm,
        extent=(-180, 180, -90, 90),
        origin="lower",
        alpha=ALPHA,
        transform=ccrs.PlateCarree(),
        animated=True,
    )
    # draw coastlines
    ax1.coastlines("50m", linewidth=0.5)

    # Add horizontal colorbar and adjust size
    # extend = add extension triangles to upper and lower bounds
    # options: neither, both, min, max
    # pad = distance from main plot axis
    # shrink = percent size of colorbar
    # aspect = lengthXwidth aspect of colorbar
    cbar = plt.colorbar(
        im,
        ax=ax1,
        extend=CBEXTEND,
        extendfrac=0.0375,
        orientation="horizontal",
        pad=0.025,
        shrink=0.925,
        aspect=23,
        drawedges=False,
    )
    # rasterized colorbar to remove lines
    cbar.solids.set_rasterized(True)
    # Add label to the colorbar
    CBTITLE = " ".join(CBTITLE.split("_"))
    cbar.ax.set_title(CBTITLE, fontsize=13, rotation=0, y=-1.65, va="top")
    cbar.ax.set_xlabel(CBUNITS, fontsize=13, rotation=0, va="center")
    cbar.ax.xaxis.set_label_coords(1.075, 0.5)
    # Set the tick levels for the colorbar
    cbar.set_ticks(levels)
    cbar.set_ticklabels([CBFORMAT.format(ct) for ct in levels])
    # ticks lines all the way across
    cbar.ax.tick_params(
        which="both",
        width=1,
        length=15,
        labelsize=13,
        direction="in",
    )

    # axis = equal
    ax1.set_aspect("equal", adjustable="box")
    # no ticks on the x and y axes
    ax1.get_xaxis().set_ticks([])
    ax1.get_yaxis().set_ticks([])

    # add date label (year-calendar month e.g. 2002-01)
    time_text = ax1.text(
        0.02,
        0.015,
        "",
        transform=fig.transFigure,
        color="k",
        size=18,
        ha="left",
        va="baseline",
        usetex=True,
    )

    # stronger linewidth on frame
    ax1.spines["geo"].set_linewidth(2.0)
    ax1.spines["geo"].set_capstyle("projecting")
    # adjust subplot within figure
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.05, top=0.98)

    # for each input file
    for t, mon in enumerate(grace_Ylms.month):
        # convert harmonics to truncated, smoothed coefficients of output unit
        Ylms = grace_Ylms.index(t)
        Ylms.subtract(GIA_Ylms.index(t))
        Ylms.convolve(dfactor * wt)
        # convert spherical harmonics to output spatial grid
        data = gravtk.harmonic_summation(
            Ylms.clm,
            Ylms.slm,
            glon,
            glat,
            LMIN=LMIN,
            LMAX=LMAX,
            MMAX=MMAX,
            PLM=PLM,
        ).T
        # set image
        im.set_data(data)
        # add date label (year-calendar month e.g. 2002-01)
        year, month = gravtk.time.grace_to_calendar(mon)
        date_label = r"\textbf{{{0:4d}--{1:02d}}}".format(year, month)
        time_text.set_text(date_label)
        # output to file
        FIGURE_FILE = f"{PROC}-{DREL}-{mon:003d}.{FIGURE_FORMAT}"
        OUTPUT_FILE = OUTPUT_DIRECTORY.joinpath(FIGURE_FILE)
        plt.savefig(OUTPUT_FILE, dpi=FIGURE_DPI, format=FIGURE_FORMAT)
    # clear all figure axes
    plt.cla()
    plt.clf()
    plt.close()


# PURPOSE: create argument parser
def arguments():
    parser = argparse.ArgumentParser(
        description="""Creates a series of GMT-like plots of GRACE data on a
            global Plate Carr\u00e9e (Equirectangular) projection
            """,
        fromfile_prefix_chars="@",
    )
    parser.convert_arg_line_to_args = gravtk.utilities.convert_arg_line_to_args
    # working data directory
    parser.add_argument(
        "--directory",
        "-D",
        type=pathlib.Path,
        default=gravtk.utilities.get_cache_path(ensure_exists=False),
        help="Working data directory",
    )
    parser.add_argument(
        "--output-directory",
        "-O",
        type=pathlib.Path,
        default=pathlib.Path().cwd(),
        help="Output directory for spatial files",
    )
    # Data processing center or satellite mission
    parser.add_argument(
        "--center",
        "-c",
        metavar="PROC",
        type=str,
        required=True,
        help="GRACE/GRACE-FO Processing Center",
    )
    # GRACE/GRACE-FO data release
    parser.add_argument(
        "--release",
        "-r",
        metavar="DREL",
        type=str,
        default="RL06",
        help="GRACE/GRACE-FO Data Release",
    )
    # GRACE/GRACE-FO Level-2 data product
    parser.add_argument(
        "--product",
        "-p",
        metavar="DSET",
        type=str,
        default="GSM",
        help="GRACE/GRACE-FO Level-2 data product",
    )
    # minimum spherical harmonic degree
    parser.add_argument(
        "--lmin",
        type=int,
        default=1,
        help="Minimum spherical harmonic degree",
    )
    # maximum spherical harmonic degree and order
    parser.add_argument(
        "--lmax",
        "-l",
        type=int,
        default=60,
        help="Maximum spherical harmonic degree",
    )
    parser.add_argument(
        "--mmax",
        "-m",
        type=int,
        default=None,
        help="Maximum spherical harmonic order",
    )
    # start and end GRACE/GRACE-FO months
    parser.add_argument(
        "--start",
        "-S",
        type=int,
        default=4,
        help="Starting GRACE/GRACE-FO month",
    )
    parser.add_argument(
        "--end",
        "-E",
        type=int,
        help="Ending GRACE/GRACE-FO month",
    )
    MISSING = [
        6,
        7,
        18,
        109,
        114,
        125,
        130,
        135,
        140,
        141,
        146,
        151,
        156,
        162,
        166,
        167,
        172,
        177,
        178,
        182,
        187,
        188,
        189,
        190,
        191,
        192,
        193,
        194,
        195,
        196,
        197,
        200,
        201,
    ]
    parser.add_argument(
        "--missing",
        "-N",
        metavar="MISSING",
        type=int,
        nargs="+",
        default=MISSING,
        help="Missing GRACE/GRACE-FO months",
    )
    # different treatments of the load Love numbers
    # 0: Han and Wahr (1995) values from PREM
    # 1: Gegout (2005) values from PREM
    # 2: Wang et al. (2012) values from PREM
    # 3: Wang et al. (2012) values from PREM with hard sediment
    # 4: Wang et al. (2012) values from PREM with soft sediment
    parser.add_argument(
        "--love",
        "-n",
        type=int,
        default=0,
        choices=[0, 1, 2, 3, 4],
        help="Treatment of the Load Love numbers",
    )
    # option for setting reference frame for gravitational load love number
    # reference frame options (CF, CM, CE)
    parser.add_argument(
        "--reference",
        type=str.upper,
        default="CF",
        choices=["CF", "CM", "CE"],
        help="Reference frame for load Love numbers",
    )
    # Gaussian smoothing radius (km)
    parser.add_argument(
        "--radius",
        "-R",
        type=float,
        default=0,
        help="Gaussian smoothing radius (km)",
    )
    # Use a decorrelation (destriping) filter
    parser.add_argument(
        "--destripe",
        "-d",
        default=False,
        action="store_true",
        help="Use decorrelation (destriping) filter",
    )
    # output units
    parser.add_argument(
        "--units",
        "-U",
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5],
        help="Output units",
    )
    # output grid parameters
    parser.add_argument(
        "--spacing",
        type=float,
        nargs="+",
        default=[0.5, 0.5],
        metavar=("dlon", "dlat"),
        help="Spatial resolution of output data",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=2,
        choices=[1, 2],
        help=("Output grid interval (1: global, 2: centered global)"),
    )
    # GIA model type list
    models = {}
    models["IJ05-R2"] = "Ivins R2 GIA Models"
    models["W12a"] = "Whitehouse GIA Models"
    models["SM09"] = "Simpson/Milne GIA Models"
    models["ICE6G"] = "ICE-6G GIA Models"
    models["Wu10"] = "Wu (2010) GIA Correction"
    models["AW13-ICE6G"] = "Geruo A ICE-6G GIA Models"
    models["AW13-IJ05"] = "Geruo A IJ05-R2 GIA Models"
    models["Caron"] = "Caron JPL GIA Assimilation"
    models["ICE6G-D"] = "ICE-6G Version-D GIA Models"
    models["ascii"] = "reformatted GIA in ascii format"
    models["netCDF4"] = "reformatted GIA in netCDF4 format"
    models["HDF5"] = "reformatted GIA in HDF5 format"
    # GIA model type
    parser.add_argument(
        "--gia",
        "-G",
        type=str,
        metavar="GIA",
        choices=models.keys(),
        help="GIA model type to read",
    )
    # full path to GIA file
    parser.add_argument(
        "--gia-file",
        type=pathlib.Path,
        help="GIA file to read",
    )
    # use atmospheric jump corrections from Fagiolini et al. (2015)
    parser.add_argument(
        "--atm-correction",
        default=False,
        action="store_true",
        help="Apply atmospheric jump correction coefficients",
    )
    # correct for pole tide drift follow Wahr et al. (2015)
    parser.add_argument(
        "--pole-tide",
        default=False,
        action="store_true",
        help="Correct for pole tide drift",
    )
    # Update Degree 1 coefficients with SLR or derived values
    # Tellus: GRACE/GRACE-FO TN-13 from PO.DAAC
    #     https://grace.jpl.nasa.gov/data/get-data/geocenter/
    # SLR: satellite laser ranging from CSR
    #     ftp://ftp.csr.utexas.edu/pub/slr/geocenter/
    # UCI: Sutterley and Velicogna, Remote Sensing (2019)
    #     https://www.mdpi.com/2072-4292/11/18/2108
    # Swenson: GRACE-derived coefficients from Sean Swenson
    #     https://doi.org/10.1029/2007JB005338
    # GFZ: GRACE/GRACE-FO coefficients from GFZ GravIS
    #     http://gravis.gfz-potsdam.de/corrections
    parser.add_argument(
        "--geocenter",
        metavar="DEG1",
        type=str,
        choices=["Tellus", "SLR", "SLF", "UCI", "Swenson", "GFZ"],
        help="Update Degree 1 coefficients with SLR or derived values",
    )
    parser.add_argument(
        "--geocenter-file",
        type=pathlib.Path,
        help="Specific geocenter file if not default",
    )
    parser.add_argument(
        "--interpolate-geocenter",
        default=False,
        action="store_true",
        help="Least-squares model missing Degree 1 coefficients",
    )
    # replace low degree harmonics with values from Satellite Laser Ranging
    parser.add_argument(
        "--slr-c20",
        type=str,
        default=None,
        choices=["CSR", "GFZ", "GSFC"],
        help="Replace C20 coefficients with SLR values",
    )
    parser.add_argument(
        "--slr-21",
        type=str,
        default=None,
        choices=["CSR", "GFZ", "GSFC"],
        help="Replace C21 and S21 coefficients with SLR values",
    )
    parser.add_argument(
        "--slr-22",
        type=str,
        default=None,
        choices=["CSR", "GSFC"],
        help="Replace C22 and S22 coefficients with SLR values",
    )
    parser.add_argument(
        "--slr-c30",
        type=str,
        default=None,
        choices=["CSR", "GFZ", "GSFC", "LARES"],
        help="Replace C30 coefficients with SLR values",
    )
    parser.add_argument(
        "--slr-c40",
        type=str,
        default=None,
        choices=["CSR", "GSFC", "LARES"],
        help="Replace C40 coefficients with SLR values",
    )
    parser.add_argument(
        "--slr-c50",
        type=str,
        default=None,
        choices=["CSR", "GSFC", "LARES"],
        help="Replace C50 coefficients with SLR values",
    )
    # mean file to remove
    parser.add_argument(
        "--mean-file",
        type=str,
        help="GRACE/GRACE-FO mean file to remove from the harmonic data",
    )
    # input data format for mean file (ascii, netCDF4, HDF5)
    parser.add_argument(
        "--mean-format",
        type=str,
        default="netCDF4",
        choices=["ascii", "netCDF4", "HDF5", "gfc"],
        help="Input data format for GRACE/GRACE-FO mean file",
    )
    # plot range
    parser.add_argument(
        "--plot-range",
        type=float,
        nargs=3,
        metavar=("MIN", "MAX", "STEP"),
        help="Plot range and step size for normalization",
    )
    parser.add_argument(
        "--boundary",
        type=float,
        nargs="+",
        help="Plot boundary for normalization",
    )
    # color palette table or named color map
    try:
        cmap_set = set(cm.datad.keys()) | set(cm.cmaps_listed.keys())
    except (ValueError, NameError) as exc:
        cmap_set = []
    parser.add_argument(
        "--colormap",
        metavar="COLORMAP",
        type=str,
        default="viridis",
        choices=sorted(cmap_set),
        help="Named Matplotlib colormap",
    )
    parser.add_argument(
        "--cpt-file",
        type=pathlib.Path,
        help="Input Color Palette Table (.cpt) file",
    )
    # color map alpha
    parser.add_argument(
        "--alpha",
        type=float,
        default=1.0,
        help="Named Matplotlib colormap",
    )
    # colorbar parameters
    parser.add_argument(
        "--cbextend",
        type=str,
        default="both",
        choices=["neither", "both", "min", "max"],
        help="Add extension triangles to colorbar",
    )
    parser.add_argument(
        "--cbtitle",
        type=str,
        default="",
        help="Title label for colorbar",
    )
    parser.add_argument(
        "--cbunits",
        type=str,
        default="",
        help="Units label for colorbar",
    )
    parser.add_argument(
        "--cbformat",
        type=str,
        default="{0:0.0f}",
        help="Tick format for colorbar",
    )
    # output file format and dpi
    parser.add_argument(
        "--figure-format",
        type=str,
        default="png",
        choices=("pdf", "png", "jpg", "svg"),
        help="Output figure format",
    )
    parser.add_argument(
        "--figure-dpi",
        type=int,
        default=180,
        help="Output figure resolution in dots per inch (dpi)",
    )
    # Output log file for each job in forms
    # validrun_2002-04-01T00:00:00_PID-00000.log
    # failedrun_2002-04-01T00:00:00_PID-00000.log
    parser.add_argument(
        "--log",
        default=False,
        action="store_true",
        help="Output log file for each job",
    )
    # print information about each input and output file
    parser.add_argument(
        "--verbose",
        "-V",
        action="count",
        default=0,
        help="Verbose output of run",
    )
    # permissions mode of the local directories and files (number in octal)
    parser.add_argument(
        "--mode",
        "-M",
        type=lambda x: int(x, base=8),
        default=0o775,
        help="Permissions mode of output files",
    )
    # return the parser
    return parser


# This is the main part of the program that calls the individual functions
def main():
    # Read the system arguments listed after the program
    parser = arguments()
    args, _ = parser.parse_known_args()

    # create logger
    loglevels = [logging.CRITICAL, logging.INFO, logging.DEBUG]
    logger = gravtk.utilities.build_logger(__name__, level=loglevels[args.verbose])

    # try to run the plot program with listed parameters
    try:
        info(args)
        # run plot program with parameters
        output_files = plot_grace(
            args.directory,
            args.center,
            args.release,
            args.product,
            args.lmax,
            args.radius,
            START=args.start,
            END=args.end,
            MISSING=args.missing,
            LMIN=args.lmin,
            MMAX=args.mmax,
            LOVE_NUMBERS=args.love,
            REFERENCE=args.reference,
            DESTRIPE=args.destripe,
            UNITS=args.units,
            GIA=args.gia,
            GIA_FILE=args.gia_file,
            ATM=args.atm_correction,
            POLE_TIDE=args.pole_tide,
            DEG1=args.geocenter,
            DEG1_FILE=args.geocenter_file,
            MODEL_DEG1=args.interpolate_geocenter,
            SLR_C20=args.slr_c20,
            SLR_21=args.slr_21,
            SLR_22=args.slr_22,
            SLR_C30=args.slr_c30,
            SLR_C40=args.slr_c40,
            SLR_C50=args.slr_c50,
            MEAN_FILE=args.mean_file,
            MEANFORM=args.mean_format,
            DDEG=args.spacing,
            INTERVAL=args.interval,
            COLOR_MAP=args.colormap,
            CPT_FILE=args.cpt_file,
            PLOT_RANGE=args.plot_range,
            BOUNDARY=args.boundary,
            ALPHA=args.alpha,
            CBEXTEND=args.cbextend,
            CBTITLE=args.cbtitle,
            CBUNITS=args.cbunits,
            CBFORMAT=args.cbformat,
            OUTPUT_DIRECTORY=args.output_directory,
            FIGURE_FORMAT=args.figure_format,
            FIGURE_DPI=args.figure_dpi,
            MODE=args.mode,
        )
    except Exception as exc:
        # if there has been an error exception
        # print the type, value, and stack trace of the
        # current exception being handled
        logger.critical(f"process id {os.getpid():d} failed")
        logger.error(traceback.format_exc())
        if args.log:  # write failed job completion log file
            logfile = gravtk.utilities.create_log_file(
                "failedrun",
                filename=pathlib.Path(sys.argv[0]).name,
                arguments=vars(args),
            )
            logger.info(logfile)
    else:
        if args.log:  # write successful job completion log file
            logfile = gravtk.utilities.create_log_file(
                "validrun",
                filename=pathlib.Path(sys.argv[0]).name,
                arguments=vars(args),
                output=output_files,
            )
            logger.info(logfile)


# run main program
if __name__ == "__main__":
    main()
