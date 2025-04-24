"""Unit tests for the generate_price_stream function."""

import unittest
from datetime import datetime, timedelta

import pandas as pd

from botcoin.data.data_fetcher import generate_price_stream


class TestGeneratePriceStream(unittest.TestCase):
    """Unit tests for the generate_price_stream function."""

    def setUp(self):
        # Create dummy OHLC data
        self.high = 105
        self.low = 95
        self.close = 102
        self.open = 100
        self.volume = 1000

        self.candle_duration = "1min"
        self.avg_freq_per_minute = 10
        self.seed = 42

        self.ohlc_df = pd.DataFrame(
            {
                "Open": [self.open],
                "High": [self.high],
                "Low": [self.low],
                "Close": [self.close],
                "Volume": [self.volume],
            },
            index=pd.to_datetime([datetime(2023, 1, 1, 9, 30)]),
        )

    def test_output_columns_and_index(self):
        """Test if the output DataFrame has the correct columns and index."""
        stream = generate_price_stream(
            self.ohlc_df,
            candle_duration=self.candle_duration,
            avg_freq_per_minute=self.avg_freq_per_minute,
            seed=self.seed,
        )
        self.assertIn("price", stream.columns)
        self.assertIsInstance(stream.index, pd.DatetimeIndex)

    def test_contains_open_high_low_close(self):
        """Test if the generated price stream contains the OHLC values."""
        stream = generate_price_stream(
            self.ohlc_df,
            candle_duration=self.candle_duration,
            avg_freq_per_minute=self.avg_freq_per_minute,
            seed=self.seed,
        )
        prices = stream["price"].values
        self.assertIn(self.open, prices)
        self.assertIn(self.high, prices)
        self.assertIn(self.low, prices)
        self.assertIn(self.close, prices)

    def test_time_range_within_candle(self):
        """Test if the generated price stream is within the candle duration."""
        stream = generate_price_stream(
            self.ohlc_df,
            candle_duration=self.candle_duration,
            avg_freq_per_minute=self.avg_freq_per_minute,
            seed=self.seed,
        )
        start = self.ohlc_df.index[0]
        end = start + timedelta(minutes=1)
        self.assertGreaterEqual(stream.index.min(), start)
        self.assertLessEqual(stream.index.max(), end)

    def test_minimum_number_of_prices(self):
        """Test if the generated price stream has a minimum number of prices."""
        # Even with low avg freq, should be at least 4 (O, H, L, C)
        stream = generate_price_stream(
            self.ohlc_df,
            candle_duration=self.candle_duration,
            avg_freq_per_minute=0,
            seed=self.seed,
        )
        self.assertGreaterEqual(len(stream), 4)
