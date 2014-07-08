#! /usr/bin/env python

import unittest

import datetime
import os
import sqlite3

import spigot


class TestOldConfig(unittest.TestCase):
    test_config_path = "utils/tests/test.json"

    def setUp(self):
        self.config = spigot.SpigotConfig(self.test_config_path)
        self.config.load()

    def tearDown(self):
        self.config = None

    def test_config_check(self):
        old_config = self.config.check_old_config()
        self.assertTrue(old_config)


class TestNewConfig(unittest.TestCase):
    test_config_path = "test.json"

    def setUp(self):
        self.config = spigot.SpigotConfig(self.test_config_path)

    def test_no_config(self):
        self.assertFalse(os.path.exists(self.test_config_path))
        self.assertTrue(self.config.no_config)

    def test_add_user(self):
        pass

    def test_add_feed(self):
        pass

    def test_save(self):
        self.assertTrue(self.config.save())
        self.assertTrue(os.path.exists(self.test_config_path))

    def tearDown(self):
        self.config = None
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)


class SpigotDBTest(unittest.TestCase):
    test_db_path = "test.db"
    test_data = "utils/tests/test-existing.sql"
    db_schema = [("feed", "text"), ("link", "text"), ("message", "text"),
                 ("date", "timestamp"), ("posted", "timestamp")]
    det_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    old_url = "http://example.com/post/17"
    new_url = "http://example.com/post/18"
    new_feed = "http://example.com/feed.xml"
    new_message = "Post #18 - http://example.com/post/18"
    new_date = datetime.datetime(2014, 7, 1, 12, 15, 0)

    def setUp(self):
        if self.test_data:
            sql_file = open(self.test_data, "r")
            sql_cmds = sql_file.readlines()
            sql_file.close()
            dbtest = sqlite3.connect(self.test_db_path,
                                     detect_types=self.det_types)
            curs = dbtest.cursor()
            for cmd in sql_cmds:
                curs.execute(cmd)
            curs.close()
            dbtest.commit()
            dbtest.close()
            dbtest = None
        self.db = spigot.SpigotDB(path=self.test_db_path)

    def tearDown(self):
        self.db.close()
        self.db = None
        os.remove(self.test_db_path)


class TestOldDB(SpigotDBTest):
    test_data = "utils/tests/test-old.sql"

#    def test_db_check(self):
#        old_db = self.db.check_old_db()
#        self.assertTrue(old_db)

    def tearDown(self):
        self.db.close()
        self.db = None

class TestExistingDB(SpigotDBTest):

    def test_check_link_false(self):
        "Run check_link with a known new link"

        self.assertFalse(self.db.check_link(self.new_url))

    def test_check_link_true(self):
        "Run check_link with a known new link"

        self.assertTrue(self.db.check_link(self.old_url))

    def test_add_item(self):
        "Run add_item and verify that the added item is in the DB"

        self.db.add_item(feed_url=self.new_feed, link=self.new_url,
                         message=self.new_message, date=self.new_date)
        self.assertTrue(self.db.check_link(self.new_url))

    def test_get_unposted_items(self):
        "Run get_unposted_items and verify that result matches test data"

        unposted = self.db.get_unposted_items(self.new_feed)
        self.assertEquals(len(unposted), 6)

        # Testing mark_posted() and get_latest_post()

    def test_db_check(self):
        "Test that a post-2.2 DB schema is not flagged as pre-2.2"

        old_db = self.db.check_old_db()
        self.assertFalse(old_db)


class TestNewDB(SpigotDBTest):
    test_data = None

    def test_new(self):
        "Testing the initialization of a new DB"

        self.assertTrue(os.path.exists(self.test_db_path))
        det_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        dbtest = sqlite3.connect(self.test_db_path, detect_types=det_types)
        curs = dbtest.cursor()
        curs.execute("PRAGMA table_info(items);")
        cols = curs.fetchall()
        curs.close()
        for col in cols:
            self.assertIn((col[1], col[2]), self.db_schema)


if __name__ == '__main__':
    unittest.main()

# TODO
# Config
# - Upgrade of spigot config
# -
