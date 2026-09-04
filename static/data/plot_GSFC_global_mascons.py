#!/usr/bin/env python
"""
plot_GSFC_global_mascons.py
Written by Tyler Sutterley (09/2026)
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
    Updated 09/2026: switch from parameter files to argparse arguments
        use upstream file logger for verbose output
        use pathlib to define and operate on paths
        place some imports behind try/except statements
        added color palette table (cpt) file reader from tools
    Updated 11/2024: automatically parse for latest GSFC mascon file
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
import re
import h5py
import copy
import argparse
import logging
import pathlib
import traceback
import numpy as np
import gravity_toolkit as gravtk
from GSFC_grace_date import GSFC_mascon_list

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
    import matplotlib.patches as patches
    from matplotlib.collections import PatchCollection

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


# plot mascon program
def plot_mascon(
    base_dir,
    PROC,
    DREL,
    DSET,
    RANGE=None,
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

    # import GRACE file
    # set the GRACE directory
    grace_dir = os.path.join(base_dir, PROC, DREL, DSET)
    # query for the HDF5 file (as list)
    URL = GSFC_mascon_list(DREL)
    grace_file = URL[-1]
    # valid date string (HDF5 attribute: 'days since 2002-01-00T00:00:00')
    date_string = "days since 2002-01-01T00:00:00"
    epoch, to_secs = gravtk.time.parse_date_string(date_string)
    # read the HDF5 file
    with h5py.File(os.path.join(grace_dir, grace_file), "r") as fileID:
        nmas, nt = fileID["solution"]["cmwe"].shape
        cmwe = fileID["solution"]["cmwe"][:, :].copy()
        lat_center = fileID["mascon"]["lat_center"][:].flatten()
        lon_center = fileID["mascon"]["lon_center"][:].flatten()
        lat_span = fileID["mascon"]["lat_span"][:].flatten()
        lon_span = fileID["mascon"]["lon_span"][:].flatten()
        julian = 2452275.5 + fileID["time"]["ref_days_middle"][:].flatten()
        MJD = gravtk.time.convert_delta_time(
            to_secs * fileID["time"]["ref_days_middle"][:].flatten(),
            epoch1=epoch,
            epoch2=(1858, 11, 17, 0, 0, 0),
            scale=1.0 / 86400.0,
        )
    # sign to convert from center to patch
    lon_sign = np.array(
        [-0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 0.5, 0.3, 0.1, -0.1, -0.3, -0.5, -0.5]
    )
    lat_sign = np.array(
        [-0.5, -0.5, -0.5, -0.5, -0.5, -0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, -0.5]
    )
    # convert to -180:180
    lon_center = np.where(lon_center > 180, lon_center - 360.0, lon_center)

    # convert Julian days to calendar days
    cal_date = gravtk.time.convert_julian(MJD + 2400000.5)
    # calculate the GRACE month (Apr02 == 004)
    # https://grace.jpl.nasa.gov/data/grace-months/
    # Notes on special months (e.g. 119, 120) below
    grace_month = gravtk.time.calendar_to_grace(
        cal_date["year"], month=cal_date["month"]
    )
    # calculating the month number of 'Special Months' with accelerometer
    # shutoffs is more complicated as days from other months are used
    grace_month = gravtk.time.adjust_months(grace_month)

    # use a mean range for the static field to remove
    MEAN = np.zeros((nmas))
    if RANGE is not None:
        ind = np.flatnonzero((grace_month >= RANGE[0]) & (grace_month <= RANGE[-1]))
        for i in range(nmas):
            MEAN[i] = np.mean(cmwe[i, ind])

    # read CPT or use color map
    if CPT_FILE is not None:
        # cpt file
        cmap = gravtk.tools.from_cpt(CPT_FILE)
    else:
        # colormap
        cmap = plt.get_cmap(COLOR_MAP).copy()
    # grey color map for bad values
    cmap.set_bad("w", 0.5)

    # setup Plate Carree map
    projection = ccrs.PlateCarree()
    fig, ax1 = plt.subplots(
        num=1, figsize=(5.5, 3.5), subplot_kw=dict(projection=projection)
    )

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

    # polygon and colors
    poly_list = []
    data = np.zeros((nmas))
    # for each shape entity
    for i in range(nmas):
        if lat_center[i] == 90.0:  # NH polar mascon
            points = np.zeros((10, 2))
            points[:, 0] = lon_center[i] + np.linspace(0, 360, 10)
            points[:, 1] = lat_center[i] - lat_span[i] * np.ones((10))
        if lat_center[i] == -90.0:  # SH polar mascon
            points = np.zeros((10, 2))
            points[:, 0] = lon_center[i] + np.linspace(0, 360, 10)
            points[:, 1] = lat_center[i] + lat_span[i] * np.ones((10))
        else:
            # extract lat/lon coordinates for mascon
            points = np.zeros((13, 2))
            points[:, 0] = lon_center[i] + lon_sign * lon_span[i]
            points[:, 1] = lat_center[i] + lat_sign * lat_span[i]
        # add mascon lat/lon to polygon list
        poly_list.append(patches.Polygon(list(zip(points[:, 0], points[:, 1]))))
    # add patch collection with color map
    p = PatchCollection(poly_list, cmap=cmap, alpha=ALPHA)
    p.set_array(data)
    p.set_edgecolor(cmap(norm(data)))
    p.set_norm(norm)
    ax1.add_collection(p)

    # draw coastlines
    ax1.coastlines("50m", linewidth=0.5)

    # Add horizontal colorbar for GRACE magnitude and adjust size
    # add extension triangles to upper and lower bounds
    # pad = distance from main plot axis
    # shrink = percent size of colorbar
    # aspect = lengthXwidth aspect of colorbar
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(
        sm,
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

    # set x and y limits
    ax1.set_xlim(-180, 180)
    ax1.set_ylim(-90, 90)
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

    # for each date
    for t, mon in enumerate(grace_month):
        # data for time with mean removed
        data = cmwe[:, t] - MEAN
        # set colors for patch
        p.set_array(data)
        p.set_edgecolor(cmap(norm(data)))
        # add date label (year-calendar month e.g. 2002-01)
        args = (cal_date["year"][t], cal_date["month"][t])
        time_text.set_text(r"\textbf{{{0:4.0f}--{1:02.0f}}}".format(*args))
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
        help="GRACE/GRACE-FO mascon product",
    )
    # start and end months for mean
    parser.add_argument(
        "--mean",
        "-m",
        metavar=("START", "END"),
        type=int,
        nargs=2,
        default=[4, 108],
        help="Start and end months for mean",
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
        output_files = plot_mascon(
            args.directory,
            args.center,
            args.release,
            args.product,
            RANGE=args.mean,
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
