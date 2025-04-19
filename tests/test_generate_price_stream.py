import unittest
import pandas as pd
import numpy as np
from botcoin.data.data_fetcher import generate_price_stream
from datetime import datetime, timedelta

class TestGeneratePriceStream(unittest.TestCase):

    def setUp(self):
        # Create dummy OHLC data
        self.HIGH = 105
        self.LOW = 95
        self.CLOSE = 102
        self.OPEN = 100
        self.VOLUME = 1000
        
        self.candle_duration = '1min'
        self.avg_freq_per_minute = 10
        self.seed = 42

        self.ohlc_df = pd.DataFrame({
            'Open': [self.OPEN],
            'High': [self.HIGH],
            'Low': [self.LOW],
            'Close': [self.CLOSE],
            'Volume': [self.VOLUME]
        }, index=pd.to_datetime([datetime(2023, 1, 1, 9, 30)]))

    def test_output_columns_and_index(self):
        stream = generate_price_stream(self.ohlc_df, 
                                       candle_duration=self.candle_duration, 
                                       avg_freq_per_minute=self.avg_freq_per_minute, 
                                       seed=self.seed)
        self.assertIn('price', stream.columns)
        self.assertIsInstance(stream.index, pd.DatetimeIndex)

    def test_contains_open_high_low_close(self):
        stream = generate_price_stream(self.ohlc_df, 
                                       candle_duration=self.candle_duration, 
                                       avg_freq_per_minute=self.avg_freq_per_minute, 
                                       seed=self.seed)
        prices = stream['price'].values
        self.assertIn(self.OPEN, prices)
        self.assertIn(self.HIGH, prices)
        self.assertIn(self.LOW, prices)
        self.assertIn(self.CLOSE, prices)

    def test_time_range_within_candle(self):
        stream = generate_price_stream(self.ohlc_df, 
                                       candle_duration=self.candle_duration, 
                                       avg_freq_per_minute=self.avg_freq_per_minute, 
                                       seed=self.seed)
        start = self.ohlc_df.index[0]
        end = start + timedelta(minutes=1)
        self.assertGreaterEqual(stream.index.min(), start)
        self.assertLessEqual(stream.index.max(), end)

    def test_minimum_number_of_prices(self):
        # Even with low avg freq, should be at least 4 (O, H, L, C)
        stream = generate_price_stream(self.ohlc_df, 
                                       candle_duration=self.candle_duration, 
                                       avg_freq_per_minute=0, 
                                       seed=self.seed)
        self.assertGreaterEqual(len(stream), 4)
