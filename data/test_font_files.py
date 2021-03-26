#!/usr/bin/env python
u"""
test_font_files.py
"""
import os
import pytest
import warnings
import matplotlib.font_manager
import matplotlib.pyplot as plt

def test_font_files(verbose=True):
    basedir = os.path.join(os.sep,'usr','share','fonts','truetype')
    fonts = ['HelveticaBoldOblique.ttf','HelveticaBold.ttf',
        'HelveticaLightOblique.ttf','HelveticaLight.ttf',
        'HelveticaOblique.ttf','Helvetica.ttf']
    print(os.listdir(basedir)) if verbose else None
    assert os.path.isdir(os.path.join(basedir,'Helvetica'))
    print(os.listdir(os.path.join(basedir,'Helvetica'))) if verbose else None
    for fpath in fonts:
        assert os.path.exists(os.path.join(basedir,'Helvetica',fpath))
    #-- reload the matplotlib fonts and set parameters
    matplotlib.font_manager._load_fontmanager()
    matplotlib.rcParams['axes.linewidth'] = 1.5
    matplotlib.rcParams['font.family'] = 'sans-serif'
    matplotlib.rcParams['font.sans-serif'] = ['Helvetica']
    matplotlib.rcParams['mathtext.default'] = 'regular'
