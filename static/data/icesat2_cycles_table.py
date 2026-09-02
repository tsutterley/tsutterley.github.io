#!/usr/bin/env python
"""
icesat2_cycles_table.py
Written by Tyler Sutterley (09/2026)

Creates a file with the date range for each ICESat-2 cycle

UPDATE HISTORY:
    Updated 09/2026: forked to just make the table and csv files
    Written 01/2025
"""

import sys
import os
import re
import time
import inspect
import pathlib
import lxml.etree
import urllib.request

def element(el, c="tooltip", s="text-align:center", t=None):
    # build element
    cls = f' class="{c}"' if c is not None else ""
    sty = f' style="{s}"' if s is not None else ""
    title = f' title="{t}"' if t is not None else ""
    return f"<{el}{cls}{sty}{title}>"

def close(el):
    return f"</{el}>"

def main():
    # directory setup
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    filepath = pathlib.Path(filename).absolute().parent
    content = filepath.parents[1].joinpath("content", "data")
    # output html table and csv files
    table_file = content.joinpath("ICESat-2-Cycles.table")
    csv_file = filepath.joinpath("ICESat2_cycles.csv")
    # open output files
    f1 = table_file.open("w")
    f2 = csv_file.open("w")
    print("cycle,start,end", file=f2)

    # print table headers
    print(element('table', s=None), file=f1)
    today = time.strftime("%Y-%m-%d", time.localtime())
    title = f"Table last modified {today}"
    print(element('thead', c=None, s=None, t=title), file=f1)
    print(element('tr', c=None, s=None), file=f1)
    print(f"\t{element('th', c=None)}ICESat-2 Cycle{close('th')}", file=f1)
    print(f"\t{element('th', c=None)}Start Date{close('th')}", file=f1)
    print(f"\t{element('th', c=None)}End Date{close('th')}", file=f1)
    print(close('tr'), file=f1)
    print(close('thead'), file=f1)
    # print table body
    print(element('tbody', c=None, s=None), file=f1)


    # read the data spec page
    parser = lxml.etree.HTMLParser()
    timeout = None
    HOST = "https://icesat-2.gsfc.nasa.gov/science/specs"
    request = urllib.request.Request(HOST)
    response = urllib.request.urlopen(request, timeout=timeout)
    tree = lxml.etree.parse(response, parser)
    # find cycles from data spec page
    strongtext = tree.xpath("//p//strong/text()")
    cycles = [s for s in strongtext if re.match(r"Cycle \d+", s)]
    # for each ycle
    for c in cycles:
        # printing table lines to file
        print(element('tr', s=None), file=f1)
        cycle, date = c.split(":")
        cycle = cycle.strip()
        # extract cycle number and date range
        (cycle_number,) = re.findall(r"\d+", cycle)
        sd, ed = re.findall(r"(\w+)\s(\d+)([,]?\s[\(]?\d+[\)]?)?", date)
        (ey,) = re.findall(r"\d+", ed[2])
        # append year if not present
        if re.findall(r"\d+", sd[2]):
            (sy,) = re.findall(r"\d+", sd[2])
        else:
            sy = ey
        # convert to date format
        stime = time.strptime(f"{sd[1]} {sd[0]} {sy}", "%d %B %Y")
        etime = time.strptime(f"{ed[1]} {ed[0]} {ey}", "%d %B %Y")
        # print to HTML file
        start_abbrv = time.strftime("%b %d %Y", stime)
        end_abbrv = time.strftime("%b %d %Y", etime)
        print(f"\t{element('td', c='tooltip__dates')}{cycle}{close('td')}", file=f1)
        print(f"\t{element('td', c=None)}{start_abbrv}{close('td')}", file=f1)
        print(f"\t{element('td', c=None)}{end_abbrv}{close('td')}", file=f1)
        # print to csv file
        start_iso = time.strftime("%G-%m-%d", stime)
        end_iso = time.strftime("%G-%m-%d", etime)
        print(f"{cycle_number},{start_iso},{end_iso}", file=f2)
        # end of table row
        print(close('tr'), file=f1)
    # print table body footer text
    print(close('tbody'), file=f1)
    print(close('table'), file=f1)
    
    # close output table and csv files
    f1.close()
    f2.close()


# run the program
if __name__ == "__main__":
    main()
