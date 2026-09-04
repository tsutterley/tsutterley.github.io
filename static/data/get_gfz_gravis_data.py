#!/usr/bin/env python
"""
get_gfz_gravis_data.py
"""

import gravity_toolkit.utilities

directory = gravity_toolkit.utilities.get_cache_path()
gravity_toolkit.utilities.from_gfz(directory=directory)
