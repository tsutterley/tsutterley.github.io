#!/usr/bin/env python
u"""
podaac_grace_sync.py
Written by Tyler Sutterley (08/2022)

Syncs GRACE/GRACE-FO and auxiliary data from the NASA JPL PO.DAAC Drive Server
Syncs CSR/GFZ/JPL GSM files for Release-06
Gets the latest technical note (TN) files

https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+Python
https://nsidc.org/support/faq/what-options-are-available-bulk-downloading-data-
    https-earthdata-login-enabled
http://www.voidspace.org.uk/python/articles/authentication.shtml#base64

Register with NASA Earthdata Login system:
https://urs.earthdata.nasa.gov

Add PO.DAAC Drive OPS to NASA Earthdata Applications and get WebDAV Password
https://podaac-tools.jpl.nasa.gov/drive

CALLING SEQUENCE:
    python podaac_grace_sync.py --user <username>
    where <username> is your NASA Earthdata username

OUTPUTS:
    CSR/GFZ/JPL RL06 GSM
    Tellus degree one coefficients (TN-13)
    Technical notes for satellite laser ranging coefficients

COMMAND LINE OPTIONS:
    --help: list the command line options
    -U X, --user X: username for NASA Earthdata Login
    -W X, --webdav X: WebDAV password for JPL PO.DAAC Drive Login
    -N X, --netrc X: path to .netrc file for authentication
    -D X, --directory X: working data directory
    -c X, --center X: GRACE/GRACE-FO Processing Center
    -r X, --release X: GRACE/GRACE-FO Data Releases to sync
    -v X, --version X: GRACE/GRACE-FO Level-2 Data Version to sync
    -t X, --timeout X: Timeout in seconds for blocking operations
    -l, --log: output log of files downloaded
    -M X, --mode X: Local permissions mode of the directories and files synced

PYTHON DEPENDENCIES:
    numpy: Scientific Computing Tools For Python
        https://numpy.org
        https://numpy.org/doc/stable/user/numpy-for-matlab-users.html
    dateutil: powerful extensions to datetime
        https://dateutil.readthedocs.io/en/stable/
    lxml: Pythonic XML and HTML processing library using libxml2/libxslt
        https://lxml.de/
        https://github.com/lxml/lxml
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
import netrc
import shutil
import logging
import argparse
import traceback
import posixpath
import lxml.etree
import multiprocessing as mp
import gravity_toolkit as gravtk

#-- PURPOSE: sync local GRACE/GRACE-FO files with JPL PO.DAAC drive server
def podaac_grace_sync(DIRECTORY, PROC=[], DREL=[], VERSION=[],
    PROCESSES=0, TIMEOUT=360, RETRY=5, LOG=False, MODE=None):

    #-- check if directory exists and recursively create if not
    os.makedirs(DIRECTORY,MODE) if not os.path.exists(DIRECTORY) else None

    #-- remote https server for GRACE data
    HOST = 'https://podaac-tools.jpl.nasa.gov'
    #-- mission shortnames
    shortname = {'grace':'GRAC', 'grace-fo':'GRFO'}
    #-- sync GSM datasets
    DSET = 'GSM'
    #-- compile HTML parser for lxml
    parser = lxml.etree.HTMLParser()

    #-- create log file with list of synchronized files (or print to terminal)
    if LOG:
        #-- format: PODAAC_sync_2002-04-01.log
        LOGFILE = 'PODAAC_sync.log'
        logging.basicConfig(filename=os.path.join(DIRECTORY,LOGFILE),
            level=logging.INFO)
        logging.info('PO.DAAC Sync Log')
        logging.info('CENTERS={0}'.format(','.join(PROC)))
        logging.info('RELEASES={0}'.format(','.join(DREL)))
    else:
        #-- standard output (terminal output)
        logging.basicConfig(level=logging.INFO)

    #-- list of GRACE data files and modification times
    remote_files = []
    remote_mtimes = []
    local_files = []

    #-- SLR C2,0 coefficients
    logging.info('C2,0 Coefficients:')
    PATH = [HOST,'drive','files','allData','grace','docs']
    remote_dir = posixpath.join(*PATH)
    local_dir = os.path.expanduser(DIRECTORY)
    #-- compile regular expression operator for remote files
    R1 = re.compile(r'TN-(05|07|11)_C20_SLR.txt', re.VERBOSE)
    #-- open connection with PO.DAAC drive server at remote directory
    files,mtimes = gravtk.utilities.drive_list(PATH,
        timeout=TIMEOUT,build=False,parser=parser,pattern=R1,sort=True)
    #-- for each file on the remote server
    for colname,remote_mtime in zip(files,mtimes):
        #-- remote and local versions of the file
        remote_files.append(posixpath.join(remote_dir,colname))
        remote_mtimes.append(remote_mtime)
        local_files.append(os.path.join(local_dir,colname))

    #-- SLR C3,0 coefficients
    logging.info('C3,0 Coefficients:')
    PATH = [HOST,'drive','files','allData','gracefo','docs']
    remote_dir = posixpath.join(*PATH)
    local_dir = os.path.expanduser(DIRECTORY)
    #-- compile regular expression operator for remote files
    R1 = re.compile(r'TN-(14)_C30_C20_GSFC_SLR.txt', re.VERBOSE)
    #-- open connection with PO.DAAC drive server at remote directory
    files,mtimes = gravtk.utilities.drive_list(PATH,
        timeout=TIMEOUT,build=False,parser=parser,pattern=R1,sort=True)
    #-- for each file on the remote server
    for colname,remote_mtime in zip(files,mtimes):
        #-- remote and local versions of the file
        remote_files.append(posixpath.join(remote_dir,colname))
        remote_mtimes.append(remote_mtime)
        local_files.append(os.path.join(local_dir,colname))

    #-- GRACE/GRACE-FO level-2 spherical harmonic products
    logging.info('GRACE/GRACE-FO L2 Global Spherical Harmonics:')
    #-- for each processing center (CSR, GFZ, JPL)
    for pr in PROC:
        #-- for each data release (RL04, RL05, RL06)
        for rl in DREL:
            #-- local directory for exact data product
            local_dir = os.path.join(DIRECTORY, pr, rl, DSET)
            #-- check if directory exists and recursively create if not
            if not os.path.exists(local_dir):
                os.makedirs(local_dir,MODE)
            #-- for each satellite mission (grace, grace-fo)
            for i,mi in enumerate(['grace','grace-fo']):
                #-- print string of exact data product
                logging.info('{0} {1}/{2}/{3}'.format(mi, pr, rl, DSET))
                #-- query CMR for dataset
                ids,urls,mtimes = gravtk.utilities.cmr(
                    mission=mi, center=pr, release=rl, product=DSET,
                    version=VERSION[i], provider='PODAAC', endpoint='data')
                #-- for each id, url and modification time
                for id,url,mtime in zip(ids,urls,mtimes):
                    #-- remote and local versions of the file
                    remote_files.append(url)
                    remote_mtimes.append(mtime)
                    granule = gravtk.utilities.url_split(url)[-1]
                    local_files.append(os.path.join(local_dir,granule))

    #-- sync in series if PROCESSES = 0
    if (PROCESSES == 0):
        #-- sync each GRACE/GRACE-FO data file
        for i,remote_file in enumerate(remote_files):
            #-- sync GRACE/GRACE-FO files with PO.DAAC Drive server
            output = http_pull_file(remote_file, remote_mtimes[i],
                local_files[i], TIMEOUT=TIMEOUT, RETRY=RETRY, MODE=MODE)
            #-- print the output string
            logging.info(output)
    else:
        #-- sync in parallel with multiprocessing Pool
        pool = mp.Pool(processes=PROCESSES)
        #-- sync each GRACE/GRACE-FO data file
        out = []
        for i,remote_file in enumerate(remote_files):
            #-- sync GRACE/GRACE-FO files with PO.DAAC Drive server
            args = (remote_file,remote_mtimes[i],local_files[i])
            kwds = dict(TIMEOUT=TIMEOUT, RETRY=RETRY, MODE=MODE)
            out.append(pool.apply_async(multiprocess_sync,args=args,kwds=kwds))
        #-- start multiprocessing jobs
        #-- close the pool
        #-- prevents more tasks from being submitted to the pool
        pool.close()
        #-- exit the completed processes
        pool.join()
        #-- print the output string
        for output in out:
            logging.info(output.get())

    #-- for each processing center (CSR, GFZ, JPL)
    for pr in PROC:
        #-- for each data release (RL04, RL05, RL06)
        for rl in DREL:
            #-- list of GRACE/GRACE-FO files for index
            grace_files = []
            #-- local directory for exact data product
            local_dir = os.path.join(DIRECTORY, pr, rl, DSET)
            #-- for each satellite mission (grace, grace-fo)
            for i,mi in enumerate(['grace','grace-fo']):
                #-- regular expression operator for data product
                rx = gravtk.utilities.compile_regex_pattern(
                    pr, rl, DSET, mission=shortname[mi])
                #-- find local GRACE/GRACE-FO files to create index
                granules = sorted([f for f in os.listdir(local_dir) if rx.match(f)])
                #-- reduce list of GRACE/GRACE-FO files to unique dates
                granules = gravtk.time.reduce_by_date(granules)
                #-- extend list of GRACE/GRACE-FO files with granules
                grace_files.extend(granules)
            #-- outputting GRACE/GRACE-FO filenames to index
            with open(os.path.join(local_dir,'index.txt'),'w') as fid:
                for fi in sorted(grace_files):
                    print('{0}'.format(fi), file=fid)
            #-- change permissions of index file
            os.chmod(os.path.join(local_dir,'index.txt'), MODE)

    #-- close log file and set permissions level to MODE
    if LOG:
        os.chmod(os.path.join(DIRECTORY,LOGFILE), MODE)

#-- PURPOSE: wrapper for running the sync program in multiprocessing mode
def multiprocess_sync(remote_file, remote_mtime, local_file,
    TIMEOUT=0, RETRY=5, MODE=0o775):
    try:
        output = http_pull_file(remote_file,remote_mtime,local_file,
            TIMEOUT=TIMEOUT,RETRY=RETRY,MODE=MODE)
    except Exception as e:
        #-- if there has been an error exception
        #-- print the type, value, and stack trace of the
        #-- current exception being handled
        logging.critical(f'process id {os.getpid():d} failed')
        logging.error(traceback.format_exc())
    else:
        return output

#-- PURPOSE: pull file from a remote host checking if file exists locally
#-- and if the remote file is newer than the local file
def http_pull_file(remote_file, remote_mtime, local_file,
    TIMEOUT=0, RETRY=5, MODE=0o775):
    #-- output string for printing files transferred
    output = '{0} --> \n\t{1}\n'.format(remote_file,local_file)
    #-- chunked transfer encoding size
    CHUNK = 16 * 1024
    #-- attempt to download up to the number of retries
    retry_counter = 0
    while (retry_counter < RETRY):
        #-- attempt to retrieve file from https server
        try:
            #-- Create and submit request.
            #-- There are a wide range of exceptions that can be thrown here
            #-- including HTTPError and URLError.
            request = gravtk.utilities.urllib2.Request(remote_file)
            response = gravtk.utilities.urllib2.urlopen(request,
                timeout=TIMEOUT)
            #-- copy contents to local file using chunked transfer encoding
            #-- transfer should work properly with ascii and binary formats
            with open(local_file, 'wb') as f:
                shutil.copyfileobj(response, f, CHUNK)
        except:
            pass
        else:
            break
        #-- add to retry counter
        retry_counter += 1
    #-- check if maximum number of retries were reached
    if (retry_counter == RETRY):
        raise TimeoutError('Maximum number of retries reached')
    #-- keep remote modification time of file and local access time
    os.utime(local_file, (os.stat(local_file).st_atime, remote_mtime))
    os.chmod(local_file, MODE)
    #-- return the output string
    return output

#-- Main program that calls podaac_grace_sync()
def main():
    #-- Read the system arguments listed after the program
    parser = argparse.ArgumentParser(
        description="""Syncs GRACE/GRACE-FO and auxiliary data from the
            NASA JPL PO.DAAC Drive Server.
            Gets the latest technical note (TN) files.
            """
    )
    #-- command line parameters
    #-- NASA Earthdata credentials
    parser.add_argument('--netrc','-N',
        type=lambda p: os.path.abspath(os.path.expanduser(p)),
        default=os.path.join(os.path.expanduser('~'),'.netrc'),
        help='Path to .netrc file for authentication')
    #-- working data directory
    parser.add_argument('--directory','-D',
        type=lambda p: os.path.abspath(os.path.expanduser(p)),
        default=os.getcwd(),
        help='Working data directory')
    #-- number of processes to run in parallel
    parser.add_argument('--np','-P',
        metavar='PROCESSES', type=int, default=0,
        help='Number of processes to run in parallel')
    #-- GRACE/GRACE-FO processing center
    parser.add_argument('--center','-c',
        metavar='PROC', type=str, nargs='+',
        default=['CSR','GFZ','JPL'], choices=['CSR','GFZ','JPL'],
        help='GRACE/GRACE-FO processing center')
    #-- GRACE/GRACE-FO data release
    parser.add_argument('--release','-r',
        metavar='DREL', type=str, nargs='+',
        default=['RL06'],
        help='GRACE/GRACE-FO data release')
    #-- GRACE/GRACE-FO data version
    parser.add_argument('--version','-v',
        metavar='VERSION', type=str, nargs='+',
        default=['0','1'], choices=['0','1','2','3'],
        help='GRACE/GRACE-FO Level-2 data version')
    #-- connection timeout
    parser.add_argument('--timeout','-t',
        type=int, default=360,
        help='Timeout in seconds for blocking operations')
    #-- Output log file in form PODAAC_sync.log
    parser.add_argument('--log','-l',
        default=False, action='store_true',
        help='Output log file')
    #-- permissions mode of the directories and files synced (number in octal)
    parser.add_argument('--mode','-M',
        type=lambda x: int(x,base=8), default=0o775,
        help='Permission mode of directories and files synced')
    args,_ = parser.parse_known_args()

    #-- JPL PO.DAAC drive hostname
    HOST = 'podaac-tools.jpl.nasa.gov'
    #-- get NASA Earthdata and JPL PO.DAAC drive credentials
    USER,_,PASSWORD = netrc.netrc(args.netrc).authenticators(HOST)
    #-- build a urllib opener for PO.DAAC Drive
    #-- Add the username and password for NASA Earthdata Login system
    gravtk.utilities.build_opener(USER,PASSWORD)

    #-- check internet connection before attempting to run program
    #-- check JPL PO.DAAC Drive credentials before attempting to run program
    DRIVE = 'https://{0}/drive/files'.format(HOST)
    if gravtk.utilities.check_credentials(DRIVE):
        podaac_grace_sync(args.directory, PROC=args.center,
            DREL=args.release, VERSION=args.version,
            PROCESSES=args.np, TIMEOUT=args.timeout,
            LOG=args.log, MODE=args.mode)

#-- run main program
if __name__ == '__main__':
    main()
