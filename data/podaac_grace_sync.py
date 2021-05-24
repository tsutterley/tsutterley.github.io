#!/usr/bin/env python
u"""
podaac_grace_sync.py
Written by Tyler Sutterley (05/2021)

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

OUTPUTS:
    CSR/GFZ/JPL RL06 GSM
    Tellus degree one coefficients (TN-13)
    Technical notes for satellite laser ranging coefficients

COMMAND LINE OPTIONS:
    --help: list the command line options
    -N X, --netrc X: path to .netrc file for authentication
    -D X, --directory X: working data directory
    -C X, --center X: GRACE Processing Center
    -R X, --release X: GRACE data releases to sync (RL06)
    -l, --log: output log of files downloaded
    -M X, --mode X: Local permissions mode of the directories and files synced

PYTHON DEPENDENCIES:
    lxml: Pythonic XML and HTML processing library using libxml2/libxslt
        https://lxml.de/
        https://github.com/lxml/lxml
    future: Compatibility layer between Python 2 and Python 3
        https://python-future.org/

PROGRAM DEPENDENCIES:
    utilities.py: download and management utilities for syncing files
"""
from __future__ import print_function

import sys
import os
import re
import netrc
import shutil
import argparse
import traceback
import posixpath
import lxml.etree
import multiprocessing as mp
import gravity_toolkit.utilities

#-- PURPOSE: create and compile regular expression operator to find GRACE files
def compile_regex_pattern(PROC, DREL, DSET):
    if ((DSET == 'GSM') and (PROC == 'CSR') and (DREL in ('RL04','RL05'))):
        #-- CSR GSM: only monthly degree 60 products
        #-- not the longterm degree 180, degree 96 dataset or the
        #-- special order 30 datasets for the high-resonance months
        release, = re.findall(r'\d+', DREL)
        args = (DSET, int(release))
        regex_pattern=r'{0}-2_\d+-\d+_\d+_UTCSR_0060_000{1:d}.gz$' .format(*args)
    elif ((DSET == 'GSM') and (PROC == 'CSR') and (DREL == 'RL06')):
        #-- CSR GSM RL06: only monthly degree 60 products
        release, = re.findall(r'\d+', DREL)
        args = (DSET, '(GRAC|GRFO)', 'BA01', int(release))
        regex_pattern=r'{0}-2_\d+-\d+_{1}_UTCSR_{2}_0{3:d}00.gz$' .format(*args)
    elif ((DSET == 'GSM') and (PROC == 'GFZ') and (DREL == 'RL04')):
        #-- GFZ RL04: only unconstrained solutions (not GK2 products)
        regex_pattern=r'{0}-2_\d+-\d+_\d+_EIGEN_G---_0004.gz$'.format(DSET)
    elif ((DSET == 'GSM') and (PROC == 'GFZ') and (DREL == 'RL05')):
        #-- GFZ RL05: updated RL05a products which are less constrained to
        #-- the background model.  Allow regularized fields
        regex_unconst=r'{0}-2_\d+-\d+_\d+_EIGEN_G---_005a.gz$'.format(DSET)
        regex_regular=r'{0}-2_\d+-\d+_\d+_EIGEN_GK2-_005a.gz$'.format(DSET)
        regex_pattern=r'{0}|{1}'.format(regex_unconst,regex_regular)
    elif ((DSET == 'GSM') and (PROC == 'GFZ') and (DREL == 'RL06')):
        #-- GFZ GSM RL06: only monthly degree 60 products
        release, = re.findall(r'\d+', DREL)
        args = (DSET, '(GRAC|GRFO)', 'BA01', int(release))
        regex_pattern=r'{0}-2_\d+-\d+_{1}_GFZOP_{2}_0{3:d}00.gz$' .format(*args)
    elif (PROC == 'JPL') and DREL in ('RL04','RL05'):
        #-- JPL: RL04a and RL05a products (denoted by 0001)
        release, = re.findall(r'\d+', DREL)
        args = (DSET, int(release))
        regex_pattern=r'{0}-2_\d+-\d+_\d+_JPLEM_0001_000{1:d}.gz$'.format(*args)
    elif ((DSET == 'GSM') and (PROC == 'JPL') and (DREL == 'RL06')):
        #-- JPL GSM RL06: only monthly degree 60 products
        release, = re.findall(r'\d+', DREL)
        args = (DSET, '(GRAC|GRFO)', 'BA01', int(release))
        regex_pattern=r'{0}-2_\d+-\d+_{1}_JPLEM_{2}_0{3:d}00.gz$' .format(*args)
    else:
        regex_pattern=r'{0}-2_(.*?).gz$'.format(DSET)
    #-- return the compiled regular expression operator used to find files
    return re.compile(regex_pattern, re.VERBOSE)

#-- PURPOSE: sync local GRACE/GRACE-FO files with JPL PO.DAAC drive server
def podaac_grace_sync(DIRECTORY,PROC,DREL=[],PROCESSES=0,TIMEOUT=360,RETRY=5,
    LOG=False,MODE=None):

    #-- check if directory exists and recursively create if not
    os.makedirs(DIRECTORY,MODE) if not os.path.exists(DIRECTORY) else None

    #-- remote https server for GRACE data
    HOST = 'https://podaac-tools.jpl.nasa.gov'
    #-- sync GSM datasets
    DSET = 'GSM'
    #-- compile HTML parser for lxml
    parser = lxml.etree.HTMLParser()

    #-- create log file with list of synchronized files (or print to terminal)
    if LOG:
        #-- format: PODAAC_sync.log
        LOGFILE = 'PODAAC_sync.log'
        fid1 = open(os.path.join(DIRECTORY,LOGFILE),'w')
        print('PO.DAAC Sync Log', file=fid1)
        print('CENTERS={0}'.format(','.join(PROC)), file=fid1)
        print('RELEASES={0}'.format(','.join(DREL)), file=fid1)
    else:
        #-- standard output (terminal output)
        fid1 = sys.stdout

    #-- list of GRACE data files and modification times
    remote_files = []
    remote_mtimes = []
    local_files = []

    #-- SLR C2,0 COEFFICIENTS
    PATH = [HOST,'drive','files','allData','grace','docs']
    remote_dir = posixpath.join(*PATH)
    local_dir = os.path.expanduser(DIRECTORY)
    #-- compile regular expression operator for remote files
    R1 = re.compile(r'TN-(05|07|11)_C20_SLR.txt', re.VERBOSE)
    #-- open connection with PO.DAAC drive server at remote directory
    files,mtimes = gravity_toolkit.utilities.drive_list(PATH,
        timeout=TIMEOUT,build=False,parser=parser,pattern=R1,sort=True)
    #-- for each file on the remote server
    for colname,remote_mtime in zip(files,mtimes):
        #-- remote and local versions of the file
        remote_files.append(posixpath.join(remote_dir,colname))
        remote_mtimes.append(remote_mtime)
        local_files.append(os.path.join(local_dir,colname))

    #-- SLR C3,0 COEFFICIENTS
    PATH = [HOST,'drive','files','allData','gracefo','docs']
    remote_dir = posixpath.join(*PATH)
    local_dir = os.path.expanduser(DIRECTORY)
    #-- compile regular expression operator for remote files
    R1 = re.compile(r'TN-(14)_C30_C20_GSFC_SLR.txt', re.VERBOSE)
    #-- open connection with PO.DAAC drive server at remote directory
    files,mtimes = gravity_toolkit.utilities.drive_list(PATH,
        timeout=TIMEOUT,build=False,parser=parser,pattern=R1,sort=True)
    #-- for each file on the remote server
    for colname,remote_mtime in zip(files,mtimes):
        #-- remote and local versions of the file
        remote_files.append(posixpath.join(remote_dir,colname))
        remote_mtimes.append(remote_mtime)
        local_files.append(os.path.join(local_dir,colname))

    #-- GRACE DATA
    #-- PROCESSING CENTERS (CSR, GFZ, JPL)
    for pr in PROC:
        PATH = [HOST,'drive','files','allData','grace']
        #-- DATA RELEASES (RL06)
        for rl in DREL:
            #-- modifiers for intermediate data releases
            if (pr == 'JPL') and (rl in ('RL04','RL05')):
                #-- JPL RELEASE 4 = RL04.1
                #-- JPL RELEASE 5 = RL05.1 (11/2014)
                drel_str = '{0}.1'.format(rl)
            else:
                drel_str = rl
            #-- remote directory for data release
            PATH.extend(['L2',pr,drel_str])
            remote_dir = posixpath.join(*PATH)
            #-- open connection with PO.DAAC drive server at remote directory
            colnames,mtimes = gravity_toolkit.utilities.drive_list(PATH,
                timeout=TIMEOUT,build=False,parser=parser,sort=True)
            #-- local directory for exact data product
            local_dir = os.path.join(DIRECTORY, pr, rl, DSET)
            #-- check if directory exists and recursively create if not
            if not os.path.exists(local_dir):
                os.makedirs(local_dir,MODE)
            #-- compile regular expression operator to find GRACE files
            R1 = re.compile(r'({0}-(.*?)(gz|txt|dif))'.format(DSET),re.VERBOSE)
            line = [i for i,f in enumerate(colnames) if R1.match(f)]
            #-- for each file on the remote server
            for i in line:
                #-- remote and local versions of the file
                remote_files.append(posixpath.join(remote_dir,colnames[i]))
                remote_mtimes.append(mtimes[i])
                local_files.append(os.path.join(local_dir,colnames[i]))

    #-- GRACE-FO DATA
    #-- PROCESSING CENTERS (CSR, GFZ, JPL)
    #-- GRACE-FO data are stored separately for each year
    for pr in PROC:
        PATH = [HOST,'drive','files','allData','gracefo']
        #-- DATA RELEASES (RL06)
        valid_gracefo_releases = [d for d in DREL if d not in ('RL04','RL05')]
        for rl in valid_gracefo_releases:
            #-- remote directory for data release
            PATH.extend(['L2',pr,rl])
            #-- open connection with PO.DAAC drive server at remote directory
            R2 = re.compile(r'\d{4}',re.VERBOSE)
            years,mtimes = gravity_toolkit.utilities.drive_list(PATH,
                timeout=TIMEOUT,build=False,parser=parser,pattern=R2,sort=True)
            for yr in years:
                #-- add the year directory to the path
                PATH.append(yr)
                remote_dir = posixpath.join(*PATH)
                #-- open connection with PO.DAAC drive server at remote directory
                colnames,mtimes=gravity_toolkit.utilities.drive_list(PATH,
                    timeout=TIMEOUT,build=False,parser=parser,sort=True)
                #-- local directory for exact data product
                local_dir = os.path.join(DIRECTORY, pr, rl, DSET)
                #-- check if directory exists and recursively create if not
                if not os.path.exists(local_dir):
                    os.makedirs(local_dir,MODE)
                #-- compile regular expression operator to find GRACE files
                R1 = re.compile(r'({0}-(.*?)(gz|txt|dif))'.format(DSET))
                line = [i for i,f in enumerate(colnames) if R1.match(f)]
                #-- for each file on the remote server
                for i in line:
                    #-- remote and local versions of the file
                    remote_files.append(posixpath.join(remote_dir,colnames[i]))
                    remote_mtimes.append(mtimes[i])
                    local_files.append(os.path.join(local_dir,colnames[i]))
                #-- remove the year directory to the path
                PATH.remove(yr)

    #-- sync in series if PROCESSES = 0
    if (PROCESSES == 0):
        #-- sync each GRACE/GRACE-FO data file
        for i,remote_file in enumerate(remote_files):
            #-- sync GRACE/GRACE-FO files with PO.DAAC Drive server
            output = http_pull_file(remote_file, remote_mtimes[i],
                local_files[i], TIMEOUT=TIMEOUT, RETRY=RETRY, MODE=MODE)
            #-- print the output string
            print(output, file=fid1)
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
            print(output.get(), file=fid1)

    #-- create index file for GRACE/GRACE-FO L2 Spherical Harmonic Data
    #-- PROCESSING CENTERS (CSR, GFZ, JPL)
    for pr in PROC:
        #-- DATA RELEASES (RL06)
        for rl in DREL:
            #-- DATA PRODUCTS (GSM)
            #-- local directory for exact data product
            local_dir = os.path.join(DIRECTORY, pr, rl, DSET)
            #-- Create an index file for each GRACE product
            #-- finding all dataset files *.gz in directory
            rx = compile_regex_pattern(pr, rl, DSET)
            #-- find local GRACE files to create index
            grace_files=[fi for fi in os.listdir(local_dir) if rx.match(fi)]
            #-- outputting GRACE filenames to index
            with open(os.path.join(local_dir,'index.txt'),'w') as fid:
                for fi in sorted(grace_files):
                    print('{0}'.format(fi), file=fid)
            #-- change permissions of index file
            os.chmod(os.path.join(local_dir,'index.txt'), MODE)

    #-- close log file and set permissions level to MODE
    if LOG:
        fid1.close()
        os.chmod(os.path.join(DIRECTORY,LOGFILE), MODE)

#-- PURPOSE: wrapper for running the sync program in multiprocessing mode
def multiprocess_sync(remote_file, remote_mtime, local_file,
    TIMEOUT=0, RETRY=5, MODE=0o775):
    try:
        output = http_pull_file(remote_file,remote_mtime,local_file,
            TIMEOUT=TIMEOUT,RETRY=RETRY,MODE=MODE)
    except:
        #-- if there has been an error exception
        #-- print the type, value, and stack trace of the
        #-- current exception being handled
        print('process id {0:d} failed'.format(os.getpid()))
        traceback.print_exc()
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
            request = gravity_toolkit.utilities.urllib2.Request(remote_file)
            response = gravity_toolkit.utilities.urllib2.urlopen(request,
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
        default=['RL06'], choices=['RL04','RL05','RL06'],
        help='GRACE/GRACE-FO data release')
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
    args = parser.parse_args()

    #-- JPL PO.DAAC drive hostname
    HOST = 'podaac-tools.jpl.nasa.gov'
    #-- get NASA Earthdata and JPL PO.DAAC drive credentials
    USER,_,PASSWORD = netrc.netrc(args.netrc).authenticators(HOST)
    #-- build a urllib opener for PO.DAAC Drive
    #-- Add the username and password for NASA Earthdata Login system
    gravity_toolkit.utilities.build_opener(USER,PASSWORD)

    #-- check internet connection before attempting to run program
    #-- check JPL PO.DAAC Drive credentials before attempting to run program
    if gravity_toolkit.utilities.check_credentials():
        podaac_grace_sync(args.directory, args.center, DREL=args.release,
            PROCESSES=args.np, TIMEOUT=args.timeout, LOG=args.log,
            MODE=args.mode)


#-- run main program
if __name__ == '__main__':
    main()
