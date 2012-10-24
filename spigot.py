#! /usr/bin/env python
#
# spigot is a rate limiter for aggregating syndicated content to StatusNet
#
# (c) 2011, 2012 by Nathan Smith <nathan@smithfam.info>
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
from datetime import datetime, timedelta
import hashlib
try:
    import json
except ImportError:
    import simplejson as json
import logging
import os
import sqlite3
import sys
from time import mktime

# 3rd-party modules
import feedparser
# import statusnet

class SpigotConfig(dict):
    """Extends the built-in dict type to provide a configuration interface 
    for Spigot, keeping track of feeds polled and accounts configured for 
    posting.
    """

    # See identicurse's config.py for the inspiration for this model
    config_file = "spigot.json"

    def __init__(self):
        pass

    def load(self):
        """Load the spigot0 json config file from the user's home directory
        and import it into the SpigotConfig dict object."""

        logging.debug("Loading spigot.json")
        # Start with a clean configuration object
        self.clear()
        try:
            self.update(json.loads(open(self.config_file, "r").read()))
        except IOError:
            logging.error("Could not load configuration file")
            sys.exit(2)

    def save(self):
        "Convert the state of the SpigotConfig dict to json and save."

        logging.debug("Saving spigot.json")
        try:
            open(self.config_file, "w").write(json.dumps(self, indent=4))
        except IOError:
            logging.error("Could not save configuration file")

    def get_feeds(self):
        """Returns a list of syndicated feeds to check for new posts."""
        
        # Make feeds to poll an internal variable for this function
        feeds = self["feeds"]
        feeds_to_poll = []
        feeds_num = len(feeds)
        if feeds_num == 0:
            logging.warning("No feeds found in feeds.conf")
        else:
            logging.info("Found %d feeds in feeds.conf" % feeds_num)
        for feed in feeds.keys():
            # Ensure that the feed section has the needed attributes
            # If not, treat as a non-fatal error, but warn the user
            if ( ( "url" in feeds[feed] ) & 
                 ( "account" in feeds[feed] ) & 
                 ( "interval" in feeds[feed] ) ):
                url = feeds[feed]["url"]
                logging.debug("Processing feed %s" % feed)
                logging.debug("  URL: %s" % url)
                account = feeds[feed]["account"]
                logging.debug("  Account: %s" % account)
                interval = feeds[feed]["interval"]
                logging.debug("  Interval: %s min" % interval)
                feeds_to_poll.append((feed, url, account))
                logging.debug("  Added to list of feeds to poll")
                
            else:
                logging.warning("  Missing necessary options, skipping")
        return feeds_to_poll


class SpigotConnect():

###############################################################################
# Below code adapted from Identicurse
###############################################################################

    def init_config(self, config):
        config.config.load(os.path.join(self.path, "config.json"))
        print msg['NoConfigFoundInfo'] % (config.config.filename)
        print msg['IdenticurseSupportOAuthInfo']
        use_oauth = raw_input("Use OAuth [Y/n]? ").upper()
        if use_oauth == "":
            use_oauth = "Y"
        if use_oauth[0] == "Y":
            config.config['use_oauth'] = True
        else:
            config.config['use_oauth'] = False
        if not config.config['use_oauth']:
            config.config['username'] = raw_input("Username: ")
            config.config['password'] = getpass.getpass("Password: ")
        api_path = raw_input("API path [%s]: " % (config.config['api_path']))
        if api_path != "":
            if len(api_path) < 7 or api_path[:7] != "http://" and\
                    api_path[:8] != "https://":
                api_path = "http://" + api_path
            if len(api_path) >= 7 and api_path[:5] != "https":
                https_api_path = "https" + api_path[4:]
                response = raw_input(msg['NotUsingHTTPSInfo'] % (
                        https_api_path)).upper()
                if response == "":
                    response = "Y"
                if response[0] == "Y":
                    api_path = https_api_path
            config.config['api_path'] = api_path
        update_interval = raw_input(msg['UpdateIntervalInput'] % (
                config.config['update_interval']))
        if update_interval != "":
            try:
                config.config['update_interval'] = int(update_interval)
            except ValueError:
                print msg['InvalidUpdateIntervalError'] % (
                    config.config['update_interval'])
        notice_limit = raw_input(msg['NumberNoticesInput'] % (
                config.config['notice_limit']))
        if notice_limit != "":
            try:
                config.config['notice_limit'] = int(notice_limit)
            except ValueError:
                print msg['InvalidNumberNoticesError'] % (
                    config.config['notice_limit'])
        # try:
        if config.config['use_oauth']:
            instance = helpers.domain_regex.findall(
                config.config['api_path'])[0][2]
            if not instance in oauth_consumer_keys:
                print msg['NoLocallyConsumerKeysInfo']
                req = urllib2.Request("http://identicurse.net/api_keys.json")
                resp = urllib2.urlopen(req)
                api_keys = json.loads(resp.read())
                if not instance in api_keys['keys']:
                    print msg["NoRemoteConsumerKeysInfor"]
                    temp_conn = StatusNet(config.config['api_path'],
                                          auth_type="oauth",
                                          consumer_key="anonymous",
                                          consumer_secret="anonymous",
                                          save_oauth_credentials=\
                                              config.store_oauth_keys)
                    config.config["consumer_key"] = "anonymous"
                    config.config["consumer_secret"] = "anonymous"
                else:
                    temp_conn = StatusNet(config.config['api_path'],
                                          auth_type="oauth",
                                          consumer_key=\
                                              api_keys['keys'][instance],
                                          consumer_secret=\
                                              api_keys['secrets'][instance],
                                          save_oauth_credentials=\
                                              config.store_oauth_keys)
                    config.config["consumer_key"] = api_keys['keys'][instance]
                    config.config["consumer_secret"] =\
                        api_keys['secrets'][instance]
            else:
                temp_conn = StatusNet(config.config['api_path'],\
                                      auth_type="oauth",
                                      consumer_key=\
                                          oauth_consumer_keys[instance],
                                      consumer_secret=\
                                          oauth_consumer_secrets[instance],
                                      save_oauth_credentials=\
                                          config.store_oauth_keys)
        else:
            temp_conn = StatusNet(config.config['api_path'],
                                  config.config['username'],
                                  config.config['password'])
        # except Exception, (errmsg):
        #     sys.exit("Couldn't establish connection: %s" % (errmsg))
        print msg["ConfigIsOKInfo"]
        config.config.save()

    def start_connection(self, config):
        try:
            if config.config["use_oauth"]:
                instance = helpers.domain_regex.findall(
                    config.config['api_path'])[0][2]
                if "consumer_key" in config.config:
                    self.conn = StatusNet(config.config['api_path'],
                                          auth_type="oauth",
                                          consumer_key=\
                                              config.config["consumer_key"],
                                          consumer_secret=\
                                              config.config["consumer_secret"],
                                          oauth_token=\
                                              config.config["oauth_token"],
                                          oauth_token_secret=\
                                              config.config[\
                                                  "oauth_token_secret"],
                                          save_oauth_credentials=\
                                              config.store_oauth_keys)
                elif not instance in oauth_consumer_keys:
                    print msg['NoLocallyConsumerKeysInfo']
                    req = urllib2.Request(
                        "http://identicurse.net/api_keys.json")
                    resp = urllib2.urlopen(req)
                    api_keys = json.loads(resp.read())
                    if not instance in api_keys['keys']:
                        sys.exit(msg['YourInstanceAPIKeysError'] % (locals()))
                    else:
                        self.conn = StatusNet(config.config['api_path'],
                                              auth_type="oauth",
                                              consumer_key=\
                                                  api_keys['keys'][instance],
                                              consumer_secret=\
                                                 api_keys['secrets'][instance],
                                              oauth_token=\
                                                  config.config["oauth_token"],
                                              oauth_token_secret=\
                                                  config.config[\
                                                      "oauth_token_secret"],
                                              save_oauth_credentials=\
                                                  config.store_oauth_keys)
                        config.config["consumer_key"] =\
                            api_keys['keys'][instance]
                        config.config["consumer_secret"] =\
                            api_keys['secrets'][instance]
                        config.config.save()
                else:
                    self.conn = StatusNet(config.config['api_path'],
                                          auth_type="oauth",
                                          consumer_key=\
                                              oauth_consumer_keys[instance],
                                          consumer_secret=\
                                              oauth_consumer_secrets[instance],
                                          oauth_token=\
                                              config.config["oauth_token"],
                                          oauth_token_secret=\
                                              config.config[\
                                                  "oauth_token_secret"],
                                          save_oauth_credentials=\
                                              config.store_oauth_keys)
            else:
                self.conn = StatusNet(config.config['api_path'],
                                      config.config['username'],
                                      config.config['password'])
        except Exception, (errmsg):
            sys.exit("ERROR: Couldn't establish connection: %s" % (errmsg))


###############################################################################
# End code from identicurse
###############################################################################

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
            
    def add_item(self, feed_name, link, title, item_hash, date):
        """Add an item to the database with the given parameters. Return True
        if successful."""
        
        curs = self._db.cursor()
        curs.execute("insert into items(feed, link, title, hash, date) \
            values (?, ?, ?, ?, ?)", (feed_name, link, title, item_hash, date))
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
        logging.info("  Found %d unposted items in feed %s" % (num_items,feed))
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
        for feed, feed_url, account in feeds_to_poll:
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
                self._spigotdb.add_item(feed, link, title, item_hash,
                    date_struct)
                new_items += 1
            else:
                logging.debug("    Already in database")
        logging.info("Found %d new items in feed %s" % (new_items, feed_url))

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
                logging.info("  Feed %s is ready for a new post" % feed)
                return True
            else:
                logging.info("  Feed %s has been posted too recently" % feed)
                logging.info("  Next post at %s" % next.isoformat())
                return False
        else:
            # Nothing has been posted for this feed, so it is OK to post
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
        self.post_items()

    ### SpigotPost private methods

    def _get_account_posts(self, account):
        """Pares the recent posts of the specified account for duplicate
        checking."""
        
        feed_url = "%s/rss" % account
        try:
            self._acct_parse = feedparser.parse(feed_url)
        except:
            logging.warning("  Unable to parse account feed %s" % feed_url)
            return False

    def _check_duplicate(self, account, message, item_hash):

       """Return True if the given content has been posted on the given
       statusnet account recently. Otherwise return False. Intended to prevent
       accidental duplicate posts."""

       username = self._accounts_config.get(account, "username")
       formatted_message = "%s: %s" % (username, message)
       duplicate = False
       for i in range(len(self._acct_parse.entries)):
           if formatted_message == self._acct_parse.entries[i].title:
               duplicate = True
               # Update the posted time in the database
               real_date = self._acct_parse.entries[i].date_parsed
               date = datetime.fromtimestamp(mktime(real_date))
               logging.warn("  Item %s has already been posted. Correcting."
                   % item_hash)
               self._spigotdb.mark_posted(item_hash, date)
       return duplicate

    def _format_message(self, feed, link, title):
        """Return a string formatted according to the feed's configuration.
        If the string is too long for the maximum post length for the server,
        first attempt to shorten any included URL, and then truncate with an
        ellipse.
        
        Replacement strings:
        $t : title
        $l : link"""
        
        raw_format = self._config["feeds"][feed]["format"]
        message = raw_format.replace("$t",title)
        message = message.replace("$l",link)
        # TODO get maxlength from statusnet server via api
        shortened_url = False
        size = len(message)
        # Allow 3 extra chars for '...'
        trunc = (size - 140) + 3
        logging.debug("  Length of message is %d chars" % size)
        if size > 140:
            logging.info("  Message is longer than max length for server.")
        while len(message) > 140:
            # First try to shorten the URL if included
            if (not shortened_url) and ("$l" in raw_format):
                # Get shortened URL for link
                krunch = krunchlib.Krunch("http://is.gd/api.php?longurl=")
                try:
                    shortened_url = krunch.krunch_url(link)
                    logging.info("  Shortened URL")
                    message = raw_format.replace("$t",title)
                    message = message.replace("$l",shortened_url)
                except:
                    logging.warn("  Unable to shorten URL")
                    # Do not try to shorten endlessly
                    shortened_url = True
            # Otherwise truncate the message using an ellipse
            else:
                # Try shortening the title
                # Trying to avoid breaking the link, if possible
                # This code is not very smart, hopefully people will not
                # input stuff longer than their max server length :-(
                if "$t" in raw_format:
                    logging.info("  Truncating title")
                    new_title = title[:-trunc] + '...'
                    message = raw_format.replace("$t",new_title)
                    message = message.replace("$l",shortened_url)
                else:
                    logging.warn("  Truncating message - could break links!")
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
        
        feeds = self._config.get_feeds()
        for feed, feed_url, account in feeds:
            if not account in self._config["accounts"]:
                logging.error("Account %s not configured, unable to post." %
                    account)
                sys.exit(2)
            self._get_account_posts(account)
            logging.debug("Finding eligible posts in feed %s" % feed)
            unposted_items = self._spigotdb.get_unposted_items(feed)
            while self._spigotfeed.feed_ok_to_post(feed):
                try:
                    item = unposted_items.pop(0)
                except:
                    # Escape the loop if there are no new posts waiting
                    break
                link = item[1]
                title = item[2]
                item_hash = item[3]
                message = self._format_message(feed, link, title)
                # Make sure that it has not been posted recently
                if not self._check_duplicate(account, message, item_hash):
                    logging.info("  Posting item %s from %s feed to account %s"
                        % (item_hash,feed,account))
                    # TODO Actually post it here
                    self._spigotdb.mark_posted(item_hash)
  
       
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, \
                            format='%(asctime)s %(levelname)s: %(message)s')
    logging.debug("spigot startup")
    spigot_config = SpigotConfig()
    spigot_config.load()
    spigot_db = SpigotDB()
    spigot_feed = SpigotFeeds(spigot_db, spigot_config)
    # Make this behavior configurable
    spigot_feed.poll_feeds()
    spigot_post = SpigotPost(spigot_db, spigot_config, spigot_feed)
      
# TODO
# - Offering logging configuration?
# - Authentication type
# - statusbot v. identicurse bindings to statusnet
