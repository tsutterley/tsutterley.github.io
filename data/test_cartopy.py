#!/usr/bin/env python
u"""
test_cartopy.py
"""
import pytest
import warnings
import cartopy.crs as ccrs
from numpy.testing import assert_almost_equal

def test_cartopy():
    crs = ccrs.PlateCarree()
    assert_almost_equal(crs.boundary.bounds,
        [-180.0, -90.0, 180.0, 90.0],
        decimal=0)
