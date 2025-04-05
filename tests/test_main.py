import unittest

import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from botcoin.app import main

class TestMain(unittest.TestCase):
    def test_placeholder(self):
        self.assertTrue(main())

if __name__ == "__main__":
    unittest.main()