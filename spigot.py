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
from datetime import datetime, timedelta
import hashlib
import logging
import os
import sqlite3
import sys
from time import mktime

import feedparser

# import statusnet


class SpigotDB():
    """
    Handle database calls for Spigot
    """
 
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
            self._db = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
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
        logging.debug("    add_item date type: %s" % type(date))
        logging.debug("    Added item %s to database" % item_hash)
        curs.close()
        
        self._db.commit()
        
    def get_unposted_items(self, feed):
        """Return a list of items in the database which have yet to be sent
        through to the specified statusnet account."""
        
        curs = self._db.cursor()
        curs.execute("SELECT * FROM items where (posted is NULL AND feed=?)",
            [feed])
        unposted_items = curs.fetchall()
        logging.info("Found %d unposted items in feed %s" % (len(unposted_items),feed))
        curs.close()
        return unposted_items

    def mark_posted(self, item_hash):
        """Mark the given item posted by setting its posted datetime to now."""
        
        now = datetime.now()
        logging.debug("mark_posted now type: %s" % type(now))
        curs = self._db.cursor()
        curs.execute("UPDATE items SET posted=? WHERE hash=?",(now, item_hash))
        logging.debug("Updated posted time of item %s in database" % item_hash)
        curs.close()
        self._db.commit()
    
    def get_latest_post(self, feed):
        """Return the datetime of the most recent item posted by spigot of the
        specified feed. If none have been posted, return None"""
        
        curs = self._db.cursor()
        # Try selecting the dang date to see if that gets a correct type!!!
        #curs.execute("SELECT date FROM items WHERE feed=? ORDER BY date LIMIT 1", [feed])
        curs.execute("SELECT posted FROM items WHERE (feed=? AND posted is not NULL) ORDER BY posted DESC LIMIT 1",[feed])    
        result = curs.fetchone()
        curs.close()
        if result:
            print type(result[0])
            logging.debug("Latest post for feed %s is %s" % (feed, 
                result[0]))
            return result[0]
        else:
            logging.debug("No items from feed %s have been posted" % feed)
            return None
        

class SpigotFeeds():
    """
    Handle the parsing of feeds.conf configuration file and polling the
    specified feeds for new posts. Add new posts to database in preparation for
    posting to the specified StatusNet accounts.

    """

    def __init__(self, db):
        self._spigotdb = db
        logging.debug("Loading feeds.conf")
        self._feeds_config = ConfigParser.RawConfigParser()
        if not self._feeds_config.read("feeds.conf"):
            logging.error("Could not parse feeds.conf")
            sys.exit(2)
        self.feeds_to_poll = []     

    def parse_config(self):
        """Returns a list of syndicated feeds to check for new posts."""
        
        # Make feeds to poll an internal variable for this function
        feeds_to_poll = []
        feeds = self._feeds_config.sections()
        feeds_num = len(feeds)
        if feeds_num == 0:
            logging.warning("No feeds found in feeds.conf")
        else:
            logging.info("Found %d feeds in feeds.conf" % feeds_num)
        for feed in feeds:
            logging.debug("Processing feed %s" % feed)
            
            # Ensure that the feed section has the needed attributes
            # If not, treat as a non-fatal error, but warn the user
            if ( self._feeds_config.has_option(feed, "url") &
                     self._feeds_config.has_option(feed, "account") &
                     self._feeds_config.has_option(feed, "interval") ):
                url = self._feeds_config.get(feed, "url")
                logging.debug("  URL: %s" % url)
                account = self._feeds_config.get(feed, "account")
                logging.debug("  Account: %s" % account)
                logging.debug("  Interval: %s min" % self._feeds_config.get(feed,
                    "interval"))
                feeds_to_poll.append((feed, url, account))
                logging.debug("  Added to list of feeds to poll")
                
            else:
                logging.warning("  Missing necessary options, skipping")
        return feeds_to_poll

    def poll_feeds(self):
        """Check the configured feeds for new posts."""
        
        self.feeds_to_poll = self.parse_config()
        for feed, feed_url, account in self.feeds_to_poll:
            self.scan_feed(feed, feed_url, account)

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
        
        return self._feeds_config.get(feed, "format")
        
    def get_feed_interval(self, feed):
        """Return the interval from feeds.conf of the specified feed."""
        
        return self._feeds_config.get(feed, "interval")
        
    def feed_ok_to_post(self, feed):
        """Return True if the given feed is OK to post given its configured
        interval."""
        
        interval = int(self.get_feed_interval(feed))
        delta = timedelta(minutes=interval)
        posted = self._spigotdb.get_latest_post(feed)
        if posted:
            next = posted + delta
            now = datetime.now()
            if now >= next:
                #post it                
                logging.info("Feed %s is ready for a new post" % feed)
                return True
            else:
                logging.info("Feed %s has been posted too recently" % feed)
                logging.info("Next post at %s" % next.isoformat())
                return False
        else:
            # Nothing has been posted for this feed, so it is OK to post
            return True
        
        


class SpigotPost():
    """
    Handle the posting of syndicated content stored in the SpigotDB to the 
    statusnet account.
    """
    
    def __init__(self, db, spigot_feed):
        self._spigotdb = db
        self._spigotfeed = spigot_feed
        self._accounts_config = ConfigParser.RawConfigParser()
        if not self._accounts_config.read("accounts.conf"):
            logging.error("Could not parse accounts.conf")
            sys.exit(2)
        self.post_items()

    ### SpigotPost private methods

    def _check_duplicate(self, account, content):
        """Return True if the given content has been posted on the given
        statusnet account recently. Otherwise return False. Intended to prevent
        accidental duplicate posts."""
        
        pass

    ### SpigotPost public methods




    def post_items(self):
        """Handle the posting of unposted items.
        
        
        Iterate over each pollable feed and check to see if it is permissible to
        post new items based on interval configuration. Loop while it is OK, and 
        terminate the loop when it becomes not OK. Presumably one or none will 
        be posted each time this method runs."""
        
        feeds = self._spigotfeed.feeds_to_poll
        for feed, feed_url, account in feeds:
            logging.debug("Determining if posts in feed %s are eligible for posting" % feed)
            unposted_items = self._spigotdb.get_unposted_items(feed)
            while self._spigotfeed.feed_ok_to_post(feed):
                try:
                    item = unposted_items.pop()
                except:
                    # Escape the loop if there are no new posts waiting
                    break
                link = item[1]
                title = item[2]
                item_hash = item[3]
                logging.info("Posting item %s from %s feed to account %s" % (item_hash,feed,account))
                self._spigotdb.mark_posted(item_hash)
                    
                
                
                
       
        
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, \
                            format='%(asctime)s %(levelname)s: %(message)s')
    logging.debug("spigot startup")
    spigot_db = SpigotDB()
    spigot_feed = SpigotFeeds(spigot_db)
    # Make this behavior configurable
    spigot_feed.poll_feeds()
    spigot_post = SpigotPost(spigot_db, spigot_feed)
    
    
# TODO
# - Offering logging configuration?
# - Authentication type
# - statusbot v. identicurse bindings to statusnet
