"""This module contains the StockProfiler class, which is used to profile stocks."""

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
            "1min_returns": self.compute_1min_returns(df_1min)["returns"],
        }

    def compute_1min_returns(self, df_1min):
        """
        Compute 1-minute returns for the given DataFrame.

        Args:
            df_1min (DataFrame): The DataFrame containing 1-minute OHLCV data.

        Returns:
            DataFrame: A DataFrame with the computed 1-minute returns.
        """
        df_1min["returns"] = df_1min["Close"].pct_change()
        df_1min = df_1min.dropna(subset=["returns"])
        return df_1min
