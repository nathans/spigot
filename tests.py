#! /usr/bin/env python

import unittest

import os

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


if __name__ == '__main__':
    unittest.main()

# TODO
# Config
# - Upgrade of spigot config
# - 
