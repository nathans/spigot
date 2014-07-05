#! /usr/bin/env python

import unittest

import spigot

class SpigotConfigTest(unittest.TestCase):
    test_path = "test.json"

    def setUp(self):
        self.config = spigot.SpigotConfig(self.test_path)

    def tearDown(self):
        self.config.dispose()
        self.config = None
        os.remove(self.test_path)

