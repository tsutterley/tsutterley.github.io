#!/usr/bin/env python
u"""
nasa_earthdata_nsidc_example.py (06/2018)
Modified for use with the NSIDC Servers from
https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+Python

Register with NASA Earthdata Login system:
https://urs.earthdata.nasa.gov

Add NSIDC_DATAPOOL_OPS to NASA Earthdata Applications
https://urs.earthdata.nasa.gov/oauth/authorize?client_id=_JLuwMHxb2xX6NwYTb4dRA

UPDATE HISTORY:
    Updated 06/2018: using python3 compatible octal, input and urllib
    Updated 05/2018: added checksum example to test data file transfer validity
    Written 05/2017
"""
from __future__ import print_function

import sys
import os
import shutil
import base64
import getopt
import getpass
import hashlib
import builtins
import posixpath
import lxml.etree
if sys.version_info[0] == 2:
    from cookielib import CookieJar
    import urllib2
else:
    from http.cookiejar import CookieJar
    import urllib.request as urllib2

#-- PURPOSE: check internet connection
def check_connection():
    #-- attempt to connect to https host for NSIDC
    try:
        urllib2.urlopen('https://n5eil01u.ecs.nsidc.org/',timeout=20)
    except urllib2.URLError:
        raise RuntimeError('Check internet connection')
    else:
        return True

#-- PURPOSE: example script for retrieving Icebridge elevation data from NSIDC
def nasa_earthdata_nsidc_example(USER='', PASSWORD=''):
    #-- https://docs.python.org/3/howto/urllib2.html#id5
    #-- create a password manager
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    #-- Add the username and password for NASA Earthdata Login system
    password_mgr.add_password(None, 'https://urs.earthdata.nasa.gov',
        USER, PASSWORD)
    #-- Encode username/password for request authorization headers
    base64_string = base64.b64encode('{0}:{1}'.format(USER, PASSWORD))
    #-- Create cookie jar for storing cookies. This is used to store and return
    #-- the session cookie given to use by the data server (otherwise will just
    #-- keep sending us back to Earthdata Login to authenticate).
    cookie_jar = CookieJar()
    #-- create "opener" (OpenerDirector instance)
    opener = urllib2.build_opener(
        urllib2.HTTPBasicAuthHandler(password_mgr),
        #urllib2.HTTPHandler(debuglevel=1),  # Uncomment these two lines to see
        #urllib2.HTTPSHandler(debuglevel=1), # details of the requests/responses
        urllib2.HTTPCookieProcessor(cookie_jar))
    #-- add Authorization header to opener
    opener.addheaders = [("Authorization", "Basic {0}".format(base64_string))]
    #-- Now all calls to urllib2.urlopen use our opener.
    urllib2.install_opener(opener)
    #-- All calls to urllib2.urlopen will now use handler
    #-- Make sure not to include the protocol in with the URL, or
    #-- HTTPPasswordMgrWithDefaultRealm will be confused.

    #-- NSIDC https server
    HOST = 'https://n5eil01u.ecs.nsidc.org'
    #-- example file to download from NSIDC
    FILE = 'ILATM2_20090331_122747_smooth_nadir3seg_50pt.csv'
    #-- remote path to example file
    remote_file=posixpath.join(HOST,"ICEBRIDGE","ILATM2.002","2009.03.31",FILE)

    #-- Create and submit request adding authorization header.
    #-- There are a wide range of exceptions that can be thrown here
    #-- including HTTPError and URLError.
    request = urllib2.Request(remote_file)
    response = urllib2.urlopen(request)

    #-- Printing file transferred
    print('{0} -->\n\t{1}\n'.format(remote_file,os.path.realpath(FILE)))

    #-- copy contents to local file using chunked transfer encoding
    #-- transfer should work properly for both ascii and binary data formats
    CHUNK = 16 * 1024
    with open(FILE, 'wb') as f:
        shutil.copyfileobj(response, f, CHUNK)

    #-- run compare checksum program for data file
    compare_checksum('{0}.xml'.format(remote_file), FILE, True)
    #-- close request
    request = None

#-- PURPOSE: compare the checksum in the remote xml file with the local hash
def compare_checksum(remote_xml, local_file, verbose):
    #-- read and parse remote xml file
    req = urllib2.Request(remote_xml)
    #-- compile xml parser for lxml
    xmlparser = lxml.etree.XMLParser()
    tree = lxml.etree.parse(urllib2.urlopen(req,timeout=20),xmlparser)
    filename, = tree.xpath('//DataFileContainer/DistributedFileName/text()')
    #-- if the DistributedFileName matches the synced filename
    if (os.path.basename(local_file) == filename):
        #-- extract checksum and checksum type of the remote file
        checksum_type, = tree.xpath('//DataFileContainer/ChecksumType/text()')
        remote_hash, = tree.xpath('//DataFileContainer/Checksum/text()')
        #-- calculate checksum of local file
        local_hash = get_checksum(local_file, checksum_type)
        #-- compare local and remote checksums to validate data transfer
        if (local_hash != remote_hash):
            if verbose:
                print('Remote checksum: {0}'.format(remote_hash))
                print('Local checksum: {0}' .format(local_hash))
            raise Exception('Checksum verification failed')
        elif (local_hash == remote_hash) and verbose:
            print('{0} checksum match: {1}'.format(checksum_type,local_hash))

#-- PURPOSE: generate checksum hash from a local file for a checksum type
#-- supplied hashes within NSIDC *.xml files can currently be MD5 and CKSUM
#-- https://nsidc.org/data/icebridge/provider_info.html
def get_checksum(local_file, checksum_type):
    #-- read the input file to get file information
    fd = os.open(local_file, os.O_RDONLY)
    n = os.fstat(fd).st_size
    #-- open the filename in binary read mode
    file_buffer = os.fdopen(fd, 'rb').read()
    #-- generate checksum hash for a given type
    if (checksum_type == 'MD5'):
        return hashlib.md5(file_buffer).hexdigest()
    elif (checksum_type == 'CKSUM'):
        crc32_table = []
        for b in range(0,256):
            vv = b<<24
            for i in range(7,-1,-1):
                vv = (vv<<1)^0x04c11db7 if (vv & 0x80000000) else (vv<<1)
            crc32_table.append(vv & 0xffffffff)
        #-- calculate CKSUM hash with both file length and file buffer
        i = c = s = 0
        for c in file_buffer:
            s = ((s << 8) & 0xffffffff)^crc32_table[(s >> 24)^ord(c)]
        while n:
            c = n & 0xff
            n = n >> 8
            s = ((s << 8) & 0xffffffff)^crc32_table[(s >> 24)^c]
        return str((~s) & 0xffffffff)
    elif (checksum_type == 'CRC32'):
        crc32_table = []
        for b in range(256):
            vv = b
            for i in range(8):
                vv = (vv>>1)^0xedb88320 if (vv & 1) else (vv>>1)
            crc32_table.append(vv & 0xffffffff)
        s = 0xffffffff
        for c in file_buffer:
            s = crc32_table[(ord(c) ^ s) & 0xff] ^ (s >> 8)
        return str((~s) & 0xffffffff)

#-- PURPOSE: help module to describe the optional input parameters
def usage():
    print('\nHelp: {0}'.format(os.path.basename(sys.argv[0])))
    print(' -U X, --user=X\t\tUsername for NASA Earthdata Login\n')

#-- Main program that calls nasa_earthdata_nsidc_example()
def main():
    #-- Read the system arguments listed after the program
    optlist,arglist = getopt.getopt(sys.argv[1:],'hU:',['help','user='])

    #-- NASA Earthdata credentials used to authenticate access to data
    #-- Register with NASA Earthdata system: https://urs.earthdata.nasa.gov
    USER = ""
    for opt, arg in optlist:
        if opt in ("-h","--help"):
            usage()
            sys.exit()
        elif opt in ("-U","--user"):
            USER = arg

    #-- NASA Earthdata hostname
    HOST = 'urs.earthdata.nasa.gov'
    #-- check that NASA Earthdata credentials were entered
    if not USER:
        USER = builtins.input('Username for {0}: '.format(HOST))
    #-- enter password securely from command-line
    PASSWORD = getpass.getpass('Password for {0}@{1}: '.format(USER,HOST))

    #-- check internet connection before attempting to run program
    if check_connection():
        nasa_earthdata_nsidc_example(USER=USER, PASSWORD=PASSWORD)

#-- run main program
if __name__ == '__main__':
    main()
