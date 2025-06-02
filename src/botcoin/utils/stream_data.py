"""This module contains functions to generate simulated price streams from historical OHLC data."""

from datetime import timedelta

import numpy as np
import pandas as pd


def generate_price_stream(
    ohlc_df,
    candle_duration="1min",
    avg_freq_per_minute=10,
    seed=None,
) -> pd.DataFrame:
    """
    Simulate real-time price updates from historical OHLC data.

    Args:
        ohlc_df (pd.DataFrame): DataFrame with
                ['DatetimeIndex', 'Open', 'High', 'Low', 'Close', 'Volume'].
        candle_duration (str): Duration of each OHLC candle (e.g., '1min', '5min').
        avg_freq_per_minute (int): Average number of price points to simulate per minute.
        seed (int): Random seed for reproducibility.

    Returns:
        pd.DataFrame: DataFrame with ['timestamp', 'price'].
    """
    if seed is not None:
        np.random.seed(seed)

    result = []

    for idx, row in ohlc_df.iterrows():
        start_time = idx.to_pydatetime()
        duration = pd.to_timedelta(candle_duration)

        # Number of points for this candle
        minutes = duration.total_seconds() / 60
        expected_points = avg_freq_per_minute * minutes
        n_points = np.random.poisson(expected_points)
        n_points = max(n_points, 4)  # ensure at least open, high, low, close

        # Generate random timestamps within the candle period
        random_offsets = sorted(np.random.uniform(0, duration.total_seconds(), size=n_points))
        timestamps = [start_time + timedelta(seconds=offset) for offset in random_offsets]

        # Ensure first, high, low, and last prices are in the stream
        prices = [row["Open"], row["High"], row["Low"], row["Close"]]

        # Fill the rest with random prices between low and high
        remaining = n_points - 4
        if remaining > 0:
            random_prices = np.random.uniform(row["Low"], row["High"], size=remaining).tolist()
            prices.extend(random_prices)

        # Shuffle all prices except open, high, low, close for randomness
        np.random.shuffle(prices[1:-1])  # keep open at start and close at end

        # convert datetime to timestamp
        timestamps = [pd.Timestamp(ts).timestamp() for ts in timestamps]

        # Pair timestamps with sorted (by time) prices
        stream = list(zip(timestamps, prices))
        stream.sort(key=lambda x: x[0])  # sort by timestamp again

        result.extend(stream)

    return pd.DataFrame(result, columns=["timestamp", "price"]).set_index("timestamp")
