#! /usr/bin/env python

# Tool to upgrade databases of spigot 2.1 and below to spigot 2.2 and higher

import argparse
import logging
try:
    import json
except ImportError:
    import simplejson as json
import sqlite3
import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database",default="spigot.db")
    parser.add_argument("--config",default="spigot.json")
    args = parser.parse_args()

    logging.basicConfig(level="INFO", 
                        format='%(asctime)s %(levelname)s: %(message)s')
    # Set up configuration object
    try:
        config = json.loads(open(args.config, "r").read())
    except IOError:
        logging.warning("Could not load configuration file")

    # Set up database object
    try:
        db = sqlite3.connect(args.database,
                    detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    except:
        logging.exception("Could not connect to database %s" % args.database)
        sys.exit(2)

    # Alter table to add message column
    curs = db.cursor()
    curs.execute("ALTER TABLE items ADD COLUMN message text")
    curs.close()
    db.commit()
    logging.info("Added message column to DB")

    posts_curs = db.cursor()
    posts_curs.execute("SELECT feed, link, title FROM items")
    all_items = posts_curs.fetchall()
    posts_curs.close()
    for item in all_items:
        feed = item[0]
        link = item[1]
        title = item[2]
        logging.info("Item: %s" % link)
        format = config["feeds"][feed]["format"]

        transforms = [ ("$t", title), ("$l", link) ]
        for string, val in transforms:
            format = format.replace(string, val)

        logging.info("  Message: %s" % format)
        a_curs = db.cursor()
        a_curs.execute("UPDATE items SET message=? WHERE link=?", (format,link))
        a_curs.close()
        
    logging.info("Commiting database")
    db.commit()

    # Transform config file
    changes = [ ("$t","%title%"), ("$l", "%link%") ]
    conf_file = open(args.config,"r")
    conf = conf_file.read()
    conf_file.close()
    for old, new in changes:
        conf = conf.replace(old,new)
    logging.info("Writing modified config file")
    new_file = open(args.config,"w")
    new_file.write(conf)
    new_file.close()
