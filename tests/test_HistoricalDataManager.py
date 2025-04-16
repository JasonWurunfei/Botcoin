import unittest

import sys
import os
import pandas as pd
from datetime import datetime
import pytz

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from botcoin.data.data_fetcher import HistoricalDataManager

class Test_HistoricalDataManager(unittest.TestCase):
    
    def setUp(self):
        self.ticker = "AAPL"
        self.data_path = os.path.join("tests/test_data", f"{self.ticker}_1min_data.parquet")
        self.hdm = HistoricalDataManager(ticker=self.ticker, data_folder="tests/test_data")
        self.df = pd.read_parquet(self.data_path)
        self.earliest_date = self.df.index.min()  # 2025-03-18 09:30:00-04:00
        self.latest_date = self.df.index.max()    # 2025-04-15 15:59:00-04:00
        

    def tearDown(self):
        pass
    
    def test_get_data_start_after_end(self):
        start   = datetime(year=2025, month=4, day=16, hour=0, minute=0, second=0)
        end     = datetime(year=2025, month=4, day=15, hour=0, minute=0, second=0)
        
        start   = self.hdm.tz.localize(start)
        end     = self.hdm.tz.localize(end)
        
        with self.assertRaises(ValueError):
            # Attempt to fetch data with start date after end date
            self.hdm.get_data(start=start, end=end)
            
    def test_if_in_local_data(self):
        start   = datetime(year=2025, month=3, day=18, hour=9,  minute=30, second=0)
        end     = datetime(year=2025, month=4, day=15, hour=15, minute=59, second=0)
        
        start   = self.hdm.tz.localize(start)
        end     = self.hdm.tz.localize(end)
        
        self.assertTrue(self.hdm._check_data_in_local(start=start, end=end), "Data is not in local data")   


if __name__ == "__main__":
    unittest.main()