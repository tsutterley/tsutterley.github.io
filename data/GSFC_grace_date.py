#!/usr/bin/env python
u"""
GSFC_grace_date.py
Written by Tyler Sutterley (05/2023)

Reads dates of GSFC GRACE mascon data file and assigns the month number
    reads the start and end date from the filename,
    calculates the mean date in decimal format (correcting for leap years)

COMMAND LINE OPTIONS:
    --help: list the command line options
    -D X, --directory X: working data directory
    -v X, --version X: GSFC GRACE mascon version
    -t X, --timeout X: Timeout in seconds for blocking operations
    -r X, --retry X: Connection retry attempts
    -M X, --mode=X: Local permissions mode of the directories and files synced

PYTHON DEPENDENCIES:
    numpy: Scientific Computing Tools For Python (https://numpy.org)
    h5py: Python interface for Hierarchal Data Format 5 (HDF5)
        (https://h5py.org)
    future: Compatibility layer between Python 2 and Python 3
        (http://python-future.org/)

PROGRAM DEPENDENCIES:
    time.py: utilities for calculating time operations
    utilities.py: download and management utilities for syncing files

UPDATE HISTORY:
    Updated 05/2023: use pathlib to define and operate on paths
    Updated 04/2023: added newer GSFC mascons for RL06v2.0
    Updated 01/2023: single implicit import of gravity toolkit
    Updated 10/2022: added links to newer GSFC mascons Release-6 Version 2.0
    Updated 05/2022: added links to newer GSFC mascons Release-6 Version 2.0
    Updated 02/2022: added links to newer GSFC mascons Release-6 Version 1.0
    Updated 01/2022: added links to newer GSFC mascons Release-6 Version 1.0
    Updated 05/2021: added options for connection timeout and retry attempts
    Updated 03/2021: use python requests to download GSFC mascon file
        added parameters for GSFC mascons Release-6 Version 1.0
    Updated 02/2021: use adjust_months function to fix special months cases
    Updated 12/2020: using utilities from time module.  add version option
    Updated 10/2020: use argparse to set command line parameters
    Updated 03/2020: using getopt to set parameters if run from command line
    Written 07/2018
"""
import sys
import os
import h5py
import inspect
import logging
import pathlib
import requests
import argparse
import posixpath
import numpy as np
import gravity_toolkit as gravtk

# PURPOSE: get GSFC GRACE mascon data
def get_GSFC_grace_mascons(base_dir, TIMEOUT=None, RETRY=5,
    VERSION=None, MODE=0o775):
    # set GRACE parameters
    PROC, DSET = 'GSFC', 'GSM'
    # remote path for mascon versions
    HOST = {}
    HOST['v02.4'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
        'neptune','grace','mascons_2.4','GSFC.glb.200301_201607_v02.4.hdf']
    # HOST['rl06v1.0'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
    #     '2021-03','gsfc.glb_.200204_202009_rl06v1.0_obp-ice6gd.h5']
    # HOST['rl06v1.0'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
    #     '2021-10','gsfc.glb_.200204_202107_rl06v1.0_obp-ice6gd.h5']
    HOST['rl06v1.0'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
        '2022-01','GSFC.glb_.200204_202110_RL06v1.0_OBP-ICE6GD_0.h5']
    # HOST['rl06v2.0'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
    #     '2022-05','gsfc.glb_.200204_202112_rl06v2.0_obp-ice6gd.h5']
    # HOST['rl06v2.0'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
    #     '2022-10','gsfc.glb_.200204_202207_rl06v2.0_obp-ice6gd.h5']
    # HOST['rl06v2.0'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
    #     '2023-03','gsfc.glb_.200204_202211_rl06v2.0_obp-ice6gd.h5']
    HOST['rl06v2.0'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
        'geo','gsfc.glb_.200204_202312_rl06v2.0_obp-ice6gd.h5']
    # local file
    base_dir = pathlib.Path(base_dir).expanduser().absolute()
    local = base_dir.joinpath(PROC,VERSION,DSET,HOST[VERSION][-1])
    # check if the local file exists
    if local.exists():
        return
    # attempt to download up to the number of retries
    retry_counter = 0
    while (retry_counter < RETRY):
        try:
            # get GSFC GRACE mascon file
            from_http(HOST[VERSION], timeout=TIMEOUT, local=local,
                verbose=True, mode=MODE)
        except:
            pass
        else:
            return
        # add to retry counter
        retry_counter += 1
    # check if maximum number of retries were reached
    if (retry_counter == RETRY):
        raise TimeoutError('Maximum number of retries reached')

# PURPOSE: download a file from a http host
def from_http(HOST,timeout=None,local=None,verbose=False,mode=0o775):
    """
    Download a file from a http host

    Arguments
    ---------
    HOST: remote http host path split as list

    Keyword arguments
    -----------------
    timeout: timeout in seconds for blocking operations
    local: path to local file
    verbose: print file transfer information
    mode: permissions mode of output local file
    """
    # get GSFC GRACE mascon file
    req = requests.get(posixpath.join(*HOST), timeout=timeout,
        allow_redirects=True)
    # get last modified time of GRACE mascon file
    last_modified = req.headers['last-modified']
    mtime = gravtk.utilities.get_unix_time(last_modified,
        format='%a, %d %b %Y %H:%M:%S %Z')
    # recursively create local directory if non-existent
    local.parent.mkdir(mode=mode, parents=True, exist_ok=True)
    # print file information
    args = (posixpath.join(*HOST),local)
    print('{0} -->\n\t{1}'.format(*args)) if verbose else None
    with local.open(mode='wb') as f:
        f.write(req.content)
    # keep remote modification time of file and local access time
    os.utime(local, (local.stat().st_atime, mtime))
    # change the permissions mode
    local.chmod(mode=mode)

def GSFC_grace_date(base_dir, VERSION='v02.4', MODE=0o775):
    # set GRACE parameters
    PROC, DSET = 'GSFC', 'GSM'
    # set the GRACE directory
    base_dir = pathlib.Path(base_dir).expanduser().absolute()
    grace_dir = base_dir.joinpath(PROC,VERSION,DSET)
    # dictionary of GSFC GRACE mascon files
    grace_file = {}
    grace_file['v02.4'] = 'GSFC.glb.200301_201607_v02.4.hdf'
    # grace_file['rl06v1.0'] = 'gsfc.glb_.200204_202009_rl06v1.0_obp-ice6gd.h5'
    # grace_file['rl06v1.0'] = 'gsfc.glb_.200204_202107_rl06v1.0_obp-ice6gd.h5'
    grace_file['rl06v1.0'] = 'GSFC.glb_.200204_202110_RL06v1.0_OBP-ICE6GD_0.h5'
    # grace_file['rl06v2.0'] = 'gsfc.glb_.200204_202112_rl06v2.0_obp-ice6gd.h5'
    # grace_file['rl06v2.0'] = 'gsfc.glb_.200204_202207_rl06v2.0_obp-ice6gd.h5'
    # grace_file['rl06v2.0'] = 'gsfc.glb_.200204_202211_rl06v2.0_obp-ice6gd.h5'
    grace_file['rl06v2.0'] = 'gsfc.glb_.200204_202312_rl06v2.0_obp-ice6gd.h5'
    # valid date string (HDF5 attribute: 'days since 2002-01-00T00:00:00')
    date_string = 'days since 2002-01-01T00:00:00'
    epoch,to_secs = gravtk.time.parse_date_string(date_string)
    # dictionary of start, end and mid-dates as Modified Julian Days
    MJD = {}
    # read the HDF5 file
    input_file = grace_dir.joinpath(grace_file[VERSION])
    with h5py.File(input_file, mode='r') as fileID:
        # output HDF5 file information
        logging.info(fileID.filename)
        logging.info(list(fileID.keys()))
        # get GSFC mascon dates
        nmas,nt = fileID['solution']['cmwe'].shape
        # convert from reference days to Modified Julian Days
        for key in ['ref_days_first','ref_days_last','ref_days_middle']:
            MJD[key] = gravtk.time.convert_delta_time(
                to_secs*fileID['time'][key][:].flatten(),
                epoch1=epoch, epoch2=(1858,11,17,0,0,0), scale=1.0/86400.0)

    # convert from Modified Julian Days to calendar days
    start_yr,M1,D1,h1,m1,s1 = gravtk.time.convert_julian(2400000.5 +
        MJD['ref_days_first'], FORMAT='tuple')
    end_yr,M2,D2,h2,m2,s2 = gravtk.time.convert_julian(2400000.5 +
        MJD['ref_days_last'], FORMAT='tuple')
    YY,MM,DD,hh,mm,ss = gravtk.time.convert_julian(2400000.5 +
        MJD['ref_days_middle'], FORMAT='tuple')
    # convert mid-date calendar dates to year-decimal
    tdec = gravtk.time.convert_calendar_decimal(YY,MM,day=DD,
        hour=hh,minute=mm,second=ss)

    # create day of year variables
    start_day = np.zeros((nt))
    end_day = np.zeros((nt))
    # days per month in a leap and a standard year
    # only difference is February (29 vs. 28)
    dpm_leap = np.array([31,29,31,30,31,30,31,31,30,31,30,31], dtype=np.float64)
    dpm_stnd = np.array([31,28,31,30,31,30,31,31,30,31,30,31], dtype=np.float64)
    # create matrix with the lower half = 1
    mon_mat = np.tri(12,12,-1)
    # find indices for standard years and leap years
    lp1, = np.nonzero(((start_yr % 4) == 0))
    sd1, = np.nonzero(((start_yr % 4) != 0))
    lp2, = np.nonzero(((end_yr % 4) == 0))
    sd2, = np.nonzero(((end_yr % 4) != 0))
    # convert from months to months indices
    m1_m1 = np.array(M1, dtype=np.int64) - 1
    m2_m1 = np.array(M2, dtype=np.int64) - 1
    # calculate the day of the year for leap and standard
    # use total days of all months before date
    # and add number of days before date in month
    start_day[sd1] = (D1[sd1]-1) + np.dot(mon_mat[m1_m1[sd1],:],dpm_stnd)
    start_day[lp1] = (D1[lp1]-1) + np.dot(mon_mat[m1_m1[lp1],:],dpm_leap)
    end_day[sd2] = (D2[sd2]-1) + np.dot(mon_mat[m2_m1[sd2],:],dpm_stnd)
    end_day[lp2] = (D2[lp2]-1) + np.dot(mon_mat[m2_m1[lp2],:],dpm_leap)

    # calculate the GRACE month (Apr02 == 004)
    # https://grace.jpl.nasa.gov/data/grace-months/
    # Notes on special months (e.g. 119, 120) below
    grace_month = np.array(12*(YY - 2002) + MM, dtype=np.int64)
    # calculating the month number of 'Special Months' with accelerometer
    # shutoffs is more complicated as days from other months are used
    grace_month = gravtk.time.adjust_months(grace_month)

    # Output GRACE date ascii file
    grace_date_file = grace_dir.joinpath(f'{PROC}_{VERSION}_DATES.txt')
    fid = grace_date_file.open(mode='w', encoding='utf-8')
    # date file header information
    args = ('Mid-date','Month','Start_Day','End_Day','Total_Days')
    print('{0} {1:>10} {2:>11} {3:>10} {4:>13}'.format(*args),file=fid)

    # calculate total number of days since Jan 2002
    tot_days = np.zeros((nt))

    # for each date
    for t,mon in enumerate(grace_month):
        # number of days in the year
        dpy = gravtk.time.calendar_days(start_yr[t]).sum()
        # For data that crosses years
        end_cyclic = (end_yr[t] - start_yr[t])*dpy + end_day[t]
        # Calculation of total days since start of campaign
        count = 0
        n_yrs = np.int64(start_yr[t]-2002)
        # for each of the GRACE years up to the file year
        for iyr in range(n_yrs):
            # year i
            year = 2002 + iyr
            # number of days in year i (if leap year or standard year)
            # add all days from prior years to count
            count += gravtk.time.calendar_days(year).sum()

        # calculating the total number of days since 2002
        tot_days[t] = np.mean([count+start_day[t], count+end_cyclic])

        # print to GRACE DATES ascii file (NOTE: tot_days will be rounded up)
        print(('{0:13.8f} {1:03d} {2:8.0f} {3:03.0f} {4:8.0f} {5:03.0f} '
            '{6:8.0f}').format(tdec[t],mon,start_yr[t],start_day[t],
            end_yr[t],end_day[t],tot_days[t]), file=fid)

    # close date file
    # set permissions level of output date file
    fid.close()
    grace_date_file.chmod(mode=MODE)

# This is the main program that calls the individual modules
def main():
    # Read the system arguments listed after the program
    parser = argparse.ArgumentParser(
        description="""Reads dates of GSFC GRACE mascon data files and assigns
            the month number
            """
    )
    # current file path
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    filepath = pathlib.Path(filename).absolute().parent
    # working data directory
    parser.add_argument('--directory','-D',
        type=pathlib.Path, default=filepath,
        help='Working data directory')
    # GSFC GRACE mascon version
    parser.add_argument('--version','-v',
        type=str, default='rl06v2.0',
        help='GSFC GRACE mascon version')
    # connection timeout and number of retry attempts
    parser.add_argument('--timeout','-t',
        type=int, default=360,
        help='Timeout in seconds for blocking operations')
    parser.add_argument('--retry','-r',
        type=int, default=5,
        help='Connection retry attempts')
    parser.add_argument('--verbose','-V',
        action='count', default=0,
        help='Verbose output of processing run')
    # permissions mode of the local files (number in octal)
    parser.add_argument('--mode','-M',
        type=lambda x: int(x,base=8), default=0o775,
        help='Permission mode of directories and files synced')
    args = parser.parse_args()

    # create logger
    loglevels = [logging.CRITICAL, logging.INFO, logging.DEBUG]
    logging.basicConfig(level=loglevels[args.verbose])

    # get GSFC GRACE mascon data
    get_GSFC_grace_mascons(args.directory, TIMEOUT=args.timeout,
        RETRY=args.retry, VERSION=args.version, MODE=args.mode)
    # run GSFC GRACE mascon date program
    GSFC_grace_date(args.directory, VERSION=args.version, MODE=args.mode)

# run main program
if __name__ == '__main__':
    main()
