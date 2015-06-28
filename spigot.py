#! /usr/bin/env python
#
# spigot is a rate limiter for aggregating syndicated content to pump.io
#
# (c) 2011-2015 by Nathan D. Smith <nathan@smithfam.info>
# (c) 2014 Craig Maloney <craig@decafbad.net>
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

# Standard library imports
import argparse
from datetime import datetime, timedelta
try:
    import json
except ImportError:
    import simplejson as json
import logging
import os
import re
import sqlite3
import sys
from time import mktime

# 3rd-party modules
import feedparser
from pypump import PyPump
from pypump import Client

SPIGOT_VERSION = "2.3.0"


def simple_verifier(url):
    print 'Please follow the instructions at the following URL:'
    print url
    return raw_input("Verifier: ")


class SpigotConfig(dict):
    """Extends the built-in dict type to provide a configuration interface for
    Spigot, keeping track of feeds polled and accounts configured for posting.
    """

    def __init__(self, path="spigot.json"):
        self.config_file = path
        self.no_config = True
        if os.path.exists(self.config_file):
            self.no_config = False

    def check_old_config(self):
        """Check existing configuration for pre-2.2 format and return True
        if the config needs to be updated."""

        formats = [self["feeds"][feed]["format"] for feed in self["feeds"]]
        for format in formats:
            if (("$t" in format) or ("$l" in format)):
                logging.debug("Existing config reflects pre-2.2 format")
                return True
            else:
                logging.debug("Existing config reflects post-2.2 format")
                return False

    def load(self):
        """Load the spigot json config file from the working directory
        and import it into the SpigotConfig dict object."""

        logging.debug("Loading %s" % self.config_file)
        # Start with a clean configuration object
        self.clear()
        try:
            self.update(json.loads(open(self.config_file, "r").read()))
        except IOError:
            logging.warning("Could not load configuration file")

    def save(self):
        "Convert the state of the SpigotConfig dict to json and save."

        logging.debug("Saving %s" % self.config_file)
        try:
            open(self.config_file, "w").write(json.dumps(self, indent=4))
            return True
        except IOError:
            logging.exception("Could not save configuration file")
            sys.exit(2)

    def add_feed(self):
        "Add a feed, account, interval, and format to the configuration."

        # TODO Add feature to specify to and cc for each feed
        self.load()
        account = None
        interval = None
        form = None

        print "Adding feed..."
        url = raw_input("Feed URL: ")
        # Test feed for presence, validity
        test_feed = None
        try:
            test_feed = feedparser.parse(url)
            logging.debug("Successfully parsed feed %s" % url)
        except:
            logging.warning("Could not parse feed %s" % url)
        account = raw_input("Account Webfinger ID (e.g. bob@example.com): ")
        # Verify that the account is valid
        # PyPump will authorize the account if necessary
        client = Client(
            webfinger=account,
            name="Spigot",
            type="native")
        try:
            pump = PyPump(client, verifier_callback=simple_verifier)
            print pump.me
        except:
            logging.exception("Could not verify account")
            sys.exit(2)

        # Obtain the posting interval
        valid_interval = False
        while not valid_interval:
            try:
                raw_inter = raw_input("Minimum time between posts (minutes): ")
                interval = int(raw_inter)
                valid_interval = True
            except:
                print "Invalid interval specified."
        print """Spigot formats your outgoing posts based on fields in the feed
              being scanned. Specify the field name surrounded by the '%'
              character to have it replaced with the corresponding value for
              the item (e.g. %title% or %link%)."""
        if test_feed:
            print """The following fields are present in an example item in
                     this feed:"""
            for field in test_feed["items"][0].keys():
                print field
        print """Next you will be prompted for the message format and
              optional title format for outgoing posts."""
        form = raw_input("Message format: ")
        title = raw_input("Title format (optional): ")

        # Put it all together
        feed = {}
        feed["account"] = account
        feed["interval"] = interval
        feed["format"] = form
        feed["title"] = title

        if "feeds" in self:
            self["feeds"][url] = feed
        else:
            feeds = {}
            feeds[url] = feed
            self["feeds"] = feeds

        self.save()

    def get_feeds(self):
        """Sets instance variable 'feeds' of feeds to check for new posts.
        Formatted in a tuple in the form of (url, account, interval, format)
        """

        feeds = self["feeds"]
        feeds_to_poll = []
        feeds_num = len(feeds)
        logging.debug("Found %d feeds in configuration" % feeds_num)
        for url in feeds.keys():
            logging.debug("Processing feed %s" % url)
            account = feeds[url]["account"]
            logging.debug("  Account: %s" % account)
            interval = feeds[url]["interval"]
            logging.debug("  Interval: %s min" % interval)
            form = feeds[url]["format"]
            logging.debug("  Format: %s" % form)
            feeds_to_poll.append((url, account, interval, form))
            logging.debug("  Added to list of feeds to poll")
        return feeds_to_poll


class SpigotDB():
    """Handle database calls for Spigot."""

    def __init__(self, path="spigot.db"):
        self.path = path
        self._connect()

    def _connect(self):
        """Establish the database connection for this instantiation."""

        # Check first for a database file
        new_db = False
        if not os.path.exists(self.path):
            new_db = True
            logging.debug("Database file %s does not exist" % self.path)
        det_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        try:
            self._db = sqlite3.connect(self.path, detect_types=det_types)
        except:
            logging.exception("Could not connect to database %s" % self.path)
            sys.exit(2)

        if new_db:
                self._init_db_tables()

    def _init_db_tables(self):
        """Initialize the database if it is new"""

        curs = self._db.cursor()
        # Figure out db tables based on tricklepost
        create_query = """create table items (feed text, link text,
                          message text, title text, date timestamp,
                          posted timestamp)"""
        curs.execute(create_query)
        self._db.commit()
        logging.debug("Initialized database tables")
        curs.close()

    def check_old_db(self):
        """Inspect schema of existing sqlite3 database and return True if
        the database needs to be upgraded to the post 2.2 schema."""

        curs = self._db.cursor()
        curs.execute("PRAGMA table_info(items);")
        cols = curs.fetchall()
        curs.close()
        if "message" not in [col[1] for col in cols]:
            logging.debug("Existing database lacks 'message' field")
            return True
        elif "title" not in [col[1] for col in cols]:
            logging.debug("Existing database lacks 'title' field")
            return True
        else:
            logging.debug("Existing database is up-to-date")
            return False

    def close(self):
        """Cleanup after the db is no longer needed."""

        self._db.close()
        logging.debug("Closed connection to database")

    def check_link(self, item_link):
        """Returns true if the specified link is already in the database."""

        curs = self._db.cursor()
        curs.execute("select * from items where link=?", [item_link])
        items = curs.fetchall()
        if len(items) > 0:
            return True
        else:
            return False
        curs.close()

    def add_item(self, feed_url, link, message, title, date):
        """Add an item to the database with the given parameters. Return True
        if successful."""

        curs = self._db.cursor()
        curs.execute("insert into items(feed, link, message, title, date) \
            values (?, ?, ?, ?, ?)", (feed_url, link, message, title, date))
        logging.debug("    Added item %s to database" % link)
        curs.close()

        self._db.commit()
        return True

    def get_unposted_items(self, feed):
        "Return a list of items in the database which have yet to be posted."

        curs = self._db.cursor()
        curs.execute("SELECT feed, link, message, title FROM items \
            where (posted is NULL AND feed=?) \
            ORDER BY date ASC", [feed])
        unposted_items = curs.fetchall()
        num_items = len(unposted_items)
        logging.debug("  Found %d unposted items in %s" % (num_items, feed))
        curs.close()
        return unposted_items

    def mark_posted(self, item_link, date=None):
        """Mark the given item posted by setting its posted datetime to now."""

        if not date:
            date = datetime.utcnow()
        curs = self._db.cursor()
        curs.execute("UPDATE items SET posted=? WHERE link=?",
                     (date, item_link))
        logging.debug("  Updated posted time of item %s in database"
                      % item_link)
        curs.close()
        self._db.commit()

    def get_latest_post(self, feed):
        """Return the datetime of the most recent item posted by spigot of the
        specified feed. If none have been posted, return None"""

        curs = self._db.cursor()
        curs.execute("SELECT posted FROM items WHERE \
            (feed=? AND posted is not NULL) ORDER BY posted DESC LIMIT 1",
                     [feed])
        result = curs.fetchone()
        curs.close()
        if result:
            logging.debug("  Latest post for feed %s is %s" % (feed,
                                                               result[0]))
            return result[0]
        else:
            logging.debug("  No items from feed %s have been posted" % feed)
            return None


class SpigotFeeds():
    """
    Handle the polling the specified feeds for new posts. Add new posts to
    database in preparation for posting to the specified Pump.io accounts.
    """

    def __init__(self, db, config):
        self._spigotdb = db
        self._config = config

    def format_element(self, feed, entry, element):
        """Returns an outgoing message for the given entry based on the given
        feed's configured format."""

        message = self._config["feeds"][feed][element]
        # Store a list of tuples containing format string and value
        replaces = []
        field_re = re.compile("%\w+%")
        fields = field_re.findall(message)
        for raw_field in fields:
            # Trim the % character from format
            field = raw_field[1:-1]
            if field in entry:
                # Make a special exception for the content element, which in
                # ATOM can appear multiple times per entry. Assume the element
                # with index=0 is the desired value.
                if field == "content":
                    logging.debug("    'content' field in formatting string")
                    value = entry.content[0].value
                else:
                    value = entry[field]
            else:
                value = ""
            replaces.append((raw_field, value))
        # Fill in the message format with actual values
        for string, val in replaces:
            message = message.replace(string, val)
        return message

    def poll_feeds(self):
        """Check the configured feeds for new posts."""

        feeds_to_poll = self._config.get_feeds()
        for url, account, interval, form in feeds_to_poll:
            self.scan_feed(url)

    def scan_feed(self, url):
        """Poll the given feed and then update the database with new info"""

        logging.debug("Polling feed %s for new items" % url)
        # Allow for parsing of this feed to fail without raising an exception
        try:
            p = feedparser.parse(url)
        except:
            logging.error("Unable to parse feed %s" % url)
            return None
        # Get a list of items for the feed and compare it to the database
        num_items = len(p.entries)
        logging.debug("Found %d items in feed %s" % (num_items, url))
        new_items = 0
        for i in range(len(p.entries)):
            logging.debug("  Processing item %d" % i)
            title = p.entries[i].title
            logging.debug("    Title: %s" % title)
            link = p.entries[i].link
            logging.debug("    Link: %s" % link)
            # Check for existence of published_parsed, fail back to updated
            if 'published_parsed' in p.entries[i]:
                date = p.entries[i].published_parsed
            else:
                date = p.entries[i].updated_parsed
            date_struct = datetime.fromtimestamp(mktime(date))
            logging.debug("    Date: %s" % datetime.isoformat(date_struct))
            # Craft the message based feed format string
            message = self.format_element(url, p.entries[i], "format")
            logging.debug("    Message: %s" % message)
            note_title = self.format_element(url, p.entries[i], "title")
            logging.debug("    Note Title: %s" % note_title)
            # Check to see if item has already entered the database
            if not self._spigotdb.check_link(link):
                logging.debug("    Not in database")
                self._spigotdb.add_item(url, link, message, note_title,
                                        date_struct)
                new_items += 1
            else:
                logging.debug("    Already in database")
        logging.debug("Found %d new items in feed %s" % (new_items, url))

    def feed_ok_to_post(self, feed):
        """Return True if the given feed is OK to post given its configured
        interval."""

        interval = int(self._config["feeds"][feed]["interval"])
        delta = timedelta(minutes=interval)
        posted = self._spigotdb.get_latest_post(feed)
        if posted:
            next = posted + delta
            now = datetime.utcnow()
            if now >= next:
                # post it
                logging.debug("  Feed %s is ready for a new post" % feed)
                return True
            else:
                logging.debug("  Feed %s has been posted too recently" % feed)
                logging.debug("  Next post at %s" % next.isoformat())
                return False
        else:
            # Nothing has been posted for this feed, so it is OK to post
            logging.debug("  Feed %s is ready for a new post" % feed)
            return True


class SpigotPost():
    """Handle the posting of syndicated content stored in the SpigotDB to the
    pump.io account.
    """

    def __init__(self, db, spigot_config, spigot_feed):
        self._spigotdb = db
        self._config = spigot_config
        self._spigotfeed = spigot_feed

    def post_items(self):
        """Handle the posting of unposted items.

        Iterate over each pollable feed and check to see if it is permissible
        to post new items based on interval configuration. Loop while it is OK,
        and terminate the loop when it becomes not OK. Presumably one or none
        will be posted each time this method runs."""

        for feed, account, interval, form in self._config.get_feeds():
            logging.debug("Finding eligible posts in feed %s" % feed)
            unposted_items = self._spigotdb.get_unposted_items(feed)
            # Initialize Pump.IO connection here
            client = Client(
                webfinger=account,
                type="native",
                name="Spigot")
            pump = PyPump(
                client=client,
                verifier_callback=simple_verifier)

            while self._spigotfeed.feed_ok_to_post(feed):
                try:
                    item = unposted_items.pop(0)
                except:
                    # Escape the loop if there are no new posts waiting
                    break
                feed = item[0]
                link = item[1]
                message = item[2]
                # Optional title
                title = None
                if item[3]:
                    title = item[3]

                try:
                    logging.info("  Posting item %s from %s to account %s"
                                 % (link, feed, account))
                    new_note = pump.Note(message, title)
                    new_note.to = pump.Public
                    new_note.send()
                    self._spigotdb.mark_posted(link)
                except:
                    logging.exception("  Unable to post item")


if __name__ == "__main__":
    spigot_config = SpigotConfig()
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", "-v", action="store_true")
    parser.add_argument("--add-feed", "-f", action="store_true")
    log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    parser.add_argument("--log-level", "-l", choices=log_levels,
                        default="WARNING")
    args = parser.parse_args()

    # Logging configuration
    logging.basicConfig(level=args.log_level,
                        format='%(asctime)s %(levelname)s: %(message)s')
    logging.debug("spigot startup")

    # No configuration present, doing welcom wagon
    if args.version:
        print "Spigot %s" % SPIGOT_VERSION
        sys.exit(0)
    if spigot_config.no_config:
        print "No configuration file now, running welcome wizard."
        spigot_config.add_feed()
        sys.exit(0)
    if args.add_feed:
        spigot_config.add_feed()
        sys.exit(0)

    # Normal operation
    spigot_config.load()
    # Check for pre-2.2 formatted spigot configuration file
    if not spigot_config.no_config:
        old_config = spigot_config.check_old_config()
        if old_config:
            logging.error("Config not upgraded for Spigot 2.2")
            logging.error("Please upgrade the config using the \
utils/convert.py script found in the source repository.")
            sys.exit(2)

    spigot_db = SpigotDB()
    # Test for pre-2.2 database structure
    if spigot_db.check_old_db():
        logging.error("Existing database not upgraded for the latest spigot")
        logging.error("Please upgrade the database using the \
utils/convert.py script found in the source repository.")
        sys.exit(2)

    spigot_feed = SpigotFeeds(spigot_db, spigot_config)
    spigot_feed.poll_feeds()
    spigot_post = SpigotPost(spigot_db, spigot_config, spigot_feed)
    spigot_post.post_items()
