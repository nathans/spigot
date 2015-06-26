#! /usr/bin/env python

from distutils.core import setup

setup(name='spigot',
      version='2.3.0',
      description='Rate-limited feed aggregation to pump.io',
      long_description=open("README.rst").read(),
      author='Nathan D. Smith',
      author_email='nathan@smithfam.info',
      url='https://pypi.python.org/pypi/spigot/',
      scripts=['spigot.py'],
      license="GPLv3",
      install_requires=[
          "pypump=0.6",
          "feedparser>=5.0",
          "argparse>=1.0",
          ],
      classifiers=["Development Status :: 5 - Production/Stable",
                   "Programming Language :: Python",
                   "Programming Language :: Python :: 2",
                   "Programming Language :: Python :: 2.6",
                   "Programming Language :: Python :: 2.7",
                   "Operating System :: OS Independent",
                   "Operating System :: POSIX",
                   "Intended Audience :: End Users/Desktop"])
