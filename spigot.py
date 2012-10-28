#! /usr/bin/env python
#
# spigot is a rate limiter for aggregating syndicated content to StatusNet
#
# (c) 2011, 2012 by Nathan Smith <nathan@smithfam.info>
#
# Portions adapted from Identicurse (http://identicurse.net)
# (C) 2010-2012 Reality <tinmachin3@gmail.com> and
# Psychedelic Squid <psquid@psquid.net>
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
import feedparser
import hashlib
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
import urllib

# Bundled modules
from statusnet import StatusNet

# Globals
# TODO Get "production" keys, these are the "dev" set
oauth_keys = {
    "identi.ca": {
        "consumer_key": "197fe6cae1e4996187be6398f0264647",
        "consumer_secret": "df84016bce5050b1cfc6b280410c4b1c"
    }
}
# Via identicurse below
domain_regex = re.compile("http(s|)://(www\.|)(.+?)(/.*|)$")


class SpigotConfig(dict):
    """Extends the built-in dict type to provide a configuration interface 
    for Spigot, keeping track of feeds polled and accounts configured for 
    posting.
    """

    # See identicurse's config.py for the inspiration for this model

    def __init__(self, path="spigot.json"):
        self.config_file = path
        self.current_oauth_user = None
        self.no_config = True
        if os.path.exists(self.config_file):
            self.no_config = False

    def load(self):
        """Load the spigot0 json config file from the user's home directory
        and import it into the SpigotConfig dict object."""

        logging.debug("Loading %s" % self.config_file)
        # Start with a clean configuration object
        self.clear()
        try:
            # Validate here
            self.update(json.loads(open(self.config_file, "r").read()))
        except IOError:
            logging.warning("Could not load configuration file")

    def save(self):
        "Convert the state of the SpigotConfig dict to json and save."

        logging.debug("Saving spigot.json")
        try:
            # Validate here
            open(self.config_file, "w").write(json.dumps(self, indent=4))
        except IOError:
            logging.exception("Could not save configuration file")
            sys.exit(2)

    def store_oauth_tokens(self, token, secret):
        "Store the given oauth token and token_secret temporarily"

        # Have to store these tokens temporarily as a shim to be compatible
        # with Identicurse's single-user paradigm.
        logging.debug("Received oauth tokens")
        self.temp_oauth_token = token
        self.temp_oauth_token_secret = secret

    def add_user(self):
        "Interactively add a new user to the configuration."

        # Adapted from Identicurse - http://b1t.it/cjLm
        self.load()

        print "Adding user"
        raw_api_path = raw_input("API path [https://identi.ca/api]: ")
        if raw_api_path == "":
            api_path = "https://identi.ca/api"
        else:
            if len(raw_api_path) < 7 or raw_api_path[:7] != "http://" and\
                    raw_api_path[:8] != "https://":
                raw_api_path = "http://" + raw_api_path
            if len(raw_api_path) >= 7 and raw_api_path[:5] != "https":
                https_api_path = "https" + raw_api_path[4:]
                response = raw_input("Use HTTPS instead? [Y/n] ").upper()
                if response == "":
                    response = "Y"
                if response[0] == "Y":
                    api_path = https_api_path
                else:
                    api_path = raw_api_path

        # Authorization type: OAuth or U/P
        use_oauth = raw_input("Use OAuth [Y/n]? ").upper()
        if use_oauth == "":
            use_oauth = "Y"
        if use_oauth[0] == "Y":
            instance = domain_regex.findall(api_path)[0][2]
            if instance in oauth_keys:
                auth_type = "oauth"
            else:
                print "No oauth keys available fo this instance."
                print "Reverting authentication to uname/pass."
                auth_type = "userpass"
        else:
            auth_type = "userpass"

        # Set up userpass method
        if auth_type == "userpass":
            username = raw_input("Username: ")
            password = raw_input("Password: ")

        # Construct user configuration dict, starting with global options
        user = {}
        user["api_path"] = api_path
        user["auth_type"] = auth_type

        account = None
        idnum = None
        if auth_type == "oauth":
            # Initialize the Oauth relationship
            init_sn = SpigotConnect(api_path, auth_type="oauth",
                consumer_key=oauth_keys[instance]["consumer_key"],
                consumer_secret=oauth_keys[instance]["consumer_secret"],
                save_oauth_credentials=self.store_oauth_tokens)
            # Construct the user configuration dict
            account, idnum = init_sn.get_account_info()
            user["consumer_key"] = oauth_keys[instance]["consumer_key"]
            user["consumer_secret"] = oauth_keys[instance]["consumer_secret"]
            user["oauth_token"] = self.temp_oauth_token
            user["oauth_token_secret"] = self.temp_oauth_token_secret

        else:
            init_sn = SpigotConnect(api_path, username, password)
            account, idnum = init_sn.get_account_info()
            user["username"] = username
            user["password"] = password

        user["id"] = idnum

        # Finish constructing the user configuration
        if "accounts" in self:
            self["accounts"][account] = user
        else:
            users = {}
            users[account] = user
            self["accounts"] = users
        self.save()
        # Clean up the kludge
        self.temp_oauth_token = None
        self.temp_oauth_token_secret = None

    def add_feed(self):
        "Add a feed, account, interval, and format to the configuration."

        self.load()
        if not "accounts" in self:
            logging.error("No accounts configured.")
            sys.exit(2)
        account = None
        interval = None
        form = None

        print "Adding feed..."
        url = raw_input("Feed URL: ")
        accounts = self["accounts"].keys()
        print "Choose an account:"
        for i in range(len(accounts)):
            print "%d. %s" % (i,accounts[i])

        valid_account = False
        while not valid_account:
            try:
                account_raw = int(raw_input("Number: "))
                try:
                    account = accounts[account_raw]
                    valid_account = True
                except:
                    print "Choice out of range."
            except:
                print "Not a number."
        valid_interval = False
        while not valid_interval:
            try:
                raw_inter = raw_input("Minimum time between posts (minutes): ")
                interval = int(raw_inter)
                valid_interval = True
            except:
                print "Invalide interval specified."
        print """Spigot formats your outgoing posts based on fields in the feed
              being scanned. Use the following substitutions:
              $t - title
              $l - link"""
        form = raw_input("Format: ")
        
        # Put it all together
        feed = {}
        feed["account"] = account
        feed["interval"] = interval
        feed["format"] = form
        
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

    # SpigotConfig private methods below
    def _validate_config(self):
        """Returns True if the json configuration file contains the minimum
        necessary elements for operation in a proper format."""

        # TODO Write this
        pass


class SpigotConnect(StatusNet):
    """Extends StatusNet class to provide connectivity to StatusNet instances.
    Provides some additional features for Spigot."""

    # API returns a full user profile upon successful auth
    def get_account_info(self):
        """Retrieve the JSON account profile information which comes with a 
        successful verify credentials and return the account URL and id."""

        resp = self._StatusNet__makerequest("account/verify_credentials")
        url = resp["statusnet_profile_url"]
        idnum = resp["id"]
        return url, idnum


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
            logging.debug("Database file %s does not exist" % self.path)
        try:
            self._db = sqlite3.connect(self.path,
                detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
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
            hash text, date timestamp, posted timestamp)"""
        curs.execute(create_query)
        self._db.commit()
        logging.debug("Initialized database tables")
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
            
    def add_item(self, feed_url, link, title, item_hash, date):
        """Add an item to the database with the given parameters. Return True
        if successful."""
        
        curs = self._db.cursor()
        curs.execute("insert into items(feed, link, title, hash, date) \
            values (?, ?, ?, ?, ?)", (feed_url, link, title, item_hash, date))
        logging.debug("    Added item %s to database" % item_hash)
        curs.close()
        
        self._db.commit()
        
    def get_unposted_items(self, feed):
        """Return a list of items in the database which have yet to be sent
        through to the specified statusnet account."""
        
        curs = self._db.cursor()
        curs.execute("SELECT * FROM items where (posted is NULL AND feed=?) \
            ORDER BY date ASC",[feed])
        unposted_items = curs.fetchall()
        num_items = len(unposted_items)
        logging.debug("  Found %d unposted items in %s" % (num_items,feed))
        curs.close()
        return unposted_items

    def mark_posted(self, item_hash, date=None):
        """Mark the given item posted by setting its posted datetime to now."""
        
        if not date:
            date = datetime.now()
        curs = self._db.cursor()
        curs.execute("UPDATE items SET posted=? WHERE hash=?",
            (date, item_hash))
        logging.debug("  Updated posted time of item %s in database"
            % item_hash)
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
    database in preparation for posting to the specified StatusNet accounts.
    """

    def __init__(self, db, config):
        self._spigotdb = db
        self._config = config

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
        logging.debug("Found %d items in feed %s" % (num_items,url))
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
            date = p.entries[i].published_parsed
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
                self._spigotdb.add_item(url, link, title, item_hash,
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
            now = datetime.now()
            if now >= next:
                #post it                
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
    """
    Handle the posting of syndicated content stored in the SpigotDB to the 
    statusnet account.
    """
    
    def __init__(self, db, spigot_config, spigot_feed):
        self._spigotdb = db
        self._config = spigot_config
        self._spigotfeed = spigot_feed

    ### SpigotPost private methods

    def _get_account_posts(self, account, idnum):
        """Return a feedparser object of the account's feed or false if 
        unparseable."""

        api = self._config["accounts"][account]["api_path"]
        feed_url = "%s/statuses/user_timeline/%s.atom" % (api,idnum)
        try:
            return feedparser.parse(feed_url)
        except:
            logging.warning("  Could not parse account feed %s" % feed_url)
            return False

    def _check_duplicate(self, posts, message, item_hash):

       """Return True if the given content has been posted on the given
       statusnet account recently. Otherwise return False. Intended to prevent
       accidental duplicate posts."""

       # Infer the username based on the text before ":" in the title element
       # of the first post in the feed. This should probably be done with an 
       # API call if possible.

       try:
           for i in range(len(posts.entries)):
               if message == posts.entries[i].title:
                   # Update the posted time in the database
                   real_date = posts.entries[i].date_parsed
                   date = datetime.fromtimestamp(mktime(real_date))
                   logging.debug("  Item %s already been posted. Correcting."
                                % item_hash)
                   self._spigotdb.mark_posted(item_hash, date)
                   return True
           return False
       except TypeError:
           logging.warning("  Could not check account %s for duplicates to \
               item %s" % (account,item_hash))
           return false

    def _shorten_url(self, url):
        """Return a shortened URL using the b1t.it service, or return the
        unmodified URL if the service is unavailable."""

        params = urllib.urlencode({"url":url})
        try:
            resp = urllib.urlopen("http://b1t.it/", params).read()
        except:
            logging.exception("  Could not contact URL-shortening service")
            return url
        result = {}
        try:
            result.update(json.loads(resp))
        except:
            logging.exception("  Invalid response from URL-shortening service")
            return url
        if result.has_key("url"):
            short_url = result["url"]
            logging.debug("  Retrieved shortened url %s for %s" % 
                          (short_url, url))
            return short_url
        else:
            logging.error("  Could not get short url for %s" % url)
            return url


    def _format_message(self, feed, link, title, form, limit):
        """Return a string formatted according to the feed's configuration.
        If the string is too long for the maximum post length for the server,
        first attempt to shorten any included URL, and then truncate with an
        ellipse.
        
        Replacement strings:
        $t : title
        $l : link"""
        
        message = form.replace("$t",title)
        message = message.replace("$l",link)
        # TODO get maxlength from statusnet server via api
        shortened_url = False
        size = len(message)
        # Allow 3 extra chars for '...'
        trunc = (size - limit) + 3
        logging.debug("  Length of message is %d chars" % size)
        # Limit=0 indicates no limit, skip truncation efforts
        if size > limit > 0:
            logging.warning("  Message is longer than max length for server.")
            while len(message) > limit:
                # First try to shorten the URL if included
                if (not shortened_url) and ("$l" in form):
                    logging.debug("  Attempting to shorten URL in post")
                    shortened_url = self._shorten_url(link)
                    message = form.replace("$t",title)
                    message = message.replace("$l",shortened_url)
                    shortened_url = True
            # Otherwise truncate the message using an ellipse
                else:
                # Try shortening the title
                # Trying to avoid breaking the link, if possible
                # This code is not very smart, hopefully people will not
                # input stuff longer than their max server length :-(
                    if "$t" in raw_format:
                        logging.debug("  Truncating title")
                        new_title = title[:-trunc] + '...'
                        message = form.replace("$t",new_title)
                        message = message.replace("$l",shortened_url)
                    else:
                        logging.warning("  Truncating message - could break \
                                        links")
                        message = message[:137] + '...'
        logging.debug("  Posted message will be %s" % message)
        return message

    ### SpigotPost public methods

    def post_items(self):
        """Handle the posting of unposted items.
        
        
        Iterate over each pollable feed and check to see if it is permissible
        to post new items based on interval configuration. Loop while it is OK,
        and terminate the loop when it becomes not OK. Presumably one or none 
        will be posted each time this method runs."""
        
        for feed, account, interval, form in self._config.get_feeds():
            if not account in self._config["accounts"]:
                logging.error("Account %s not configured, unable to post." 
                                  % account)
                sys.exit(2)
            logging.debug("Finding eligible posts in feed %s" % feed)
            unposted_items = self._spigotdb.get_unposted_items(feed)
            # Initialize Statusnet connection here
            sn = None
            ac = self._config["accounts"][account]
            if ac["auth_type"] == "oauth":
                sn = SpigotConnect(ac["api_path"], auth_type="oauth",
                                      consumer_key=ac["consumer_key"],
                                      consumer_secret=ac["consumer_secret"],
                                      oauth_token=ac["oauth_token"],
                                      oauth_token_secret=\
                                          ac["oauth_token_secret"])
            else:
                sn = SpigotConnect(ac["api_path"], ac["username"], 
                                   ac["password"])
            url, idnum = sn.get_account_info()
            limit = int(sn.statusnet_config()["site"]["textlimit"])
            logging.debug("  Text limit for this instance is %d" % limit)
            
            while self._spigotfeed.feed_ok_to_post(feed):
                try:
                    item = unposted_items.pop(0)
                except:
                    # Escape the loop if there are no new posts waiting
                    break
                link = item[1]
                title = item[2]
                item_hash = item[3]
                message = self._format_message(feed, link, title, form, limit)
                # Make sure that it has not been posted recently
                user_posts = self._get_account_posts(account, idnum)
                logging.debug("  Evaluating item %s for posting." % item_hash)
                if not self._check_duplicate(user_posts, message, item_hash):
                    logging.info("  Posting item %s from %s to account %s" 
                                 % (item_hash,feed,account))

                    try:
                        sn.statuses_update(message.encode(user_posts.encoding),
                                       "Spigot")
                        self._spigotdb.mark_posted(item_hash)
                    except:
                        logging.exception("  Unable to post item")


if __name__ == "__main__":
    spigot_config = SpigotConfig()

    parser = argparse.ArgumentParser()
    parser.add_argument("--add-account","-a",action="store_true")
    parser.add_argument("--add-feed","-f",action="store_true")
    log_levels = ["DEBUG","INFO","WARNING","ERROR","CRITICAL"]
    parser.add_argument("--log-level","-l",choices=log_levels,
                        default="WARNING")
    args = parser.parse_args()

    # Logging configuration
    logging.basicConfig(level=args.log_level, \
                            format='%(asctime)s %(levelname)s: %(message)s')
    logging.debug("spigot startup")

    # No configuration present, doing welcom wagon
    if spigot_config.no_config:
        print "No configuration file now, running welcome wizard."
        spigot_config.add_user()
        spigot_config.add_feed()
        sys.exit(0)
    if args.add_account:
        spigot_config.add_user()
        sys.exit(0)
    if args.add_feed:
        spigot_config.add_feed()
        sys.exit(0)

    # Normal operation
    spigot_config.load()
    spigot_db = SpigotDB()
    spigot_feed = SpigotFeeds(spigot_db, spigot_config)
    spigot_feed.poll_feeds()
    spigot_post = SpigotPost(spigot_db, spigot_config, spigot_feed)
    spigot_post.post_items()
