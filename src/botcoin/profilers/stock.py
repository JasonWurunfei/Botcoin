"""This module contains the StockProfiler class, which is used to profile stocks."""

import pandas as pd

from botcoin.data.historical import YfDataManager


class StockProfiler:
    """A class to profile stocks."""

    def __init__(self):
        self.dm = YfDataManager()

    def profile(self, symbol: str) -> dict:
        """
        Profile the given stock.

        Args:
            symbol (str): The stock symbol to profile.
        Returns:
            dict: A dictionary containing the stock profile.
        """
        df_1min = self.dm.get_30d_1min_data(symbol)
        return {
            "symbol": symbol,
            "1min_returns": self.compute_oc_returns(df_1min),
        }

    def compute_oc_returns(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute open-close returns for the given DataFrame.

        Args:
            df (DataFrame): The DataFrame containing OHLCV data.

        Returns:
            Series: A Series with the computed open-close returns.
        """
        df["oc_returns"] = (df["Close"] - df["Open"]) / df["Open"]
        return df["oc_returns"]
