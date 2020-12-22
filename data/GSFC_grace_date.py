#!/usr/bin/env python
u"""
GSFC_grace_date.py
Written by Tyler Sutterley (12/2020)

Reads dates of GSFC GRACE mascon data file and assigns the month number
    reads the start and end date from the filename,
    calculates the mean date in decimal format (correcting for leap years)

OPTIONS:
    VERSION: GSFC data version
    MODE: Permissions mode of output file

PYTHON DEPENDENCIES:
    numpy: Scientific Computing Tools For Python (https://numpy.org)
    h5py: Python interface for Hierarchal Data Format 5 (HDF5)
        (https://h5py.org)
    future: Compatibility layer between Python 2 and Python 3
        (http://python-future.org/)

PROGRAM DEPENDENCIES:
    time.py: utilities for calculating time operations
    utilities: download and management utilities for syncing files

UPDATE HISTORY:
    Updated 12/2020: using utilities from time module.  add version option
    Updated 10/2020: use argparse to set command line parameters
    Updated 03/2020: using getopt to set parameters if run from command line
    Written 07/2018
"""
import sys
import os
import h5py
import inspect
import argparse
import numpy as np
import gravity_toolkit.time
import gravity_toolkit.utilities

#-- PURPOSE: get GSFC GRACE mascon data
def get_GSFC_grace_mascons(base_dir, VERSION='v02.4', MODE=0o775):
    #-- remote path for mascon versions
    HOST = {}
    HOST['v02.4'] = ['https://earth.gsfc.nasa.gov','sites','default','files',
        'neptune','grace','mascons_2.4','GSFC.glb.200301_201607_v02.4.hdf']
    #-- local file
    local = os.path.join(base_dir,'GSFC',VERSION,'GSM',HOST[VERSION][-1])
    if not os.access(os.path.dirname(local),os.F_OK):
        os.makedirs(os.path.dirname(local),MODE)
    #-- get GSFC GRACE mascon file
    gravity_toolkit.utilities.from_http(HOST[VERSION], local=local,
        verbose=True, mode=MODE)

def GSFC_grace_date(base_dir, VERSION='v02.4', MODE=0o775):
    #-- set the GRACE directory
    grace_dir = os.path.join(base_dir,'GSFC',VERSION,'GSM')
    #-- dictionary of GSFC GRACE mascon files
    grace_file = {}
    grace_file['v02.4'] = 'GSFC.glb.200301_201607_v02.4.hdf'
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
    dpm_leap = np.array([31,29,31,30,31,30,31,31,30,31,30,31], dtype=np.float)
    dpm_stnd = np.array([31,28,31,30,31,30,31,31,30,31,30,31], dtype=np.float)
    #-- create matrix with the lower half = 1
    mon_mat = np.tri(12,12,-1)
    #-- find indices for standard years and leap years
    lp1, = np.nonzero(((start_yr % 4) == 0))
    sd1, = np.nonzero(((start_yr % 4) != 0))
    lp2, = np.nonzero(((end_yr % 4) == 0))
    sd2, = np.nonzero(((end_yr % 4) != 0))
    #-- convert from months to months indices
    m1_m1 = np.array(M1, dtype=np.int) - 1
    m2_m1 = np.array(M2, dtype=np.int) - 1
    #-- calculate the day of the year for leap and standard
    #-- use total days of all months before date
    #-- and add number of days before date in month
    start_day[sd1] = (D1[sd1]-1) + np.dot(mon_mat[m1_m1[sd1],:],dpm_stnd)
    start_day[lp1] = (D1[lp1]-1) + np.dot(mon_mat[m1_m1[lp1],:],dpm_leap)
    end_day[sd2] = (D2[sd2]-1) + np.dot(mon_mat[m2_m1[sd2],:],dpm_stnd)
    end_day[lp2] = (D2[lp2]-1) + np.dot(mon_mat[m2_m1[lp2],:],dpm_leap)

    #-- define date variables
    tot_days = np.zeros((nt))#-- number of days since Jan 2002
    mon = np.zeros((nt),dtype=np.int)#-- GRACE month number

    #-- Output GRACE date ascii file
    grace_date_file = '{0}_{1}_DATES.txt'.format('GSFC', VERSION)
    fid = open(os.path.join(grace_dir,grace_date_file), 'w')
    #-- date file header information
    args = ('Mid-date','Month','Start_Day','End_Day','Total_Days')
    print('{0} {1:>10} {2:>11} {3:>10} {4:>13}'.format(*args),file=fid)

    #-- for each date
    for t in range(nt):
        #-- number of days in the year
        dpy = gravity_toolkit.time.calendar_days(start_yr[t]).sum()
        #-- For data that crosses years
        end_cyclic = (end_yr[t] - start_yr[t])*dpy + end_day[t]
        #-- Calculation of total days since start of campaign
        count = 0
        n_yrs = np.int(start_yr[t]-2002)
        #-- for each of the GRACE years up to the file year
        for iyr in range(n_yrs):
            #-- year i
            year = 2002 + iyr
            #-- number of days in year i (if leap year or standard year)
            #-- add all days from prior years to count
            count += gravity_toolkit.time.calendar_days(year).sum()

        #-- calculating the total number of days since 2002
        tot_days[t] = np.mean([count+start_day[t], count+end_cyclic])

        #-- calculate the GRACE month (Apr02 == 004)
        #-- https://grace.jpl.nasa.gov/data/grace-months/
        #-- Notes on special months (e.g. 119, 120) below
        mon[t] = 12*(YY[t] - 2002) + MM[t]

        #-- calculating the month number of 'Special Months' with accelerometer
        #-- shutoffs is more complicated as days from other months are used
        if (mon[t] == mon[t-1]) and (mon[t-1] == 160):
            mon[t] = mon[t-1] + 1

        #-- print to GRACE DATES ascii file (NOTE: tot_days will be rounded up)
        print(('{0:13.8f} {1:03d} {2:8.0f} {3:03.0f} {4:8.0f} {5:03.0f} '
            '{6:8.0f}').format(tdec[t],mon[t],start_yr[t],start_day[t],
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
        type=str, default='v02.4',
        help='GSFC GRACE mascon version')
    #-- permissions mode of the local files (number in octal)
    parser.add_argument('--mode','-M',
        type=lambda x: int(x,base=8), default=0o775,
        help='Permission mode of directories and files synced')
    args = parser.parse_args()

    #-- get GSFC GRACE mascon data
    get_GSFC_grace_mascons(args.directory, VERSION=args.version, MODE=args.mode)
    #-- run GSFC GRACE mascon date program
    GSFC_grace_date(args.directory, VERSION=args.version, MODE=args.mode)

#-- run main program
if __name__ == '__main__':
    main()
