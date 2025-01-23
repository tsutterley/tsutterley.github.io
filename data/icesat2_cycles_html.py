#!/usr/bin/env python
u"""
icesat2_cycles_html.py
Written by Tyler Sutterley (01/2025)

Creates a html file with the date range for each ICESat-2 cycle

UPDATE HISTORY:
    Written 01/2025
"""
import sys
import os
import re
import time
import inspect
import lxml.etree
import urllib.request

def main():

    # Opening output HTML and csv files
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    filepath = os.path.dirname(os.path.abspath(filename))
    f1 = open(os.path.join(filepath,'ICESat-2-Cycles.html'), 'w')
    f2 = open(os.path.join(filepath,'ICESat2_cycles.csv'), 'w')
    print('cycle,start,end', file=f2)

    # print HTML headers
    print('<!DOCTYPE html>', file=f1)
    print('<html>', file=f1)
    print('\t<head>', file=f1)
    print('\t<meta charset="utf-8">', file=f1)
    print('\t<meta name="author" content="Tyler Sutterley">', file=f1)
    print('\t<meta name="viewport" content="width=device-width">', file=f1)
    print('\t<title>ICESat-2 Cycles</title>', file=f1)
    print('\t<link rel="icon" href="../assets/img/favicon.ico" type="image/x-icon"/>', file=f1)
    print('\t<link rel="stylesheet" href="../assets/css/styles.css">', file=f1)
    print('\t<link rel="stylesheet" href="../assets/css/font-awesome.min.css">', file=f1)
    print('\t<link rel="stylesheet" href="../assets/css/academicons.min.css">', file=f1)
    print('\t<style>', file=f1)
    print('\t\ttable {', file=f1)
    print('\t\t\twidth:auto;', file=f1)
    print('\t\t\tborder-collapse: collapse;', file=f1)
    print('\t\t\tborder: 2px solid black;', file=f1)
    print('\t\t\t}', file=f1)
    print('\t\ttable.ref {', file=f1)
    print('\t\t\twidth:auto;', file=f1)
    print('\t\t\tborder: None;', file=f1)
    print('\t\t\tmargin:0 0 20px;', file=f1)
    print('\t\t\tcounter-reset: rowNumber;', file=f1)
    print('\t\t\t}', file=f1)
    print('\t\ttd.ref {', file=f1)
    print('\t\t\ttext-align:left;', file=f1)
    print('\t\t\tpadding:5px 10px;', file=f1)
    print('\t\t\tborder-bottom:1px solid #e5e5e5;', file=f1)
    print('\t\t}', file=f1)
    print('\t\ttr.ref {', file=f1)
    print('\t\t\ttext-align:left;', file=f1)
    print('\t\t\tpadding:5px 10px;', file=f1)
    print('\t\t\tborder-bottom:1px solid #e5e5e5;', file=f1)
    print('\t\t\tcounter-increment: rowNumber;',file=f1)
    print('\t\t}', file=f1)
    print('\t\ttable.ref tr.ref td.ref:first-child::before {', file=f1)
    print('\t\t\tcontent: "[" counter(rowNumber) "]";',file=f1)
    print('\t\t}', file=f1)
    print('\t\tth {', file=f1)
    print('\t\t\tbackground-color: #222;', file=f1)
    print('\t\t\tcolor: white;', file=f1)
    print('\t\t\tpadding: 5px;', file=f1)
    print('\t\t\tborder-bottom: 2px solid black;', file=f1)
    print('\t\t}', file=f1)
    print('\t\ttd {', file=f1)
    print('\t\t\tpadding: 5px;', file=f1)
    print('\t\t\tborder-bottom: 1px solid black;', file=f1)
    print('\t\t}', file=f1)
    print('\t\ttr.hover:hover {', file=f1)
    print('\t\t\tbackground-color: #fffbcc;', file=f1)
    print('\t\t}', file=f1)
    print('\t\tspan.hover {', file=f1)
    print('\t\t\tposition: fixed;', file=f1)
    print('\t\t\tvisibility: hidden;', file=f1)
    print('\t\t}', file=f1)
    print('\t\ttd.hover:hover span {', file=f1)
    print('\t\t\tvisibility: visible;', file=f1)
    print('\t\t\ttop:15%; left:50%;', file=f1)
    print('\t\t\tz-index:1;', file=f1)
    print('\t\t}', file=f1)
    print('\t</style>', file=f1)
    print('\t</head>', file=f1)
    print('\t<body id="preview" onload="lfsmedia()">', file=f1)
    print('\t\t<div id="Sidenav" class="sidenav">', file=f1)
    print('\t\t\t<a href="javascript:void(0)" class="closebtn" onclick="closeNav()">&times;</a>', file=f1)
    print('\t\t\t<a href="../index.html">Home</a>', file=f1)
    print('\t\t\t<a href="../references/publications.html">Publications</a>', file=f1)
    print('\t\t\t<a href="../references/presentations.html">Presentations</a>', file=f1)
    print('\t\t\t<a href="../references/datasets.html">Datasets</a>', file=f1)
    print('\t\t\t<a href="../references/documentation.html">Documentation</a>', file=f1)
    print('\t\t\t<a href="../references/Sutterley_Tyler.pdf">Curriculum Vitae</a>', file=f1)
    print('\t\t\t<a href="../news/index.html">News</a>', file=f1)
    print('\t\t\t<a href="../resources/index.html">Resources</a>', file=f1)
    print('\t\t\t<a href="../animations/greenland.html">GRACE Greenland Animation</a>', file=f1)
    print('\t\t\t<a href="../animations/antarctica.html">GRACE Antarctic Animation</a>', file=f1)
    print('\t\t\t<a href="./GRACE-Months.html">GRACE Months</a>', file=f1)
    print(('\t\t</div>\n\t\t<span style="font-size:20px;cursor:pointer" '
        'onclick="openNav()">&#9776;</span>'), file=f1)
    print('\t\t<table>', file=f1)
    # print table header
    print('\t\t<thead>', file=f1)
    print('\t\t<tr>', file=f1)
    print('\t\t\t<th style="text-align:center">ICESat-2 Cycle</th>', file=f1)
    print('\t\t\t<th style="text-align:center">Start Date</th>', file=f1)
    print('\t\t\t<th style="text-align:center">End Date</th>', file=f1)
    print('\t\t</tr>', file=f1)
    print('\t\t</thead>', file=f1)
    # print table body
    print('\t\t<tbody>', file=f1)

    # read the data spec page
    parser = lxml.etree.HTMLParser()
    timeout = None
    HOST = 'https://icesat-2.gsfc.nasa.gov/science/specs'
    request = urllib.request.Request(HOST)
    response = urllib.request.urlopen(request, timeout=timeout)
    tree = lxml.etree.parse(response, parser)
    # find cycles from data spec page
    strongtext = tree.xpath('//p//strong/text()')
    cycles = [s for s in strongtext if re.match(r'Cycle \d+', s)]
    # for each ycle
    for c in cycles:
        # printing table lines to file
        print('\t\t<tr class="hover">',file=f1)
        cycle, date = c.split(':')
        cycle = cycle.strip()
        # extract cycle number and date range
        cycle_number, = re.findall(r'\d+', cycle)
        sd, ed = re.findall(r'(\w+)\s(\d+)([,]?\s[\(]?\d+[\)]?)?', date)
        ey, = re.findall(r'\d+', ed[2])
        # append year if not present
        if re.findall(r'\d+', sd[2]):
            sy, = re.findall(r'\d+', sd[2])
        else:
            sy = ey
        # convert to date format
        stime = time.strptime(f"{sd[1]} {sd[0]} {sy}", "%d %B %Y")
        etime = time.strptime(f"{ed[1]} {ed[0]} {ey}", "%d %B %Y")
        # print to HTML file
        start_abbrv = time.strftime('%b %d %Y', stime)
        end_abbrv = time.strftime('%b %d %Y', etime)
        print(f'\t\t\t<td style="text-align:center"><b>{cycle}</b></td>', file=f1)
        print(f'\t\t\t<td style="text-align:center">{start_abbrv}</td>', file=f1)
        print(f'\t\t\t<td style="text-align:center">{end_abbrv}</td>', file=f1)
        # print to csv file
        start_iso = time.strftime('%G-%m-%d', stime)
        end_iso = time.strftime('%G-%m-%d', etime)
        print(f'{cycle_number},{start_iso},{end_iso}', file=f2)
        # end of table row
        print('\t\t</tr>', file=f1)
    # print table body footer text
    print('\t\t</tbody>', file=f1)
    print('\t\t</table>', file=f1)

    # print footer text
    args = (time.strftime('%Y-%m-%d',time.localtime()), os.path.basename(sys.argv[0]))
    print(('\n\t\t<p><em>Table generated on {0} with <a href="./{1}">\n'
        '\t\t\t<code>{1}</code></a></em><br>').format(*args), file=f1)
    print((f'\n\t\t<em>Mission information from the <a href="{HOST}">'
        'ICESat-2 Website</a></em><br>'), file=f1)
    print('\t\t<em><a href="./ICESat2_cycles.csv">Table as csv file</a></em></p>', file=f1)
    # print navigation symbols
    print(('\t\t<p><small>\n\t\t\t<a href="../index.html">'
        '<i class="fa fa-home" aria-hidden="true"></i></a>\n\t\t\t'
        '<a href="javascript:history.back()">'
        '<i class="fa fa-angle-left" aria-hidden="true"></i></a>'
        '\n\t\t</small></p>'), file=f1)

    # print javascript commands
    print(('\t\t<script type="text/javascript" '
        'src="../assets/js/highlight.row.js"></script>'), file=f1)
    print(('\t\t<script type="text/javascript" '
        'src="../assets/js/sidenav.js"></script>'), file=f1)
    print(('\t\t<script type="text/javascript" '
        'src="../assets/js/scale.fix.js"></script>'), file=f1)
    print(('\t\t<script type="text/javascript" '
        'src="../assets/js/lfs.media.js"></script>'), file=f1)
    # print HTML footers
    print('\t</body>\n</html>', file=f1)
    # close output HTML and csv files
    f1.close()
    f2.close()


# run the program
if __name__ == '__main__':
    main()
