#!/usr/bin/env python
u"""
GSFC_grace_date.py
Written by Tyler Sutterley (02/2022)

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
import requests
import argparse
import posixpath
import numpy as np
import gravity_toolkit.time
import gravity_toolkit.utilities

#-- PURPOSE: get GSFC GRACE mascon data
def get_GSFC_grace_mascons(base_dir, TIMEOUT=None, RETRY=5,
    VERSION=None, MODE=0o775):
    #-- remote path for mascon versions
    HOST = {}
    HOST['v02.4'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
        'neptune','grace','mascons_2.4','GSFC.glb.200301_201607_v02.4.hdf']
    # HOST['rl06v1.0'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
    #     '2021-03','gsfc.glb_.200204_202009_rl06v1.0_sla-ice6gd.h5']
    # HOST['rl06v1.0'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
    #     '2021-10','gsfc.glb_.200204_202107_rl06v1.0_sla-ice6gd.h5']
    HOST['rl06v1.0'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
        '2022-01','GSFC.glb_.200204_202110_RL06v1.0_SLA-ICE6GD_0.h5']
    HOST['rl06v2.0'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
        '2022-05','gsfc.glb_.200204_202112_rl06v2.0_sla-ice6gd.h5']
    #-- local file
    local = os.path.join(base_dir,'GSFC',VERSION,'GSM',HOST[VERSION][-1])
    #-- attempt to download up to the number of retries
    retry_counter = 0
    while (retry_counter < RETRY):
        try:
            #-- get GSFC GRACE mascon file
            from_http(HOST[VERSION], timeout=TIMEOUT, local=local,
                verbose=True, mode=MODE)
        except:
            pass
        else:
            return
        #-- add to retry counter
        retry_counter += 1
    #-- check if maximum number of retries were reached
    if (retry_counter == RETRY):
        raise TimeoutError('Maximum number of retries reached')

#-- PURPOSE: download a file from a http host
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
    #-- get GSFC GRACE mascon file
    req = requests.get(posixpath.join(*HOST), timeout=timeout,
        allow_redirects=True)
    #-- get last modified time of GRACE mascon file
    last_modified = req.headers['last-modified']
    mtime = gravity_toolkit.utilities.get_unix_time(last_modified,
        format='%a, %d %b %Y %H:%M:%S %Z')
    #-- recursively create local directory if non-existent
    if not os.access(os.path.dirname(local),os.F_OK):
        os.makedirs(os.path.dirname(local),mode)
    #-- print file information
    args = (posixpath.join(*HOST),local)
    print('{0} -->\n\t{1}'.format(*args)) if verbose else None
    with open(local, 'wb') as f:
        f.write(req.content)
    #-- keep remote modification time of file and local access time
    os.utime(local, (os.stat(local).st_atime, mtime))
    #-- change the permissions mode
    os.chmod(local, mode)

def GSFC_grace_date(base_dir, VERSION='v02.4', MODE=0o775):
    #-- set the GRACE directory
    grace_dir = os.path.join(base_dir,'GSFC',VERSION,'GSM')
    #-- dictionary of GSFC GRACE mascon files
    grace_file = {}
    grace_file['v02.4'] = 'GSFC.glb.200301_201607_v02.4.hdf'
    # grace_file['rl06v1.0'] = 'gsfc.glb_.200204_202009_rl06v1.0_sla-ice6gd.h5'
    # grace_file['rl06v1.0'] = 'gsfc.glb_.200204_202107_rl06v1.0_sla-ice6gd.h5'
    grace_file['rl06v1.0'] = 'GSFC.glb_.200204_202110_RL06v1.0_SLA-ICE6GD_0.h5'
    grace_file['rl06v2.0'] = 'gsfc.glb_.200204_202112_rl06v2.0_sla-ice6gd.h5'
    #-- valid date string (HDF5 attribute: 'days since 2002-01-00T00:00:00')
    date_string = 'days since 2002-01-01T00:00:00'
    epoch,to_secs = gravity_toolkit.time.parse_date_string(date_string)
    #-- dictionary of start, end and mid-dates as Modified Julian Days
    MJD = {}
    #-- read the HDF5 file
    with h5py.File(os.path.join(grace_dir,grace_file[VERSION]),'r') as fileID:
        nmas,nt = fileID['solution']['cmwe'].shape
        #-- convert from reference days to Modified Julian Days
        for key in ['ref_days_first','ref_days_last','ref_days_middle']:
            MJD[key] = gravity_toolkit.time.convert_delta_time(
                to_secs*fileID['time'][key][:].flatten(),
                epoch1=epoch, epoch2=(1858,11,17,0,0,0), scale=1.0/86400.0)

    #-- convert from Modified Julian Days to calendar days
    start_yr,M1,D1,h1,m1,s1 = gravity_toolkit.time.convert_julian(2400000.5 +
        MJD['ref_days_first'], FORMAT='tuple')
    end_yr,M2,D2,h2,m2,s2 = gravity_toolkit.time.convert_julian(2400000.5 +
        MJD['ref_days_last'], FORMAT='tuple')
    YY,MM,DD,hh,mm,ss = gravity_toolkit.time.convert_julian(2400000.5 +
        MJD['ref_days_middle'], FORMAT='tuple')
    #-- convert mid-date calendar dates to year-decimal
    tdec = gravity_toolkit.time.convert_calendar_decimal(YY,MM,day=DD,
        hour=hh,minute=mm,second=ss)

    #-- create day of year variables
    start_day = np.zeros((nt))
    end_day = np.zeros((nt))
    #-- days per month in a leap and a standard year
    #-- only difference is February (29 vs. 28)
    dpm_leap = np.array([31,29,31,30,31,30,31,31,30,31,30,31], dtype=np.float64)
    dpm_stnd = np.array([31,28,31,30,31,30,31,31,30,31,30,31], dtype=np.float64)
    #-- create matrix with the lower half = 1
    mon_mat = np.tri(12,12,-1)
    #-- find indices for standard years and leap years
    lp1, = np.nonzero(((start_yr % 4) == 0))
    sd1, = np.nonzero(((start_yr % 4) != 0))
    lp2, = np.nonzero(((end_yr % 4) == 0))
    sd2, = np.nonzero(((end_yr % 4) != 0))
    #-- convert from months to months indices
    m1_m1 = np.array(M1, dtype=np.int64) - 1
    m2_m1 = np.array(M2, dtype=np.int64) - 1
    #-- calculate the day of the year for leap and standard
    #-- use total days of all months before date
    #-- and add number of days before date in month
    start_day[sd1] = (D1[sd1]-1) + np.dot(mon_mat[m1_m1[sd1],:],dpm_stnd)
    start_day[lp1] = (D1[lp1]-1) + np.dot(mon_mat[m1_m1[lp1],:],dpm_leap)
    end_day[sd2] = (D2[sd2]-1) + np.dot(mon_mat[m2_m1[sd2],:],dpm_stnd)
    end_day[lp2] = (D2[lp2]-1) + np.dot(mon_mat[m2_m1[lp2],:],dpm_leap)

    #-- calculate the GRACE month (Apr02 == 004)
    #-- https://grace.jpl.nasa.gov/data/grace-months/
    #-- Notes on special months (e.g. 119, 120) below
    grace_month = np.array(12*(YY - 2002) + MM, dtype=np.int64)
    #-- calculating the month number of 'Special Months' with accelerometer
    #-- shutoffs is more complicated as days from other months are used
    grace_month = gravity_toolkit.time.adjust_months(grace_month)

    #-- Output GRACE date ascii file
    grace_date_file = '{0}_{1}_DATES.txt'.format('GSFC', VERSION)
    fid = open(os.path.join(grace_dir,grace_date_file), 'w')
    #-- date file header information
    args = ('Mid-date','Month','Start_Day','End_Day','Total_Days')
    print('{0} {1:>10} {2:>11} {3:>10} {4:>13}'.format(*args),file=fid)

    #-- calculate total number of days since Jan 2002
    tot_days = np.zeros((nt))

    #-- for each date
    for t,mon in enumerate(grace_month):
        #-- number of days in the year
        dpy = gravity_toolkit.time.calendar_days(start_yr[t]).sum()
        #-- For data that crosses years
        end_cyclic = (end_yr[t] - start_yr[t])*dpy + end_day[t]
        #-- Calculation of total days since start of campaign
        count = 0
        n_yrs = np.int64(start_yr[t]-2002)
        #-- for each of the GRACE years up to the file year
        for iyr in range(n_yrs):
            #-- year i
            year = 2002 + iyr
            #-- number of days in year i (if leap year or standard year)
            #-- add all days from prior years to count
            count += gravity_toolkit.time.calendar_days(year).sum()

        #-- calculating the total number of days since 2002
        tot_days[t] = np.mean([count+start_day[t], count+end_cyclic])

        #-- print to GRACE DATES ascii file (NOTE: tot_days will be rounded up)
        print(('{0:13.8f} {1:03d} {2:8.0f} {3:03.0f} {4:8.0f} {5:03.0f} '
            '{6:8.0f}').format(tdec[t],mon,start_yr[t],start_day[t],
            end_yr[t],end_day[t],tot_days[t]), file=fid)

    #-- close date file
    #-- set permissions level of output date file
    fid.close()
    os.chmod(os.path.join(grace_dir, grace_date_file), MODE)

#-- This is the main program that calls the individual modules
def main():
    #-- Read the system arguments listed after the program
    parser = argparse.ArgumentParser(
        description="""Reads dates of GSFC GRACE mascon data files and assigns
            the month number
            """
    )
    #-- current file path
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    filepath = os.path.dirname(os.path.abspath(filename))
    #-- working data directory
    parser.add_argument('--directory','-D',
        type=lambda p: os.path.abspath(os.path.expanduser(p)), default=filepath,
        help='Working data directory')
    #-- GSFC GRACE mascon version
    parser.add_argument('--version','-v',
        type=str, default='rl06v2.0',
        help='GSFC GRACE mascon version')
    #-- connection timeout and number of retry attempts
    parser.add_argument('--timeout','-t',
        type=int, default=360,
        help='Timeout in seconds for blocking operations')
    parser.add_argument('--retry','-r',
        type=int, default=5,
        help='Connection retry attempts')
    #-- permissions mode of the local files (number in octal)
    parser.add_argument('--mode','-M',
        type=lambda x: int(x,base=8), default=0o775,
        help='Permission mode of directories and files synced')
    args = parser.parse_args()

    #-- get GSFC GRACE mascon data
    get_GSFC_grace_mascons(args.directory, TIMEOUT=args.timeout,
        RETRY=args.retry, VERSION=args.version, MODE=args.mode)
    #-- run GSFC GRACE mascon date program
    GSFC_grace_date(args.directory, VERSION=args.version, MODE=args.mode)

#-- run main program
if __name__ == '__main__':
    main()
