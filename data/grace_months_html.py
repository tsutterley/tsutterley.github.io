#!/usr/bin/env python
u"""
grace_months_html.py
Written by Tyler Sutterley (10/2020)

Creates a html file with the start and end days for each dataset
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
import os
import inspect
import argparse
import numpy as np
import calendar,time

#-- PURPOSE: create HTML file of GRACE "nominal" months
def grace_months(base_dir, DREL=['RL06','rl06v1.0']):

    #-- Opening output GRACE months HTML file
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    filepath = os.path.dirname(os.path.abspath(filename))
    fid = open(os.path.join(filepath,'GRACE-Months.html'), 'w')

    #-- Initial parameters
    #-- processing centers
    PROC = ['CSR', 'GFZ', 'JPL', 'GSFC']
    #-- read from GSM datasets
    DSET = 'GSM'
    #-- maximum month of the datasets
    #-- checks for the maximum month between processing centers
    max_mon = 0
    #-- contain the information for each dataset
    var_info = {}

    #-- Looping through data releases first (all RL04 then all RL05)
    #-- for each considered data release (RL04,RL05)
    for rl in DREL:
        #-- for each processing centers (CSR, GFZ, JPL)
        for pr in PROC:
            #-- Setting the data directory for processing center and release
            grace_dir = os.path.join(base_dir,pr,rl,DSET)
            #-- read GRACE date ascii file
            #-- file created in read_grace.py or grace_dates.py
            grace_date_file = '{0}_{1}_DATES.txt'.format(pr,rl)
            if os.access(os.path.join(grace_dir,grace_date_file), os.F_OK):
                #-- skip the header line
                date_input = np.loadtxt(os.path.join(grace_dir,grace_date_file),
                    skiprows=1)
                #-- number of months
                nmon = np.shape(date_input)[0]

                #-- Setting the dictionary key e.g. 'CSR RL04'
                var_name = '{0} {1}'.format(pr,rl)

                #-- Creating a python dictionary for each dataset with parameters:
                #-- month #, start year, start day, end year, end day
                #-- Purpose is to get all of the dates loaded for each dataset
                #-- Adding data to dictionary for data processing and release
                var_info[var_name] = {}
                #-- allocate for output variables
                var_info[var_name]['mon'] = np.zeros((nmon),dtype=np.int)
                var_info[var_name]['styr'] = np.zeros((nmon),dtype=np.int)
                var_info[var_name]['stday'] = np.zeros((nmon),dtype=np.int)
                var_info[var_name]['endyr'] = np.zeros((nmon),dtype=np.int)
                var_info[var_name]['endday'] = np.zeros((nmon),dtype=np.int)
                #-- place output variables in dictionary
                for i,key in enumerate(['mon','styr','stday','endyr','endday']):
                    #-- first column is date in decimal form (start at 1 not 0)
                    var_info[var_name][key] = date_input[:,i+1].astype(np.int)
                #-- Finding the maximum month measured
                if (var_info[var_name]['mon'].max() > max_mon):
                    #-- if the maximum month in this dataset is greater
                    #-- than the previously read datasets
                    max_mon = np.int(var_info[var_name]['mon'].max())

    #-- print HTML headers
    print('<!DOCTYPE html>', file=fid)
    print('<html>', file=fid)
    print('\t<head>', file=fid)
    print('\t<meta charset="utf-8">', file=fid)
    print('\t<meta name="author" content="Tyler Sutterley">', file=fid)
    print('\t<meta name="viewport" content="width=device-width">', file=fid)
    print('\t<title>GRACE/GRACE-FO Months</title>', file=fid)
    print('\t<link rel="icon" href="../assets/img/favicon.ico" type="image/x-icon"/>', file=fid)
    print('\t<link rel="stylesheet" href="../assets/css/styles.css">', file=fid)
    print('\t<link rel="stylesheet" href="../assets/css/font-awesome.min.css">', file=fid)
    print('\t<link rel="stylesheet" href="../assets/css/academicons.min.css">', file=fid)
    print('\t<style>', file=fid)
    print('\t\ttable {', file=fid)
    print('\t\t\twidth:auto;', file=fid)
    print('\t\t\tborder-collapse: collapse;', file=fid)
    print('\t\t\tborder: 2px solid black;', file=fid)
    print('\t\t\t}', file=fid)
    print('\t\ttable.ref {', file=fid)
    print('\t\t\twidth:auto;', file=fid)
    print('\t\t\tborder: None;', file=fid)
    print('\t\t\tmargin:0 0 20px;', file=fid)
    print('\t\t\tcounter-reset: rowNumber;', file=fid)
    print('\t\t\t}', file=fid)
    print('\t\ttd.ref {', file=fid)
    print('\t\t\ttext-align:left;', file=fid)
    print('\t\t\tpadding:5px 10px;', file=fid)
    print('\t\t\tborder-bottom:1px solid #e5e5e5;', file=fid)
    print('\t\t}', file=fid)
    print('\t\ttr.ref {', file=fid)
    print('\t\t\ttext-align:left;', file=fid)
    print('\t\t\tpadding:5px 10px;', file=fid)
    print('\t\t\tborder-bottom:1px solid #e5e5e5;', file=fid)
    print('\t\t\tcounter-increment: rowNumber;',file=fid)
    print('\t\t}', file=fid)
    print('\t\ttable.ref tr.ref td.ref:first-child::before {', file=fid)
    print('\t\t\tcontent: "[" counter(rowNumber) "]";',file=fid)
    print('\t\t}', file=fid)
    print('\t\tth {', file=fid)
    print('\t\t\tbackground-color: #222;', file=fid)
    print('\t\t\tcolor: white;', file=fid)
    print('\t\t\tpadding: 5px;', file=fid)
    print('\t\t\tborder-bottom: 2px solid black;', file=fid)
    print('\t\t}', file=fid)
    print('\t\ttd {', file=fid)
    print('\t\t\tpadding: 5px;', file=fid)
    print('\t\t\tborder-bottom: 1px solid black;', file=fid)
    print('\t\t}', file=fid)
    print('\t\ttr.hover:hover {', file=fid)
    print('\t\t\tbackground-color: #fffbcc;', file=fid)
    print('\t\t}', file=fid)
    print('\t\tspan.hover {', file=fid)
    print('\t\t\tposition: fixed;', file=fid)
    print('\t\t\tvisibility: hidden;', file=fid)
    print('\t\t}', file=fid)
    print('\t\ttd.hover:hover span {', file=fid)
    print('\t\t\tvisibility: visible;', file=fid)
    print('\t\t\ttop:15%; left:50%;', file=fid)
    print('\t\t\tz-index:1;', file=fid)
    print('\t\t}', file=fid)
    print('\t</style>', file=fid)
    print('\t</head>', file=fid)
    print('\t<body id="preview" onload="lfsmedia()">', file=fid)
    print('\t\t<div id="Sidenav" class="sidenav">', file=fid)
    print('\t\t\t<a href="javascript:void(0)" class="closebtn" onclick="closeNav()">&times;</a>', file=fid)
    print('\t\t\t<a href="../index.html">Home</a>', file=fid)
    print('\t\t\t<a href="../references/publications.html">Publications</a>', file=fid)
    print('\t\t\t<a href="../references/presentations.html">Presentations</a>', file=fid)
    print('\t\t\t<a href="../references/datasets.html">Datasets</a>', file=fid)
    print('\t\t\t<a href="../references/documentation.html">Documentation</a>', file=fid)
    print('\t\t\t<a href="../references/Sutterley_Tyler.pdf">Curriculum Vitae</a>', file=fid)
    print('\t\t\t<a href="../news/index.html">News</a>', file=fid)
    print('\t\t\t<a href="../resources/index.html">Resources</a>', file=fid)
    print('\t\t\t<a href="../animations/greenland.html">GRACE Greenland Animation</a>', file=fid)
    print('\t\t\t<a href="../animations/antarctica.html">GRACE Antarctic Animation</a>', file=fid)
    print(('\t\t</div>\n\t\t<span style="font-size:20px;cursor:pointer" '
        'onclick="openNav()">&#9776;</span>'), file=fid)
    print('\t\t<table>', file=fid)
    #-- print table header
    print('\t\t<thead>', file=fid)
    print('\t\t<tr>', file=fid)
    print('\t\t\t<th style="text-align:center">Month</th>', file=fid)
    print('\t\t\t<th style="text-align:center">Date</th>', file=fid)
    #-- sort datasets alphanumerically
    var_name = sorted(var_info.keys())
    for v in var_name:
        print('\t\t\t<th style="text-align:center">{0}</th>'.format(v),file=fid)
    print('\t\t</tr>', file=fid)
    print('\t\t</thead>', file=fid)
    #-- print table body
    print('\t\t<tbody>', file=fid)
    #-- for each possible month
    #-- GRACE starts at month 004 (April 2002)
    #-- max_mon+1 to include max_mon
    for m in range(4, max_mon+1):
        #-- finding the month name e.g. Apr
        calendar_year = 2002 + (m-1)//12
        calendar_month = (m-1) % 12 + 1
        month_string = calendar.month_abbr[calendar_month]
        #-- printing table lines to file
        print('\t\t<tr class="hover">',file=fid)
        print('\t\t\t<td style="text-align:center">{0:03d}</td>'.format(m),
            file=fid)
        print('\t\t\t<td style="text-align:center">{0}{1:4d}</td>'.format(
            month_string,calendar_year), file=fid)
        #-- for each processing center and data release
        for var in var_name:
            #-- split var name for data processing center and release
            PROC,DREL = var.split()
            #-- find if the month of data exists
            #-- exists will be greater than 0 if there is a match
            exists = np.count_nonzero(var_info[var]['mon'] == m)
            if (exists != 0):
                #-- if there is a matching month
                #-- indice of matching month
                ind, = np.nonzero(var_info[var]['mon'] == m)
                #-- start date
                st_yr, = var_info[var]['styr'][ind]
                st_day, = var_info[var]['stday'][ind]
                #-- end date
                end_yr, = var_info[var]['endyr'][ind]
                end_day, = var_info[var]['endday'][ind]
                #-- output table element is the date range
                #-- string format: 2002_102--2002_120
                args = (st_yr, st_day, end_yr, end_day)
                print(('\t\t\t<td class="hover" style="text-align:center">'
                    '{0:4d}_{1:03d}&ndash;{2:4d}_{3:03d}').format(*args),file=fid)
                print('\t\t\t\t<span class="hover">',file=fid)
                src = '{0}-{1}-{2:03d}.jpg'.format(PROC,DREL,m)
                print('\t\t\t\t\t<img class="lfs" data-path="images/{0}">'.format(src),file=fid)
                print('\t\t\t\t</span>',file=fid)
                print('\t\t\t</td>', file=fid)
            else:
                #-- if there is no matching month: missing or not yet processed
                print(('\t\t\t<td class="hover" style="text-align:center">'
                    '<b>**missing**</b></td>'), file=fid)
        #-- end of table row
        print('\t\t</tr>', file=fid)
    #-- print table body footer text
    print('\t\t</tbody>', file=fid)
    print('\t\t</table>', file=fid)


    #-- print references
    print('\n\t\t<div style="width:860px">', file=fid)
    print('\t\t<p><em>GRACE/GRACE-FO anomalies for harmonic solutions are calculated in reference to the 2003'
        '&#8211;2010 mean\n\t\tand are smoothed using a 350km radius Gaussian filter', file=fid)
    print(('''\t\t<a href="#Wahr:1998hy" onmouseover="HighlightRow('Wahr:1998hy')"\n'''
        '''\t\t\tonmouseout="UnhighlightRow('Wahr:1998hy')">'''
        '(Wahr&nbsp;et&nbsp;al.,&nbsp;1998)</a>'), file=fid)
    print('\t\tafter destriping with a decorrelation algorithm ', file=fid)
    print(('''\t\t<a href="#Swenson:2006hu" onmouseover="HighlightRow('Swenson:2006hu')"\n'''
        '''\t\t\tonmouseout="UnhighlightRow('Swenson:2006hu')">'''
        '(Swenson&nbsp;and&nbsp;Wahr,&nbsp;2006)</a>.'), file=fid)
    #-- pole tide drift if showing Release-5 products
    if ('RL05' in DREL):
        print(('\t\tGRACE Release-5 data products are corrected for pole tide '
            'drift following '), file=fid)
        print(('''\t\t<a href="#Wahr:2015dg" onmouseover="HighlightRow('Wahr:2015dg')"\n'''
            '''\t\t\tonmouseout="UnhighlightRow('Wahr:2015dg')">'''
            'Wahr&nbsp;et&nbsp;al.&nbsp;(2015)</a>.'), file=fid)
    print(('\t\tGSFC GRACE/GRACE-FO mascon data products are calculated as described in '), file=fid)
    print(('''\t\t<a href="#Loomis:2019ef" onmouseover="HighlightRow('Loomis:2019ef')"\n'''
        '''\t\t\tonmouseout="UnhighlightRow('Loomis:2019ef')">'''
        'Loomis&nbsp;et&nbsp;al.&nbsp;(2019)</a>.'), file=fid)
    print('\t\tGRACE/GRACE-FO fields have been corrected for Glacial Isostatic '
        'Adjustment (GIA) using coefficients from ICE6G Version-D', file=fid)
    print(('''\t\t<a href="#Peltier:2018dp" onmouseover="HighlightRow('Peltier:2018dp')"\n'''
        '''\t\t\tonmouseout="UnhighlightRow('Peltier:2018dp')">'''
        '(Peltier&nbsp;et&nbsp;al.&nbsp;,&nbsp;2018)</a>.'), file=fid)

    print('\t\t<table class="ref">', file=fid)
    print('\t\t\t<tr class="ref" valign="top" id="Swenson:2006hu">', file=fid)
    print('\t\t\t\t<td class="ref" align="right"></td>', file=fid)
    print('\t\t\t\t<td class="ref">', file=fid)
    print('\t\t\t\tS.&nbsp;Swenson and J.&nbsp;Wahr.', file=fid)
    print('\t\t\t\tPost-processing removal of correlated errors in GRACE data.', file=fid)
    print('\t\t\t\t<em>Geophysical Research Letters</em>, 33(8), 2006.', file=fid)
    print('\t\t\t\t[&nbsp;<a href="../references/Swenson-2006hu.bib">bib</a>&nbsp;|', file=fid)
    print('\t\t\t\t<a href="https://doi.org/10.1029/2005GL025285">http</a>&nbsp;]', file=fid)
    print('\t\t\t\t</td>', file=fid)
    print('\t\t\t</tr>', file=fid)

    print('\t\t\t<tr class="ref" valign="top" id="Wahr:1998hy">', file=fid)
    print('\t\t\t\t<td class="ref" align="right"></td>', file=fid)
    print('\t\t\t\t<td class="ref">', file=fid)
    print('\t\t\t\tJ.&nbsp;Wahr, M.&nbsp;Molenaar and F.&nbsp;Bryan.', file=fid)
    print("\t\t\t\tTime variability of the Earth's gravity field: Hydrological and", file=fid)
    print('\t\t\t\toceanic effects and their possible detection using GRACE.', file=fid)
    print('\t\t\t\t<em>Journal of Geophysical Research: Solid Earth</em>,', file=fid)
    print('\t\t\t\t103(B12):30205&#8211;30229, 1998.', file=fid)
    print('\t\t\t\t[&nbsp;<a href="../references/Wahr-1998hy.bib">bib</a>&nbsp;|', file=fid)
    print('\t\t\t\t<a href="https://doi.org/10.1029/98JB02844">http</a>&nbsp;]', file=fid)
    print('\t\t\t\t</td>', file=fid)
    print('\t\t\t</tr>', file=fid)

    #-- pole tide drift if showing Release-5 products
    if ('RL05' in DREL):
        print('\t\t\t<tr class="ref" valign="top" id="Wahr:2015dg">', file=fid)
        print('\t\t\t\t<td class="ref" align="right"></td>', file=fid)
        print('\t\t\t\t<td class="ref">', file=fid)
        print('\t\t\t\tJ.&nbsp;Wahr, R.&nbsp;S.&nbsp;Nerem and S.&nbsp;V.&nbsp;Bettadpur.', file=fid)
        print('\t\t\t\tThe pole tide and its effect on GRACE time-variable gravity measurements:', file=fid)
        print('\t\t\t\tImplications for estimates of surface mass variations.', file=fid)
        print('\t\t\t\t<em>Journal of Geophysical Research: Solid Earth</em>,', file=fid)
        print('\t\t\t\t120(6):4597&#8211;4615, 2015.', file=fid)
        print('\t\t\t\t[&nbsp;<a href="../references/Wahr-2015dg.bib">bib</a>&nbsp;|', file=fid)
        print('\t\t\t\t<a href="https://doi.org/10.1002/2015JB011986">http</a>&nbsp;]', file=fid)
        print('\t\t\t\t</td>', file=fid)
        print('\t\t\t</tr>', file=fid)

    print('\t\t\t<tr class="ref" valign="top" id="Loomis:2019ef">', file=fid)
    print('\t\t\t\t<td class="ref" align="right"></td>', file=fid)
    print('\t\t\t\t<td class="ref">', file=fid)
    print('\t\t\t\tB.&nbsp;D.&nbsp;Loomis, S.&nbsp;B.&nbsp;Luthcke, T.&nbsp;J.&nbsp;Sabaka.', file=fid)
    print('\t\t\t\tRegularization and error characterization of GRACE mascons.', file=fid)
    print('\t\t\t\t<em>Journal of Geodesy</em>,', file=fid)
    print('\t\t\t\t93(9):1381&#8211;1398, 2019.', file=fid)
    print('\t\t\t\t[&nbsp;<a href="../references/Loomis-2019ef.bib">bib</a>&nbsp;|', file=fid)
    print('\t\t\t\t<a href="https://doi.org/10.1007/s00190-019-01252-y">http</a>&nbsp;]', file=fid)

    print('\t\t\t<tr class="ref" valign="top" id="Peltier:2018dp">', file=fid)
    print('\t\t\t\t<td class="ref" align="right"></td>', file=fid)
    print('\t\t\t\t<td class="ref">', file=fid)
    print('\t\t\t\tW.&nbsp;R.&nbsp;Peltier, D.&nbsp;F.&nbsp;Argus, R.&nbsp;Drummond.', file=fid)
    print('\t\t\t\tComment on "An Assessment of the ICE-6G_C (VM5a) Glacial ', file=fid)
    print('\t\t\t\tIsostatic Adjustment Model" by Purcell et al.', file=fid)
    print('\t\t\t\t<em>Journal of Geophysical Research: Solid Earth</em>,', file=fid)
    print('\t\t\t\t123(2):2019&#8211;2028, 2018.', file=fid)
    print('\t\t\t\t[&nbsp;<a href="../references/Peltier-2018dp.bib">bib</a>&nbsp;|', file=fid)
    print('\t\t\t\t<a href="https://doi.org/10.1002/2016JB013844">http</a>&nbsp;]', file=fid)
    print('\t\t\t\t</td>', file=fid)
    print('\t\t\t</tr>\n\t\t</table>\n\t\t</p>\n\t\t</div>', file=fid)

    #-- print footer text
    args = (time.strftime('%Y-%m-%d',time.localtime()), os.path.basename(sys.argv[0]))
    print(('\n\t\t<p><em>Table generated on {0} with <a href="./{1}">\n'
        '\t\t\t<code>{1}</code></a></em><br>').format(*args), file=fid)
    print('\t\t<em><a href="./GRACE_months.txt">Table as plain text</a></em></p>', file=fid)
    #-- print navigation symbols
    print(('\t\t<p><small>\n\t\t\t<a href="../index.html">'
        '<i class="fa fa-home" aria-hidden="true"></i></a>\n\t\t\t'
        '<a href="javascript:history.back()">'
        '<i class="fa fa-angle-left" aria-hidden="true"></i></a>'
        '\n\t\t</small></p>'), file=fid)

    #-- print javascript commands
    print(('\t\t<script type="text/javascript" '
        'src="../assets/js/highlight.row.js"></script>'), file=fid)
    print(('\t\t<script type="text/javascript" '
        'src="../assets/js/sidenav.js"></script>'), file=fid)
    print(('\t\t<script type="text/javascript" '
        'src="../assets/js/scale.fix.js"></script>'), file=fid)
    print(('\t\t<script type="text/javascript" '
        'src="../assets/js/lfs.media.js"></script>'), file=fid)
    #-- print HTML footers
    print('\t</body>\n</html>', file=fid)
    #-- close output HTML file
    fid.close()

#-- PURPOSE: functional call to grace_months() if running as program
def main():
    #-- Read the system arguments listed after the program
    parser = argparse.ArgumentParser(
        description="""SCreates a html file with the start and end days for
            each dataset
            """
    )
    #-- command line parameters
    #-- working data directory
    parser.add_argument('--directory','-D',
        type=lambda p: os.path.abspath(os.path.expanduser(p)),
        default=os.getcwd(),
        help='Working data directory')
    #-- GRACE/GRACE-FO data release
    parser.add_argument('--release','-r',
        metavar='DREL', type=str, nargs='+',
        default=['RL06','rl06v2.0'],
        help='GRACE/GRACE-FO data release')
    args = parser.parse_args()

    #-- run GRACE/GRACE-FO months program
    grace_months(args.directory, DREL=args.release)

#-- run main program
if __name__ == '__main__':
    main()
