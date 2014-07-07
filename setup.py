# -*- coding: utf-8 -*-
#!/usr/bin/env python

import os
import sys


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import solarblog
version = solarblog.__version__

setup(
    name='Solar Blog',
    version=version,
    author='',
    author_email='jroth.solar@gmail.com',
    packages=[
        'solarblog',
    ],
    include_package_data=True,
    install_requires=[
        'Django>=1.6.1',
    ],
    zip_safe=False,
    scripts=['solarblog/manage.py'],
)