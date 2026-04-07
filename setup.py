#!/usr/bin/env python
"""
This setup.py exists primarily for versioneer to work correctly.
For actual installation, use: pip install -e .
"""

import versioneer
from setuptools import setup

setup(version=versioneer.get_version(), cmdclass=versioneer.get_cmdclass())
