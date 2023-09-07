#!/usr/bin/env python
u"""
podaac_cumulus.py
Written by Tyler Sutterley (09/2023)

Syncs GRACE/GRACE-FO data from NASA JPL PO.DAAC Cumulus AWS S3 bucket
S3 Cumulus syncs are only available in AWS instances in us-west-2

Register with NASA Earthdata Login system:
https://urs.earthdata.nasa.gov

CALLING SEQUENCE:
    python podaac_cumulus.py --user <username>
    where <username> is your NASA Earthdata username

OUTPUTS:
    CSR RL06: GAC/GAD/GSM
    GFZ RL06: GAA/GAB/GAC/GAD/GSM
    JPL RL06: GAA/GAB/GAC/GAD/GSM
    GFZ RL06: Level-1b dealiasing solutions

COMMAND LINE OPTIONS:
    --help: list the command line options
    -U X, --user X: username for NASA Earthdata Login
    -W X, --password X: password for NASA Earthdata Login
    -N X, --netrc X: path to .netrc file for authentication
    -D X, --directory X: working data directory
    -c X, --center X: GRACE/GRACE-FO Processing Center
    -r X, --release X: GRACE/GRACE-FO Data Releases to sync
    -v X, --version X: GRACE/GRACE-FO Level-2 Data Version to sync
    -t X, --timeout X: Timeout in seconds for blocking operations
    --gzip, -G: Compress output GRACE/GRACE-FO Level-2 granules
    -l, --log: output log of files downloaded
    -M X, --mode X: Local permissions mode of the directories and files synced

PYTHON DEPENDENCIES:
    numpy: Scientific Computing Tools For Python
        https://numpy.org
        https://numpy.org/doc/stable/user/numpy-for-matlab-users.html
    dateutil: powerful extensions to datetime
        https://dateutil.readthedocs.io/en/stable/
    boto3: Amazon Web Services (AWS) SDK for Python
        https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
    future: Compatibility layer between Python 2 and Python 3
        https://python-future.org/

PROGRAM DEPENDENCIES:
    time.py: utilities for calculating time operations
    utilities.py: download and management utilities for syncing files
"""
from __future__ import print_function

import sys
import os
import re
import gzip
import time
import shutil
import logging
import pathlib
import argparse
import traceback
import multiprocessing as mp
import gravity_toolkit as gravtk

# PURPOSE: sync local GRACE/GRACE-FO files with JPL PO.DAAC AWS bucket
def podaac_cumulus(DIRECTORY, PROC=[], DREL=[], VERSION=[],
    PROCESSES=0, TIMEOUT=360, RETRY=5, GZIP=False, LOG=False, MODE=None):

    # check if directory exists and recursively create if not
    DIRECTORY = pathlib.Path(DIRECTORY).expanduser().absolute()
    DIRECTORY.mkdir(mode=MODE, parents=True, exist_ok=True)

    # mission shortnames
    shortname = {'grace':'GRAC', 'grace-fo':'GRFO'}
    # sync GSM datasets
    DSET = 'GSM'
    suffix = '.gz' if GZIP else ''

    # create log file with list of synchronized files (or print to terminal)
    if LOG:
        # format: PODAAC_sync_2002-04-01.log
        today = time.strftime('%Y-%m-%d',time.localtime())
        LOGFILE = DIRECTORY.joinpath(f'PODAAC_sync_{today}.log')
        logging.basicConfig(filename=LOGFILE, level=logging.INFO)
        logging.info(f'PO.DAAC Cumulus Sync Log ({today})')
        logging.info('CENTERS={0}'.format(','.join(PROC)))
        logging.info('RELEASES={0}'.format(','.join(DREL)))
    else:
        # standard output (terminal output)
        logging.basicConfig(level=logging.INFO)

    # list of GRACE data files and modification times
    remote_files = []
    remote_mtimes = []
    local_files = []

    # Degree 1 (geocenter) coefficients
    logging.info('Degree 1 Coefficients:')
    # SLR C2,0 and C3,0 coefficients
    logging.info('C2,0 and C3,0 Coefficients:')
    # compile regular expression operator for remote files
    R1 = re.compile(r'TN-13_GEOC_(CSR|GFZ|JPL)_(.*?).txt', re.VERBOSE)
    R2 = re.compile(r'TN-(14)_C30_C20_GSFC_SLR.txt', re.VERBOSE)
    # check if geocenter directory exists and recursively create if not
    local_dir = DIRECTORY.joinpath('geocenter')
    local_dir.mkdir(mode=MODE, parents=True, exist_ok=True)
    # current time stamp to use for local files
    mtime = time.time()
    # for each processing center (CSR, GFZ, JPL)
    for pr in PROC:
        # for each data release (RL04, RL05, RL06)
        for rl in DREL:
            # for each unique version of data to sync
            for version in set(VERSION):
                # query CMR for product metadata
                urls = gravtk.utilities.cmr_metadata(
                    mission='grace-fo', center=pr, release=rl,
                    version=version, provider='POCLOUD',
                    endpoint='data')
                # verify that urls exist
                if not urls:
                    continue
                # TN-13 JPL degree 1 files
                url, = [url for url in urls if R1.search(url)]
                granule = gravtk.utilities.url_split(url)[-1]
                local_file = local_dir.joinpath(granule)
                # access auxiliary data from endpoint
                http_pull_file(url, mtime, local_file,
                    TIMEOUT=TIMEOUT, GZIP=False, MODE=MODE)
                # TN-14 SLR C2,0 and C3,0 files
                url, = [url for url in urls if R2.search(url)]
                granule = gravtk.utilities.url_split(url)[-1]
                local_file = DIRECTORY.joinpath(granule)
                # access auxiliary data from endpoint
                http_pull_file(url, mtime, local_file,
                    TIMEOUT=TIMEOUT, GZIP=False, MODE=MODE)

    # GRACE/GRACE-FO level-2 spherical harmonic products
    logging.info('GRACE/GRACE-FO L2 Global Spherical Harmonics:')
    # for each processing center (CSR, GFZ, JPL)
    for pr in PROC:
        # for each data release (RL04, RL05, RL06)
        for rl in DREL:
            # local directory for exact data product
            local_dir = DIRECTORY.joinpath(pr, rl, DSET)
            # check if directory exists and recursively create if not
            local_dir.mkdir(mode=MODE, parents=True, exist_ok=True)
            # for each satellite mission (grace, grace-fo)
            for i,mi in enumerate(['grace','grace-fo']):
                # print string of exact data product
                logging.info(f'{mi} {pr}/{rl}/{DSET}')
                # query CMR for dataset
                ids,urls,mtimes = gravtk.utilities.cmr(
                    mission=mi, center=pr, release=rl, product=DSET,
                    version=VERSION[i], provider='POCLOUD', endpoint='data')
                # for each model id and url
                for id,url,mtime in zip(ids,urls,mtimes):
                    # remote and local versions of the file
                    remote_files.append(url)
                    remote_mtimes.append(mtime)
                    granule = gravtk.utilities.url_split(url)[-1]
                    local_files.append(local_dir.joinpath(f'{granule}{suffix}'))

    # sync in series if PROCESSES = 0
    if (PROCESSES == 0):
        # sync each GRACE/GRACE-FO data file
        for i,remote_file in enumerate(remote_files):
            # sync GRACE/GRACE-FO files with PO.DAAC Drive server
            output = http_pull_file(remote_file, remote_mtimes[i],
                local_files[i], TIMEOUT=TIMEOUT, RETRY=RETRY,
                GZIP=GZIP, MODE=MODE)
            # print the output string
            logging.info(output)
    else:
        # sync in parallel with multiprocessing Pool
        pool = mp.Pool(processes=PROCESSES)
        # sync each GRACE/GRACE-FO data file
        out = []
        for i,remote_file in enumerate(remote_files):
            # sync GRACE/GRACE-FO files with PO.DAAC Drive server
            args = (remote_file,remote_mtimes[i],local_files[i])
            kwds = dict(TIMEOUT=TIMEOUT, RETRY=RETRY, GZIP=GZIP, MODE=MODE)
            out.append(pool.apply_async(multiprocess_sync,args=args,kwds=kwds))
        # start multiprocessing jobs
        # close the pool
        # prevents more tasks from being submitted to the pool
        pool.close()
        # exit the completed processes
        pool.join()
        # print the output string
        for output in out:
            logging.info(output.get())

    # for each processing center (CSR, GFZ, JPL)
    for pr in PROC:
        # for each data release (RL04, RL05, RL06)
        for rl in DREL:
            # list of GRACE/GRACE-FO files for index
            grace_files = []
            # local directory for exact data product
            local_dir = DIRECTORY.joinpath(pr, rl, DSET)
            # for each satellite mission (grace, grace-fo)
            for i,mi in enumerate(['grace','grace-fo']):
                # regular expression operator for data product
                rx = gravtk.utilities.compile_regex_pattern(
                    pr, rl, DSET, mission=shortname[mi])
                # find local GRACE/GRACE-FO files to create index
                granules = sorted([f.name for f in local_dir.iterdir()
                    if rx.match(f.name)])
                # reduce list of GRACE/GRACE-FO files to unique dates
                granules = gravtk.time.reduce_by_date(granules)
                # extend list of GRACE/GRACE-FO files with granules
                grace_files.extend(granules)
            # outputting GRACE/GRACE-FO filenames to index
            index_file = local_dir.joinpath('index.txt')
            with index_file.open('w', encoding='utf8') as fid:
                for grace_file in sorted(grace_files):
                    print(grace_file, file=fid)
            # change permissions of index file
            index_file.chmod(mode=MODE)

    # close log file and set permissions level to MODE
    if LOG:
        LOGFILE.chmod(mode=MODE)

# PURPOSE: wrapper for running the sync program in multiprocessing mode
def multiprocess_sync(remote_file, remote_mtime, local_file,
    TIMEOUT=0, RETRY=5, GZIP=False, MODE=0o775):
    try:
        output = http_pull_file(remote_file,remote_mtime,local_file,
            TIMEOUT=TIMEOUT,RETRY=RETRY,GZIP=GZIP,MODE=MODE)
    except Exception as e:
        # if there has been an error exception
        # print the type, value, and stack trace of the
        # current exception being handled
        logging.critical(f'process id {os.getpid():d} failed')
        logging.error(traceback.format_exc())
    else:
        return output

# PURPOSE: pull file from a remote host checking if file exists locally
# and if the remote file is newer than the local file
def http_pull_file(remote_file, remote_mtime, local_file,
    TIMEOUT=0, RETRY=5, GZIP=False, MODE=0o775):
    # output string for printing files transferred
    local_file = pathlib.Path(local_file)
    output = f'{remote_file} --> \n\t{str(local_file)}\n'
    # chunked transfer encoding size
    CHUNK = 16 * 1024
    # attempt to download up to the number of retries
    retry_counter = 0
    while (retry_counter < RETRY):
        # attempt to retrieve file from https server
        try:
            # Create and submit request.
            # There are a wide range of exceptions that can be thrown here
            # including HTTPError and URLError.
            request = gravtk.utilities.urllib2.Request(remote_file)
            response = gravtk.utilities.urllib2.urlopen(request,
                timeout=TIMEOUT)
            # copy contents to local file using chunked transfer encoding
            # transfer should work properly with ascii and binary formats
            if GZIP:
                with gzip.GzipFile(local_file, 'wb', 9, None, remote_mtime) as f:
                    shutil.copyfileobj(response, f)
            else:
                with local_file.open(mode='wb') as f:
                    shutil.copyfileobj(response, f, CHUNK)
        except:
            pass
        else:
            break
        # add to retry counter
        retry_counter += 1
    # check if maximum number of retries were reached
    if (retry_counter == RETRY):
        raise TimeoutError('Maximum number of retries reached')
    # keep remote modification time of file and local access time
    os.utime(local_file, (local_file.stat().st_atime, remote_mtime))
    local_file.chmod(mode=MODE)
    # return the output string
    return output

# PURPOSE: create argument parser
def arguments():
    parser = argparse.ArgumentParser(
        description="""Syncs GRACE/GRACE-FO and auxiliary data from the
            NASA JPL PO.DAAC Cumulus AWS bucket data endpoint.
            """
    )
    # command line parameters
    # NASA Earthdata credentials
    parser.add_argument('--user','-U',
        type=str, default=os.environ.get('EARTHDATA_USERNAME'),
        help='Username for NASA Earthdata Login')
    parser.add_argument('--password','-W',
        type=str, default=os.environ.get('EARTHDATA_PASSWORD'),
        help='Password for NASA Earthdata Login')
    parser.add_argument('--netrc','-N',
        type=pathlib.Path,
        default=pathlib.Path.home().joinpath('.netrc'),
        help='Path to .netrc file for authentication')
    # working data directory
    parser.add_argument('--directory','-D',
        type=pathlib.Path, default=pathlib.Path.cwd(),
        help='Working data directory')
    # number of processes to run in parallel
    parser.add_argument('--np','-P',
        metavar='PROCESSES', type=int, default=0,
        help='Number of processes to run in parallel')
    # GRACE/GRACE-FO processing center
    parser.add_argument('--center','-c',
        metavar='PROC', type=str, nargs='+',
        default=['CSR','GFZ','JPL'], choices=['CSR','GFZ','JPL'],
        help='GRACE/GRACE-FO processing center')
    # GRACE/GRACE-FO data release
    parser.add_argument('--release','-r',
        metavar='DREL', type=str, nargs='+',
        default=['RL06'], choices=['RL06'],
        help='GRACE/GRACE-FO data release')
    # GRACE/GRACE-FO data version
    parser.add_argument('--version','-v',
        metavar='VERSION', type=str, nargs=2,
        default=['0','1'], choices=['0','1','2','3'],
        help='GRACE/GRACE-FO Level-2 data version')
    # connection timeout
    parser.add_argument('--timeout','-t',
        type=int, default=360,
        help='Timeout in seconds for blocking operations')
    # output compressed files
    parser.add_argument('--gzip','-G',
        default=False, action='store_true',
        help='Compress output GRACE/GRACE-FO Level-2 granules')
    # Output log file in form
    # PODAAC_sync_2002-04-01.log
    parser.add_argument('--log','-l',
        default=False, action='store_true',
        help='Output log file')
    # permissions mode of the directories and files synced (number in octal)
    parser.add_argument('--mode','-M',
        type=lambda x: int(x,base=8), default=0o775,
        help='Permission mode of directories and files synced')
    # return the parser
    return parser

# This is the main part of the program that calls the individual functions
def main():
    # Read the system arguments listed after the program
    parser = arguments()
    args,_ = parser.parse_known_args()

    # NASA Earthdata hostname
    URS = 'urs.earthdata.nasa.gov'
    # There are a range of exceptions that can be thrown here
    # including HTTPError and URLError.
    opener = gravtk.utilities.attempt_login(URS,
        username=args.user, password=args.password,
        netrc=args.netrc, authorization_header=False)

    # retrieve data objects from AWS data endpoint
    podaac_cumulus(args.directory, PROC=args.center,
        DREL=args.release, VERSION=args.version,
        PROCESSES=args.np, TIMEOUT=args.timeout,
        GZIP=args.gzip, LOG=args.log, MODE=args.mode)

# run main program
if __name__ == '__main__':
    main()
