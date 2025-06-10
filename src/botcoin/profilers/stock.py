"""This module contains the StockProfiler class, which is used to profile stocks."""

from datetime import date, timedelta

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
        start_date, end_date = self._get_date_range(timedelta(days=365 * 5))
        df_1d = self.dm.get_ohlcv_1d(symbol, start_date, end_date)
        quote = self.dm.dp.get_quote(symbol)
        annual_returns = self.compute_annual_returns(df_1d)
        return {
            "symbol": symbol,
            "ipo_date": self.dm.dp.get_ipo_date(symbol),
            "quote": quote,
            "ohlcv_1min": df_1min,
            "1min_returns": self.compute_oc_returns(df_1min),
            "1d_returns": self.compute_oc_returns(df_1d),
            "annual_return": annual_returns.mean(),
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

    def _get_date_range(self, time_delta: timedelta) -> tuple[date, date]:
        """
        Get the date range of x days ago from today.

        Args:
            days (int): The number of days ago.

        Returns:
            str: The date in 'YYYY-MM-DD' format.
        """
        end_date = date.today()
        start_date = end_date - time_delta
        return (start_date, end_date)

    def compute_annual_returns(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute annual returns for the given DataFrame. This
        method calculates the annualized returns based on the daily returns.
        It assumes that the DataFrame contains daily OHLCV data with a 'Close' column.

        Assuming there is 252 trading days in a year, the annual returns can be
        calculated as follows:

        Annual Return = (p_x - p_x-252) / p_x-252
        where:
            - p_x is the closing price on day x
            - p_x-252 is the closing price 252 days prior to day x

        Args:
            df (DataFrame): The DataFrame containing OHLCV data.
        Returns:
            Series: A Series with the computed annual returns.
        """
        shift_days = 252
        shifted_close = df["Close"].shift(shift_days)

        df["annual_returns"] = (df["Close"] - shifted_close) / shifted_close

        # Remove NaN values that result from the shift operation
        df = df.dropna(subset=["annual_returns"])

        return df["annual_returns"]
