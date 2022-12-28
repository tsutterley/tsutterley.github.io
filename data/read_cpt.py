#!/usr/bin/env python
u"""
read_cpt.py
Written by Tyler Sutterley (09/2020)
Reads a GMT color palette table for use with matplotlib cmap functions
Can import HSV (hue-saturation-value) or RGB values

CALLING SEQUENCE:
    cpt = read_cpt(cpt_file)
    cmap = colors.LinearSegmentedColormap('cpt_import', cpt)

INPUTS:
    filename: cpt file

OPTIONS:
    REVERSE: output inverse color map

OUTPUTS:
    colorDict: python dictionary with RGB triple
        for use with colors.LinearSegmentedColorMap

NOTES:
    import matplotlib.colors as colors

UPDATE HISTORY:
    Updated 09/2020: python3 compatible regular expression patterns
    Updated 01/2019: added option REVERSE to flip the colormap
    Updated 04/2015: use regular expressions and updated header text
    Updated 09/2014: updated header text
    Written 07/2014
"""
import re
import colorsys
import numpy as np

def read_cpt(filename, REVERSE=False):

    #-- read the cpt file and get contents
    with open(filename,'r') as f:
        file_contents = f.read().splitlines()

    #-- compile regular expression operator to find numerical instances
    rx = re.compile(r'[-+]?(?:(?:\d*\.\d+)|(?:\d+\.?))(?:[Ee][+-]?\d+)?')

    #-- create list objects for x, r, g, b
    x = []
    r = []
    g = []
    b = []
    for line in file_contents:
        #-- skip over commented header text
        if bool(re.search(r"#",line)):
            #-- find color model
            if bool(re.search(r'COLOR_MODEL.*HSV',line)):
                #-- HSV color model chosen
                colorModel = "HSV"
            else:
                #-- assume RGB color model
                colorModel = "RGB"
            continue
        #-- find numerical instances within line
        x_temp,r_temp,g_temp,b_temp,x_end,r_end,g_end,b_end = rx.findall(line)
        #-- append colors and locations to lists
        x.append(x_temp)
        r.append(r_temp)
        g.append(g_temp)
        b.append(b_temp)
    #-- append end colors and locations to lists
    x.append(x_end)
    r.append(r_end)
    g.append(g_end)
    b.append(b_end)

    #-- convert list objects to numpy arrays
    x = np.array(x, dtype=np.float64)
    #-- if flipping the colormap
    if REVERSE:
        r = np.array(r[::-1], dtype=np.float64)
        g = np.array(g[::-1], dtype=np.float64)
        b = np.array(b[::-1], dtype=np.float64)
    else:
        r = np.array(r, dtype=np.float64)
        g = np.array(g, dtype=np.float64)
        b = np.array(b, dtype=np.float64)

    #-- convert input color map to output
    if (colorModel == "HSV"):
        #-- convert HSV (hue-saturation-value) to RGB
        for i,xi in enumerate(x):
            rr,gg,bb = colorsys.hsv_to_rgb(r[i]/360.,g[i],b[i])
            r[i] = rr
            g[i] = gg
            b[i] = bb
    elif (colorModel == "RGB"):
        #-- normalize hexadecimal RGB triple from (0:255) to (0:1)
        r = r/255.
        g = g/255.
        b = b/255.

    #-- calculate normalized locations (0:1)
    xNorm = (x - x[0])/(x[-1] - x[0])

    #-- output RGB lists containing normalized location and colors
    red = []
    blue = []
    green = []
    for i,xi in enumerate(x):
        red.append([xNorm[i],r[i],r[i]])
        green.append([xNorm[i],g[i],g[i]])
        blue.append([xNorm[i],b[i],b[i]])

    return {'red':red, 'green':green, 'blue':blue}
