#! /usr/bin/env python

import unittest

import datetime
import os
import sqlite3

import spigot


class TestExistingConfig(unittest.TestCase):
    test_config_path = "utils/tests/spigot.json"

    def setUp(self):
        self.config = spigot.SpigotConfig(self.test_config_path)

    def tearDown(self):
        self.config = None


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


class SpigotFeedsTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass


class SpigotDBTest(unittest.TestCase):
    test_db_path = "test.db"
    db_schema = [("feed", "text"), ("link", "text"), ("message", "text"),
                 ("date", "timestamp"), ("posted", "timestamp")]

    def setUp(self):
        self.db = spigot.SpigotDB(path=self.test_db_path)

    def tearDown(self):
        self.db.close()
        self.db = None
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_new(self):
        # Just some dummy variables
        new_url = "http://example.com/feed.xml"
        new_link = "http://example.com/example.html"
        new_message = "New post: http://example.com/example.html"
        new_date = datetime.datetime(2012, 9, 1, 12, 15, 0)

        # Testing initialization of new DB
        self.assertTrue(os.path.exists(self.test_db_path))
        det_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        dbtest = sqlite3.connect(self.test_db_path, detect_types=det_types)
        curs = dbtest.cursor()
        curs.execute("PRAGMA table_info(items);")
        cols = curs.fetchall()
        curs.close()
        for col in cols:
            self.assertIn((col[1], col[2]), self.db_schema)

        # Testing check_link() ; expecting False as the DB should be empty
        self.assertFalse(self.db.check_link(new_link))

        # Testing add_item()
        add = self.db.add_item(feed_url=new_url, link=new_link,
                               message=new_message, date=new_date)
        self.assertTrue(add)

        # Testing check_link() ; now expecting true
        self.assertTrue(self.db.check_link(new_link))

        # Testing get_unposted_items()
        test_unposted = self.db.get_unposted_items(feed=new_url)
        self.assertGreater(len(test_unposted), 0)
        item = test_unposted[0]
        self.assertEqual(item[0], new_url)
        self.assertEqual(item[1], new_link)
        self.assertEqual(item[2], new_message)

        # Testing mark_posted() and get_latest_post()
        test_date = datetime.datetime.now()
        self.db.mark_posted(item_link=new_link, date=test_date)
        latest = self.db.get_latest_post(feed=new_url)
        self.assertEqual(latest, test_date)


if __name__ == '__main__':
    unittest.main()

# TODO
# Config
# - Upgrade of spigot config
# -
