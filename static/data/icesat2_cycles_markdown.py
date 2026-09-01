#!/usr/bin/env python
"""
icesat2_cycles_markdown.py
Written by Tyler Sutterley (08/2026)

Creates a markdown file with the date range for each ICESat-2 cycle

UPDATE HISTORY:
    Updated 08/2026: forked for markdown table creation
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

def element(el, c="tooltip", s="text-align:center"):
    # build element
    cls = f' class="{c}"' if c is not None else ""
    sty = f' style="{s}"' if s is not None else ""
    return f"<{el}{cls}{sty}>"

def close(el):
    return f"</{el}>"

def main():
    # directory setup
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    filepath = pathlib.Path(filename).absolute().parent
    content = filepath.parents[1].joinpath("content", "data")
    # output markdown and csv files
    markdown_file = content.joinpath("ICESat-2-Cycles.md")
    csv_file = filepath.joinpath("ICESat2_cycles.csv")
    # open output files
    f1 = markdown_file.open("w")
    f2 = csv_file.open("w")
    print("cycle,start,end", file=f2)
    HOST = "https://icesat-2.gsfc.nasa.gov/science/specs"

    # print markdown headers
    print("---", file=f1)
    print("title: ICESat-2 Cycles", file=f1)
    print("summary: Date ranges of ICESat-2 91-day cycles", file=f1)
    print("---", file=f1)
    print("", file=f1)

    # print markdown headers
    print(element('table', s=None), file=f1)
    # print table header
    print(element('thead', c=None, s=None), file=f1)
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

    # print footer text
    today = time.strftime("%Y-%m-%d", time.localtime())
    lineage = pathlib.Path(sys.argv[0]).name
    f1.write('\n\n## Footnotes\n')
    f1.write(f'- _Generated on {today} with ')
    f1.write(f'[<code>{lineage}</code>]({lineage} "links__link")_\n')
    f1.write('- _Mission information provided by the ')
    f1.write(f'[ICESat-2 Website]({HOST} "links__link")_\n')
    f1.write(f'- _[Table as csv file]({csv_file.name} "links__link")_\n')
    
    # close output markdown and csv files
    f1.close()
    f2.close()


# run the program
if __name__ == "__main__":
    main()
