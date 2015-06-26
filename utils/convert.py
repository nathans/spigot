#! /usr/bin/env python
# Tool to upgrade db and config from spigot 2.2 to 2.3+

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
    parser.add_argument("--database", default="spigot.db")
    parser.add_argument("--config", default="spigot.json")
    args = parser.parse_args()

    logging.basicConfig(level="INFO",
                        format='%(asctime)s %(levelname)s: %(message)s')
    # Set up configuration object
    try:
        config = json.loads(open(args.config, "r").read())
    except IOError:
        logging.warning("Could not load configuration file")

    # Set up database object
    det_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    try:
        db = sqlite3.connect(args.database, detect_types=det_types)
    except:
        logging.exception("Could not connect to database %s" % args.database)
        sys.exit(2)

    # Ensure db schema is correct
    curs = db.cursor()
    curs.execute("PRAGMA table_info(items);")
    cols = curs.fetchall()
    required = "message", "title"
    for element in required:
        if element not in [col[1] for col in cols]:
            curs.execute("ALTER TABLE items ADD COLUMN %s text" % element)
            logging.info("Added %s column to DB" % element)
    curs.close()
    logging.info("Committing database")
    db.commit()

    # Clean up config file
    # Add an empty title element to each feed
    for feed in config["feeds"].keys():
        if "title" not in config["feeds"][feed].keys():
            config["feeds"][feed]["title"] = ""
            logging.info("Added blank title element to each feed")
    # Remove the accounts element
    if "accounts" in config.keys():
        logging.info("Removing accounts element")
        del config["accounts"]
        logging.info("You'll prompted to reauthorize accounts at next run")
    logging.info("Writing modified config file")
    open(args.config, "w").write(json.dumps(config, indent=4))

    logging.info("Upgrade of db/config complete.")
