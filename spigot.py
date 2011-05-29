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
from datetime import datetime
import hashlib
import logging
import os
import sqlite3
import sys
from time import mktime

import feedparser

# import statusnet


class SpigotDB():
    """Handle database calls for Spigot"""
 
    def __init__(self, path="spigot.db"):
        self.path = path
        self._connect()

    ### SpigotDB private methods

    def _connect(self):
        """Establish the database connection for this instantiation."""

        # Check first for a database file
        new_db = False
        if not os.path.exists(self.path):
            new_db = True
            logging.info("Database file %s does not exist" % self.path)
        try:
            self._db = sqlite3.connect(self.path)
        except:
            logging.exception("Could not connect to database %s" % self.path)
            sys.exit(2)
            
        if new_db:
                self._init_db_tables()
                
    def _init_db_tables(self):
        """Initialize the database if it is new"""

        curs = self._db.cursor()
        # Figure out db tables based on tricklepost
        create_query = """create table items (feed text, link text, title text,
            hash text, account text, date timestamp, posted timestamp)"""
        curs.execute(create_query)
        self._db.commit()
        logging.info("Initialized database tables")
        curs.close()
        
        ### SpigotDB public methods

    def close(self):
        """Cleanup after the db is no longer needed."""
        
        self._db.close()
        logging.debug("Closed connection to database")
        
    def check_hash(self, item_hash):
        """Returns true if the specified hash is already in the database."""
        
        curs = self._db.cursor()
        curs.execute("select * from items where hash=?", [item_hash])
        if len(curs.fetchall()) > 0:
            return True
        else:
            return False
        curs.close()
            
    def add_item(self, feed_name, link, title, item_hash, account, date):
        """Add an item to the database with the given parameters. Return True if
        successful."""
        
        curs = self._db.cursor()
        curs.execute("insert into items(feed, link, title, hash, account, \
            date) values (?, ?, ?, ?, ?, ?)",
            (feed_name, link, title, item_hash, account, date))
        logging.debug("    Added item %s to database" % item_hash)
        curs.close()
        self._db.commit()
        
    def get_unposted_items(self):
        """Return a list of items in the database which have yet to be sent
        through to the specified statusnet account."""
        
        curs = self._db.cursor()
        curs.execute("select * from items where posted is NULL")
        unposted_items = curs.fetchone()
        logging.info("Found %d unposted items" % len(unposted_items))
        curs.close()
        print unposted_items
        return unposted_items
        

class SpigotFeeds():
    """
    Handle the parsing of feeds.conf configuration file and polling the
    specified feeds for new posts. Add new posts to database in preparation for
    posting to the specified StatusNet accounts.

    """

    def __init__(self, db):
        self._spigotdb = db
        logging.debug("Loading feeds.conf")
        self.feeds_config = ConfigParser.RawConfigParser()
        if not self.feeds_config.read("feeds.conf"):
            logging.error("Could not parse feeds.conf")
            sys.exit(2)
        self.feeds_to_poll = []     
        self.feeds_to_poll = self.parse_config()
        for feed, feed_url, account in self.feeds_to_poll:
            self.scan_feed(feed, feed_url, account)

    def parse_config(self):
        """Returns a list of syndicated feeds to check for new posts."""
        
        # Make feeds to poll an internal variable for this function
        feeds_to_poll = []
        feeds = self.feeds_config.sections()
        feeds_num = len(feeds)
        if feeds_num == 0:
            logging.warning("No feeds found in feeds.conf")
        else:
            logging.info("Found %d feeds in feeds.conf" % feeds_num)
        for feed in feeds:
            logging.debug("Processing feed %s" % feed)
            
            # Ensure that the feed section has the needed attributes
            # If not, treat as a non-fatal error, but warn the user
            if ( self.feeds_config.has_option(feed, "url") &
                     self.feeds_config.has_option(feed, "account") &
                     self.feeds_config.has_option(feed, "interval") ):
                url = self.feeds_config.get(feed, "url")
                logging.debug("  URL: %s" % url)
                account = self.feeds_config.get(feed, "account")
                logging.debug("  Account: %s" % account)
                logging.debug("  Interval: %s min" % self.feeds_config.get(feed,
                    "interval"))
                feeds_to_poll.append((feed, url, account))
                logging.debug("  Added to list of feeds to poll")
                
            else:
                logging.warning("  Missing necessary options, skipping")
        return feeds_to_poll

    def scan_feed(self, feed, feed_url, account):
        """Poll the given feed and then update the database with new info"""

        logging.debug("Polling feed %s for new items" % feed_url)
        # Allow for parsing of this feed to fail without raising an exception
        
        try:
            p = feedparser.parse(feed_url)
        except:
            logging.error("Unable to parse feed %s" % feed_url)
            return None
        # Get a list of items for the feed and compare it to the database
        num_items = len(p.entries)
        logging.debug("Found %d items in feed %s" % (num_items,feed_url))
        # Find out which encoding the feed uses to avoid problems with hashlib
        # below
        enc = p.encoding
        new_items = 0
        for i in range(len(p.entries)):
            logging.debug("  Processing item %d" % i)
            title = p.entries[i].title
            logging.debug("    Title: %s" % title)
            link = p.entries[i].link
            logging.debug("    Link: %s" % link)
            date = p.entries[i].date_parsed
            date_struct = datetime.fromtimestamp(mktime(date))
            logging.debug("    Date: %s" % datetime.isoformat(date_struct))
            # Create a md5 hash of title and link, so that we can
            # easily tell duplicates in the feed. Could use guid for this, but
            # I don't trust feeds to use it correctly.
            h = hashlib.md5()
            hash_input = "%s|%s" % (title, link)
            h.update(hash_input.encode(enc))
            item_hash = h.hexdigest()
            logging.debug("    Hash: %s" % item_hash)
            # Check to see if item has already entered the database
            if not self._spigotdb.check_hash(item_hash):
                logging.debug("    Not in database")
                self._spigotdb.add_item(feed, link, title, item_hash,
                    account, date_struct)
                new_items += 1
            else:
                logging.debug("    Already in database")
        logging.info("Found %d new items in feed %s" % (new_items, feed_url))

    def get_format(self, feed):
        """Returns the format string from feeds.conf for the given feed."""
        
        return self.feeds_config.get(feed, "format")

class SpigotPost():
    """Handle the posting of syndicated content stored in the SpigotDB to the 
    statusnet account."""
    
    def __init__(self, db, spigot_feed):
        self._spigotdb = db
        self._spigotfeed = spigot_feed
        unposted_items = self._spigotdb.get_unposted_items()

    ### SpigotPost private methods

    def _check_duplicate(self, account, content):
        """Return True if the given content has been posted on the given
        statusnet account recently. Otherwise return False. Intended to prevent
        accidental duplicate posts."""
        
        pass

    ### SpigotPost public methods
    


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, \
                            format='%(asctime)s %(levelname)s: %(message)s')
    logging.debug("spigot startup")

    # Parse accounts configration file
    # Move all this to a posting class
#    logging.info("Loading accounts.conf")
#    accounts_config = ConfigParser.RawConfigParser()
#    if not accounts_config.read("accounts.conf"):
#        logging.error("Could not parse accounts.conf")
#        sys.exit(2)
    spigot_db = SpigotDB()
    spigot_feed = SpigotFeeds(spigot_db)
    spigot_post = SpigotPost(spigot_db, spigot_feed)
    
    
# TODO
# - Offering logging configuration?
# - Authentication type
# - statusbot v. identicurse bindings to statusnet
