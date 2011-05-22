#! /usr/bin/env python
#
# spigot is a rate limiter for aggregating syndicated content to StatusNet
#
# (c) 2011 by Nathan Smith <nathan@smithfam.info>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import ConfigParser
import sqlite3
import sys

try:
    import statusnet
except ImportError, e:
    print "Error: %e"
    sys.exit(2)

