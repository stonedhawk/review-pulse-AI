"""Checks the dashboard binds to localhost only. It has no login, so it must not listen on the network.

    python -m unittest
"""
import os
import tomllib
import unittest

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".streamlit", "config.toml")


class StreamlitConfigTest(unittest.TestCase):
    def test_server_address_is_localhost(self):
        with open(CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)
        self.assertEqual(config["server"]["address"], "localhost")
