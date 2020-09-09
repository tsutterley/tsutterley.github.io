#!/usr/bin/env python
u"""
test_font_files.py
"""
import os
import pytest
import warnings
import matplotlib.font_manager
import matplotlib.pyplot as plt

def test_font_files():
    basedir = os.path.join(os.sep,'usr','share','fonts','truetype','Helvetica')
    fonts = ['HelveticaBoldOblique.ttf','HelveticaBold.ttf',
        'HelveticaLightOblique.ttf','HelveticaLight.ttf',
        'HelveticaOblique.ttf','Helvetica.ttf']
    for fpath in fonts:
        assert os.path.exists(os.path.join(basedir, fpath))
    #-- rebuilt the matplotlib fonts and set parameters
    matplotlib.font_manager._rebuild()
    matplotlib.rcParams['axes.linewidth'] = 1.5
    matplotlib.rcParams['font.family'] = 'sans-serif'
    matplotlib.rcParams['font.sans-serif'] = ['Helvetica']
    matplotlib.rcParams['mathtext.default'] = 'regular'
