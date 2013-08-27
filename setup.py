#! /usr/bin/env python

from distutils.core import setup

setup(name='spigot',
      version='2.0.1',
      description='Rate-limited feed aggregation to pump.io',
      long_description=open("README.rst").read(),
      author='Nathan D. Smith',
      author_email='nathan@smithfam.info',
      url='http://nathan.smithfam.info/spigot.html',
      scripts=['spigot.py'],
      license="GPLv3",
      install_requires=[
          "pypump>=0.2",
          "feedparser>=5.0",
          ],
      classifiers=["Development Status :: 4 - Beta",
                   "Programming Language :: Python",
                   "Programming Language :: Python :: 2",
                   "Programming Language :: Python :: 2.6",
                   "Programming Language :: Python :: 2.7",
                   "Operating System :: OS Independent",
                   "Operating System :: POSIX",
                   "Intended Audience :: End Users/Desktop",
                   "License :: OSI Approved",
                   "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
                   "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",]    
     )
