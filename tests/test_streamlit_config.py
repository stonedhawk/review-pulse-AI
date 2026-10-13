"""Checks the dashboard stays local: it binds to localhost and sends no usage stats to Streamlit.

    python -m unittest
"""
import os
import tomllib
import unittest

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".streamlit", "config.toml")


class StreamlitConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CONFIG_PATH, "rb") as f:
            cls.config = tomllib.load(f)

    def test_server_address_is_localhost(self):
        # The dashboard has no login, so it must not listen on the network.
        self.assertEqual(self.config["server"]["address"], "localhost")

    def test_usage_stats_are_off(self):
        # Streamlit defaults this to true, which would send usage data off the machine.
        self.assertIs(self.config["browser"]["gatherUsageStats"], False)
