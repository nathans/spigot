#! /usr/bin/env python

import datetime
import os
import sqlite3
import unittest

import spigot


class SpigotConfigTest(unittest.TestCase):
    test_config_path = "utils/tests/test.json"

    def setUp(self):
        self.config = spigot.SpigotConfig(self.test_config_path)
        self.config.load()

    def tearDown(self):
        self.config = None


class TestOldConfig(SpigotConfigTest):
    test_config_path = "utils/tests/test-old.json"

    def test_config_check(self):
        old_config = self.config.check_old_config()
        self.assertTrue(old_config)


class TestExistingConfig(SpigotConfigTest):

    def test_check_existing_config(self):
        old_config = self.config.check_old_config()
        self.assertFalse(old_config)
        self.assertFalse(self.config.no_config)


class TestNewConfig(SpigotConfigTest):
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
                 ("title", "text"), ("date", "timestamp"),
                 ("posted", "timestamp")]
    det_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    old_url = "http://example.com/post/17"
    new_url = "http://example.com/post/18"
    new_feed = "http://example.com/feed.xml"
    new_message = "Post #18 - http://example.com/post/18"
    new_date = datetime.datetime(2014, 7, 1, 12, 15, 0)
    new_title = "Post #18"

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

    def test_db_check(self):
        old_db = self.db.check_old_db()
        self.assertTrue(old_db)


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
                         message=self.new_message, title=self.new_title,
                         date=self.new_date)
        self.assertTrue(self.db.check_link(self.new_url))

    def test_get_unposted_items(self):
        "Run get_unposted_items and verify that result matches test data"

        unposted = self.db.get_unposted_items(self.new_feed)
        self.assertEquals(len(unposted), 6)

    def test_get_latest_post(self):
        "Run get_latest_post and verify that result matches test data"

        newest_post = datetime.datetime(2014, 6, 17, 3, 42, 52, 614399)
        latest = self.db.get_latest_post(feed=self.new_feed)
        self.assertEqual(latest, newest_post)

    def test_mark_posted(self):
        "Run mark_posted and verify the update via get_latest_post"

        now = datetime.datetime.now()
        self.db.mark_posted(item_link=self.old_url, date=now)
        latest = self.db.get_latest_post(feed=self.new_feed)
        self.assertEqual(latest, now)

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
# Remake database existing test
# Config
# - Upgrade of spigot config
