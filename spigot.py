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
import logging
import os
import sqlite3
import sys

#try:
 #   import statusnet
#except ImportError, e:
#    print "Error: %s" % e
#    sys.exit(2)

try:
    import feedparser
except ImportError, e:
    print "Error: %s" % e
    sys.exit(2)

class SpigotDB():
    """Handle database calls for Spigot"""
    
    def __init__(self, path):
        self.path = path
        # Check first for a database file
        if not os.path.exists(path):
            self._init_db_tables()
            logging.info("Database file does not exist.")
        # Should probably check to make sure db is not mangled
        
        self._db = sqlite3.connect(self.path)
        logging.debug("Opened connection to database")
        
    def close(self):
        """Cleanup after the db is no longer needed."""
        
        self._db.close()
        logging.debug("Closed connection to database")
        
            
    def _init_db_tables():
        conn = sqlite3.connect(path)
        curs = conn.cursor()
        # Figure out db tables based on tricklepost
        create_query = """create table items (feed text, link text, title text,
            hash text, account text, published text)"""
        curs.execute(create_query)
        conn.commit()
        logging.info("Initialized database tables")
        curs.close()
        conn.close()

class SpigotFeedPoller():
    """
    Handle the parsing of feeds.conf configuration file and polling the
    specified feeds for new posts. Add new posts to database in preparation for
    posting to the specified StatusNet accounts.

    """

    def __init__(self):
        self.feeds_to_poll = []     
        self.feeds_to_poll = self.parse_config()
        for feed in self.feeds_to_poll:
            self.scan_feed(feed)
        
    def parse_config(self):
        """Returns a list of syndicated feeds to check for new posts."""
        
        logging.info("Loading feeds.conf")
        feeds_config = ConfigParser.RawConfigParser()
        if not feeds_config.read("feeds.conf"):
            logging.error("Could not parse feeds.conf")
            sys.exit(2)
        feeds = feeds_config.sections()
        feeds_num = len(feeds)
        if feeds_num == 0:
            logging.warning("No feeds found in feeds.conf")
        else:
            logging.debug("Found %d feeds in feeds.conf" % feeds_num)
        for feed in feeds:
            logging.debug("Processing feed '%s'" % feed)
            # Ensure that the feed section has the needed attributes
            # If not, treat as a non-fatal error, but warn the user
            if ( feeds_config.has_option(feed, "url") &
                     feeds_config.has_option(feed, "account") &
                     feeds_config.has_option(feed, "interval") ):
                logging.debug("  URL: %s" % feeds_config.get(feed, "url"))
                logging.debug("  Account: %s" % feeds_config.get(feed,
                    "account"))
                logging.debug("  Interval: %s min" % feeds_config.get(feed,
                    "interval"))
                feeds_to_poll.append(feed)
                logging.debug("  Added to list of feeds to poll")
                
            else:
                logging.warning("  Missing necessary options, skipping")
        return feeds_to_poll
        
        def scan_feed(self, feed):
            """Poll the given feed and then update the database with new info"""
            
            pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, \
                            format='%(asctime)s %(levelname)s: %(message)s')
    logging.info("spigot startup")

    # Parse accounts configration file
    # Move all this to a posting class
#    logging.info("Loading accounts.conf")
#    accounts_config = ConfigParser.RawConfigParser()
#    if not accounts_config.read("accounts.conf"):
#        logging.error("Could not parse accounts.conf")
#        sys.exit(2)

    spigot_feed = SpigotFeedPoller()
    
    
# TODO
# - Offering logging configuration?
# - Authentication type
# - statusbot v. identicurse bindings to statusnet
