#!/usr/bin/env python
"""
grace_months_markdown.py
Written by Tyler Sutterley (10/2020)

Creates a markdown file with the start and end days for each dataset
Shows the range of each month for CSR/GFZ/JPL (RL06) and GSFC (rl06v1.0)
Shows which months are missing for each dataset as **missing**

Similar to ftp://podaac.jpl.nasa.gov/allData/tellus/L3/Doc/GraceMonths.html
    ftp://podaac.jpl.nasa.gov/allData/tellus/L3/Doc/gracemonths_20160112.html

INPUTS:
    base_dir: Working data directory for GRACE/GRACE-FO data

OPTIONS:
    DREL: GRACE/GRACE-FO data release (RL06,rl06v1.0)

OUTPUTS:
    GRACE_months.txt
    Column 1: GRACE Month Number
    Column 2: Calendar Date
    Column 3: CSR RL06 Date Range
    Column 4: GFZ RL06 Date Range
    Column 5: GSFC rl06v1.0 Date Range
    Column 6: JPL RL06 Date Range

COMMAND LINE OPTIONS:
    --help: list the command line options
    -D X, --directory=X: Working GRACE/GRACE-FO data directory
    -R X, --release=X: GRACE/GRACE-FO data releases to run (RL06,rl06v1.0)

PYTHON DEPENDENCIES:
    numpy: Scientific Computing Tools For Python (https://numpy.org)

UPDATE HISTORY:
    Updated 08/2026: forked for markdown table creation
    Updated 03/2021: added options for GSFC Release-6 Version 1.0
    Updated 10/2020: use argparse to set command line parameters
    Updated 09/2020: add link to plain text table
    Updated 08/2020: using git lfs for image storage
    Updated 06/2020: use full calendar years to not require local dependencies
    Updated 03/2020: local import of required dependencies
    Updated 02/2020: add favicon to html header
    Updated 10/2019: no longer show Release-5 data by default
    Updated 06/2019: added notes for GRACE-FO data
    Updated 04/2019: set default releases for each data center
    Updated 07/2018: link images if hovering over a GRACE month for a center
        add navigation side bar and symbols to footer. include Wahr et al. 2015
        added column for GSFC mascon solutions between GFZ and JPL harmonics
    Updated 05/2018: added options for release 6
    Updated 09/2017: added more metadata to output html file
    Updated 05-06/2016: using __future__ print function. format month lines
        Highlight table rows on mouse hover
    Forked 04/2016: forked for HTML table creation
    Updated 03/2016: using getopt to set RL04 parameter, added new help module
        forked for markdown table creation
    Updated 10/2015: cleaned up and added a few comments
    Updated 11/2014: minor updates to code. added main definition
    Updated 10/2014: updated comments, current Sean Geocenter file
    Updated 05/2014: added OPTION to not run RL04
    Updated 07/2013: minor update: new Sean geocenter file
        moved geocenter files to grace.dir/geocenter.dir/
    Updated 05/2013: converted to Python and added years to month label
    Updated 03/2013: changed degree 1 to show both RL04 and RL05
    Updated 02/2013: new degree 1 file from Sean Swenson
        Changed to read from ascii files created from grace_date.pro
    Updated 11/2012: added DEG1 and SLR outputs
    Written 07/2012
"""

from __future__ import print_function

import sys
import inspect
import argparse
import pathlib
import numpy as np
import calendar, time

def element(el, c="tooltip", s="text-align:center"):
    # build element
    cls = f' class="{c}"' if c is not None else ""
    sty = f' style="{s}"' if s is not None else ""
    return f"<{el}{cls}{sty}>"

def close(el):
    return f"</{el}>"

# PURPOSE: create markdown file of GRACE "nominal" months
def grace_months(base_dir, DREL=["RL06", "rl06v1.0"]):
    # verify input path
    base_dir = pathlib.Path(base_dir).expanduser().absolute()
    # directory setup
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    filepath = pathlib.Path(filename).absolute().parent
    content = filepath.parents[1].joinpath("content", "data")
    # Opening output GRACE months markdown file
    output_file = content.joinpath("GRACE-Months.pdc")
    fid = output_file.open("w")

    # Initial parameters
    # processing centers
    PROC = ["CSR", "GFZ", "JPL", "GSFC"]
    # read from GSM datasets
    DSET = "GSM"
    # maximum month of the datasets
    # checks for the maximum month between processing centers
    max_mon = 0
    # contain the information for each dataset
    var_info = {}

    # Looping through data releases first (all RL04 then all RL05)
    # for each considered data release (RL04,RL05)
    for rl in DREL:
        # for each processing centers (CSR, GFZ, JPL)
        for pr in PROC:
            # Setting the data directory for processing center and release
            grace_dir = base_dir.joinpath(pr, rl, DSET)
            # read GRACE date ascii file
            # file created in read_grace.py or grace_dates.py
            grace_date_file = grace_dir.joinpath(f"{pr}_{rl}_DATES.txt")
            if grace_date_file.exists():
                # skip the header line
                date_input = np.loadtxt(grace_date_file, skiprows=1)
                # number of months
                nmon = np.shape(date_input)[0]

                # Setting the dictionary key e.g. 'CSR RL04'
                var_name = f"{pr} {rl}"

                # Creating a python dictionary for each dataset with parameters:
                # month #, start year, start day, end year, end day
                # Purpose is to get all of the dates loaded for each dataset
                # Adding data to dictionary for data processing and release
                var_info[var_name] = {}
                # allocate for output variables
                var_info[var_name]["mon"] = np.zeros((nmon), dtype=int)
                var_info[var_name]["styr"] = np.zeros((nmon), dtype=int)
                var_info[var_name]["stday"] = np.zeros((nmon), dtype=int)
                var_info[var_name]["endyr"] = np.zeros((nmon), dtype=int)
                var_info[var_name]["endday"] = np.zeros((nmon), dtype=int)
                # place output variables in dictionary
                for i, key in enumerate(["mon", "styr", "stday", "endyr", "endday"]):
                    # first column is date in decimal form (start at 1 not 0)
                    var_info[var_name][key] = date_input[:, i + 1].astype(int)
                # Finding the maximum month measured
                if var_info[var_name]["mon"].max() > max_mon:
                    # if the maximum month in this dataset is greater
                    # than the previously read datasets
                    max_mon = int(var_info[var_name]["mon"].max())

    # print markdown headers
    print("---", file=fid)
    print("title: GRACE Months", file=fid)
    print("summary: Date ranges of monthly GRACE/GRACE-FO products", file=fid)
    print("---", file=fid)
    print("", file=fid)

    # print table header
    print(element('table', s=None), file=fid)
    print(element('thead', c=None, s=None), file=fid)
    print(element('tr', c=None, s=None), file=fid)
    print(f"\t{element('th', c=None)}Month{close('th')}", file=fid)
    print(f"\t{element('th', c=None)}Date{close('th')}", file=fid)
    # sort datasets alphanumerically
    var_name = sorted(var_info.keys())
    for v in var_name:
        print(f"\t{element('th', c=None)}{v}{close('th')}", file=fid)
    print(close('tr'), file=fid)
    print(close('thead'), file=fid)
    # print table body
    print(element('tbody', c=None, s=None), file=fid)
    # for each possible month
    # GRACE starts at month 004 (April 2002)
    # max_mon+1 to include max_mon
    for m in range(4, max_mon + 1):
        # finding the month name e.g. Apr
        calendar_year = 2002 + (m - 1) // 12
        calendar_month = (m - 1) % 12 + 1
        month_string = calendar.month_abbr[calendar_month]
        date = f"{month_string}{calendar_year:4d}"
        # printing table lines to file
        print(element('tr', s=None), file=fid)
        print(f"\t{element('td', c='tooltip__dates')}{m:03d}{close('td')}", file=fid)
        print(f"\t{element('td', c=None)}{date}{close('td')}", file=fid)
        # for each processing center and data release
        for var in var_name:
            # split var name for data processing center and release
            PROC, DREL = var.split()
            # find if the month of data exists
            # exists will be greater than 0 if there is a match
            exists = np.count_nonzero(var_info[var]["mon"] == m)
            if exists != 0:
                # if there is a matching month
                # indice of matching month
                (ind,) = np.nonzero(var_info[var]["mon"] == m)
                # start date
                (st_yr,) = var_info[var]["styr"][ind]
                (st_day,) = var_info[var]["stday"][ind]
                # end date
                (end_yr,) = var_info[var]["endyr"][ind]
                (end_day,) = var_info[var]["endday"][ind]
                # output table element is the date range
                # string format: 2002_102--2002_120
                start = f'{st_yr:4d}_{st_day:03d}'
                end = f'{end_yr:4d}_{end_day:03d}'
                print(f"\t{element('td')}{start}&ndash;{end}", file=fid)
                print(f"\t\t{element('span', s=None)}", file=fid)
                src = f"{PROC}-{DREL}-{m:03d}.jpg"
                print(
                    f'\t\t\t<img class="lfs" width="80%" data-path="images/{src}">',
                    file=fid,
                )
                print(f"\t\t{close('span')}", file=fid)
                print(f"\t{close('td')}", file=fid)
            else:
                # if there is no matching month: missing or not yet processed
                missing = r"\*\*missing\*\*"
                print(f"\t{element('td', c='tooltip__missing')}{missing}{close('td')}", file=fid)
        # end of table row
        print(close('tr'), file=fid)
    # print table body footer text
    print(close('tbody'), file=fid)
    print(close('table'), file=fid)

    # print footer text
    today = time.strftime("%Y-%m-%d", time.localtime())
    lineage = pathlib.Path(sys.argv[0]).name
    print('\n\n## Footnotes', file=fid)
    # base processing
    print(
        (
        '- GRACE/GRACE-FO anomalies for harmonic solutions are calculated in ' 
        'reference to the 2003--2010 mean and are smoothed using a '
        '350km radius Gaussian filter [@Wahr:1998hy] after '
        'destriping with a decorrelation algorithm [@Swenson:2006hu]. '
        ),
        file=fid,
    )
    # pole tide drift
    if "RL05" in DREL:
        print(
            (
            'GRACE/GRACE-FO Release-5 products have been corrected for '
            'pole tide drift using coefficients from @Wahr:2015dg. '
            ),
            file=fid,
        )
    # GRACE/GRACE-FO mascon products
    print(
        (
        'GSFC GRACE/GRACE-FO mascon data products are calculated as '
        'described in @Loomis:2019ef. '
        ),
        file=fid,
    )
    # GIA correction
    print(
        (
        'GRACE/GRACE-FO fields have been corrected for '
        'Glacial Isostatic Adjustment (GIA) using coefficients from '
        'ICE6G Version-D [@Peltier:2018dp].'),
        file=fid,
    )
    fid.write(f'- _Generated on {today} with ')
    fid.write(f'[<code>{lineage}</code>]({lineage}){{.links__link}}_\n')
    fid.write(f'- _[Table as plain text](GRACE_months.txt){{.links__link}}_\n')

    # print bibliography text
    print('\n\n## Bibliography\n', file=fid)
    print('---', file=fid)
    print('bibliography: assets/pdc/pub.bib', file=fid)
    print('citation-style: assets/pdc/american-geophysical-union.csl', file=fid)
    print('---', file=fid)
    
    # close output markdown file
    fid.close()


# PURPOSE: functional call to grace_months() if running as program
def main():
    # Read the system arguments listed after the program
    parser = argparse.ArgumentParser(
        description="""Creates a markdown file with the
            start and end days for each dataset
            """
    )
    # command line parameters
    # working data directory
    parser.add_argument(
        "--directory",
        "-D",
        type=pathlib.Path,
        default=pathlib.Path().cwd(),
        help="Working data directory",
    )
    # GRACE/GRACE-FO data release
    parser.add_argument(
        "--release",
        "-r",
        metavar="DREL",
        type=str,
        nargs="+",
        default=["RL06", "rl06v2.0"],
        help="GRACE/GRACE-FO data release",
    )
    args = parser.parse_args()

    # run GRACE/GRACE-FO months program
    grace_months(args.directory, DREL=args.release)


# run main program
if __name__ == "__main__":
    main()
