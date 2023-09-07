#!/usr/bin/env python
u"""
get_podaac_webdav.py
Written by Tyler Sutterley (01/2023)

Retrieves and prints a user's PO.DAAC WebDAV credentials to a netrc file

https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+Python
https://nsidc.org/support/faq/what-options-are-available-bulk-downloading-data-
    https-earthdata-login-enabled
http://www.voidspace.org.uk/python/articles/authentication.shtml#base64

Register with NASA Earthdata Login system:
https://urs.earthdata.nasa.gov

Add PO.DAAC Drive OPS to NASA Earthdata Applications and get WebDAV Password
https://podaac-tools.jpl.nasa.gov/drive

CALLING SEQUENCE:
    python get_podaac_webdav.py --user=<username> --password=<password>
    where <username> and <password> are your NASA Earthdata credentials

OUTPUTS:
    PODAAC WebDAV credentials

COMMAND LINE OPTIONS:
    --help: list the command line options
    -U X, --user X: username for NASA Earthdata Login
    -P X, --password X: password for NASA Earthdata Login
    -W X, --webdav X: WebDAV password for JPL PO.DAAC Drive Login

PYTHON DEPENDENCIES:
    lxml: Pythonic XML and HTML processing library using libxml2/libxslt
        https://lxml.de/
        https://github.com/lxml/lxml
    future: Compatibility layer between Python 2 and Python 3
        https://python-future.org/

PROGRAM DEPENDENCIES:
    utilities.py: download and management utilities for syncing files

UPDATE HISTORY:
    Updated 01/2023: single implicit import of gravity toolkit
    Updated 03/2021: default credentials from environmental variables
    Updated 10/2020: use argparse to set command line parameters
    Written 05/2020 for public release
"""
from __future__ import print_function

import sys
import os
import netrc
import base64
import inspect
import builtins
import argparse
import posixpath
import lxml.etree
import gravity_toolkit as gravtk

#-- PURPOSE: retrieve PO.DAAC Drive WebDAV credentials
def podaac_webdav(USER, PASSWORD, parser=lxml.etree.HTMLParser()):
    #-- build opener for retrieving PO.DAAC Drive WebDAV credentials
    #-- Add the username and password for NASA Earthdata Login system
    URS = 'https://urs.earthdata.nasa.gov'
    gravtk.utilities.build_opener(USER, PASSWORD,
        password_manager=True, authorization_header=True, urs=URS)
    #-- All calls to urllib2.urlopen will now use handler
    #-- Make sure not to include the protocol in with the URL, or
    #-- HTTPPasswordMgrWithDefaultRealm will be confused.
    HOST = posixpath.join('https://podaac-tools.jpl.nasa.gov','drive')
    parameters = gravtk.utilities.urlencode(
        {'client_id':'lRY01RPdFZ2BKR77Mv9ivQ', 'response_type':'code',
        'state':base64.b64encode(HOST.encode()),
        'redirect_uri':posixpath.join(HOST,'authenticated'),
        'required_scope': 'country+study_area'}
    )
    #-- retrieve cookies from NASA Earthdata URS
    request = gravtk.utilities.urllib2.Request(
        url=posixpath.join(URS,'oauth','authorize?{0}'.format(parameters)))
    gravtk.utilities.urllib2.urlopen(request)
    #-- read and parse request for webdav password
    request = gravtk.utilities.urllib2.Request(url=HOST)
    response = gravtk.utilities.urllib2.urlopen(request, timeout=20)
    tree = lxml.etree.parse(response, parser)
    WEBDAV, = tree.xpath('//input[@id="password"]/@value')
    #-- return webdav password
    return WEBDAV

#-- Main program that calls podaac_webdav()
def main():
    #-- Read the system arguments listed after the program
    parser = argparse.ArgumentParser(
        description="""Retrieves and prints a user's PO.DAAC WebDAV credentials
            """
    )
    #-- command line parameters
    #-- NASA Earthdata credentials
    parser.add_argument('--user','-U',
        type=str, default=os.environ.get('EARTHDATA_USERNAME'),
        help='Username for NASA Earthdata Login')
    parser.add_argument('--password','-P',
        type=str, default=os.environ.get('EARTHDATA_PASSWORD'),
        help='Password for NASA Earthdata Login')
    parser.add_argument('--webdav','-W',
        type=str, default=os.environ.get('PODAAC_PASSWORD'),
        help='WebDAV Password for JPL PO.DAAC Drive Login')
    args = parser.parse_args()

    #-- append credentials to netrc file
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    filepath = os.path.dirname(os.path.abspath(filename))
    NETRC = os.path.join(filepath,'.netrc')

    #-- check internet connection before attempting to run program
    DRIVE = posixpath.join('https://podaac-tools.jpl.nasa.gov','drive')
    if gravtk.utilities.check_connection(DRIVE) and not args.webdav:
        #-- compile HTML parser for lxml
        args.webdav = podaac_webdav(args.user,args.password)
    #-- append to netrc file and set permissions level
    with open(NETRC,'a+') as f:
        #-- NASA Earthdata credentials
        f.write('machine {0} login {1} password {2}\n'.format(
            'urs.earthdata.nasa.gov',args.user,args.password))
        #-- JPL PO.DAAC drive credentials
        f.write('machine {0} login {1} password {2}\n'.format(
            'podaac-tools.jpl.nasa.gov',args.user,args.webdav))
        os.chmod(NETRC, 0o600)

#-- run main program
if __name__ == '__main__':
    main()
