"""This module contains the StockProfiler class, which is used to profile stocks."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from scipy import signal
from scipy.fft import fft, fftfreq
import yfinance as yf

from botcoin.data.historical import YfDataManager


class StockProfiler:
    """A class to profile stocks."""

    def __init__(self):
        self.dm = YfDataManager()

    def profile(self, symbol: str, years: int = 5) -> dict:
        """
        Profile the given stock.

        Args:
            symbol (str): The stock symbol to profile.
            years (int): The number of years of data to retrieve for profiling.
        Returns:
            dict: A dictionary containing the stock profile.
        """
        df_1min = self.dm.get_30d_1min_data(symbol)
        start_date, end_date = self._get_date_range(timedelta(days=365 * years))
        df_1d = self.dm.get_ohlcv_1d(symbol, start_date, end_date)
        quote = self.dm.dp.get_quote(symbol)
        annual_returns = self.compute_annual_returns(df_1d)
        returns_1d = self.compute_oc_returns(df_1d)
        log_returns_1d = np.log(returns_1d + 1)

        # Compute the risk-free rate for the same date range
        risk_free_rate = self.compute_risk_free_rate(start_date, end_date)
        returns_tz = getattr(annual_returns.index, "tz", None)
        risk_free_tz = getattr(risk_free_rate.index, "tz", None)
        if returns_tz is not None:
            if risk_free_tz is not None:
                risk_free_rate = risk_free_rate.tz_convert(returns_tz)
            else:
                risk_free_rate = risk_free_rate.tz_localize(returns_tz)

        sharpe_ratio = self.compute_sharpe_ratio(annual_returns, risk_free_rate)
        sortino_ratio = self.compute_sortino_ratio(annual_returns, risk_free_rate)

        # Compute beta relative to SPY
        beta = self.compute_beta(symbol)

        return {
            "symbol": symbol,
            "ipo_date": self.dm.dp.get_ipo_date(symbol),
            "quote": quote,
            "ohlcv_1min": df_1min,
            "df_1d": df_1d,
            "1d_returns": returns_1d,
            "log_returns_1d": log_returns_1d,
            "1min_returns": self.compute_oc_returns(df_1min),
            "annual_returns": annual_returns,
            "exp_annual_return": annual_returns.mean(),
            "var_annual_return": annual_returns.var(),
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "beta": beta,
        }

    def get_quote(self, symbol: str) -> float:
        """
        Get the stock quote for the given stock symbol.

        Args:
            symbol (str): The stock symbol to get the quote for.

        Returns:
            float: The current stock quote.
        """
        quote = self.dm.dp.get_quote(symbol)
        if quote is None:
            raise ValueError(f"No quote found for symbol: {symbol}")
        return quote

    def get_annual_returns(self, symbol: str) -> pd.Series:
        """
        Get the annual returns for the given stock symbol.

        Args:
            symbol (str): The stock symbol to get annual returns for.

        Returns:
            pd.Series: A Series containing the annual returns.
        """
        df_1d = self.dm.get_ohlcv_1d(
            symbol,
            *self._get_date_range(
                timedelta(days=365 * 6)
            ),  # 6 years of data to compute 5 years of annual returns
        )
        return self.compute_annual_returns(df_1d)

    def get_ohlcv_1d(self, symbol: str, years: int) -> pd.DataFrame:
        """
        Get the OHLCV data for the given stock symbol.

        Args:
            symbol (str): The stock symbol to get OHLCV data for.
            years (int): The number of years of data to retrieve.

        Returns:
            pd.DataFrame: A DataFrame containing the OHLCV data.
        """
        return self.dm.get_ohlcv_1d(
            symbol, *self._get_date_range(timedelta(days=365 * years))
        )

    @staticmethod
    def print_profile(profile: dict) -> None:
        """
        Print the stock profile in a readable format.

        Args:
            profile (dict): The stock profile to print.
        """
        print(f"Symbol: {profile['symbol']}")
        print(f"IPO Date: {profile['ipo_date']}")
        print(f"Quote: {profile['quote']}")
        print(f"Expected Annual Return: {profile['exp_annual_return']:.2%}")
        print(f"Sharpe Ratio: {profile['sharpe_ratio']:.2f}")
        print(f"Sortino Ratio: {profile['sortino_ratio']:.2f}")
        print(f"Beta: {profile['beta']:.2f}")

    def compute_1d_return_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Compute the correlation of 1-day returns between two stocks.
        Args:
            symbol1 (str): The first stock symbol.
            symbol2 (str): The second stock symbol.
        Returns:
            float: The correlation coefficient of the 1-day returns.
        """
        returns1 = self.compute_oc_returns(
            self.dm.get_ohlcv_1d(
                symbol1, *self._get_date_range(timedelta(days=365 * 5))
            )
        )
        returns2 = self.compute_oc_returns(
            self.dm.get_ohlcv_1d(
                symbol2, *self._get_date_range(timedelta(days=365 * 5))
            )
        )

        # Align on common dates
        aligned_returns = pd.concat([returns1, returns2], axis=1, join="inner").dropna()
        aligned_returns.columns = [symbol1, symbol2]

        return aligned_returns[symbol1].corr(aligned_returns[symbol2])

    def compute_1d_return_correlation_matrix(self, symbols: list[str]) -> pd.DataFrame:
        """
        Compute the correlation matrix of 1-day returns for a list of stocks.

        Args:
            symbols (list[str]): A list of stock symbols.

        Returns:
            DataFrame: A DataFrame containing the correlation matrix.
        """
        # Initialize an empty DataFrame
        correlation_matrix = pd.DataFrame(index=symbols, columns=symbols)

        # Fill the correlation matrix
        for i in symbols:
            for j in symbols:
                if i == j:
                    correlation_matrix.loc[i, j] = 1.0  # Perfect correlation with self
                elif pd.isna(correlation_matrix.loc[i, j]):
                    corr = self.compute_1d_return_correlation(i, j)
                    correlation_matrix.loc[i, j] = corr
                    correlation_matrix.loc[j, i] = corr  # Symmetric matrix

        return correlation_matrix

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

    def compute_close_returns(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute close-close returns for the given DataFrame.

        Args:
            df (DataFrame): The DataFrame containing OHLCV data.

        Returns:
            Series: A Series with the computed close-close returns.
        """
        df["close_returns"] = df["Close"].pct_change()
        return df["close_returns"].dropna()

    def compute_max_drawdown(self, df: pd.DataFrame) -> float:
        """
        Compute the maximum drawdown for the given DataFrame.

        Args:
            df (DataFrame): The DataFrame containing OHLCV data.

        Returns:
            float: The maximum drawdown as a percentage.
        """
        df["peak"] = df["Close"].cummax()
        df["drawdown"] = (df["Close"] - df["peak"]) / df["peak"]
        max_drawdown = df["drawdown"].min()
        return max_drawdown

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

    def compute_risk_free_rate(self, start_date: date, end_date: date) -> pd.Series:
        """
        Compute the risk-free rate based on the U.S. Treasury yield.

        Args:
            start_date (date): The start date for the risk-free rate calculation.
            end_date (date): The end date for the risk-free rate calculation.

        Returns:
            pd.Series: A Series containing the risk-free rate.
        """

        irx = yf.download("^IRX", start=start_date, end=end_date)

        if irx is None or irx.empty:
            raise ValueError("No data found for the risk-free rate.")
        else:
            irx["annual_yield"] = irx["Close"] / 100
            irx["daily_rf_return"] = (1 + irx["annual_yield"]) ** (1 / 252) - 1

        return irx["daily_rf_return"]

    def compute_sharpe_ratio(
        self, returns: pd.Series, risk_free_rate: pd.Series
    ) -> float:
        """
        Compute the Sharpe ratio for the given returns and risk-free rate.

        Args:
            returns (pd.Series): The returns of the asset.
            risk_free_rate (pd.Series): The risk-free rate.

        Returns:
            float: The Sharpe ratio.
        """
        excess_returns = returns - risk_free_rate
        return excess_returns.mean() / excess_returns.std()

    def compute_semivariance(self, returns: pd.Series) -> float:
        """
        Compute the semivariance for the given returns and risk-free rate.

        Args:
            returns (pd.Series): The returns of the asset.

        Returns:
            float: The semivariance.
        """
        mean = returns.mean()
        negative_returns = returns[returns < mean]
        semivariance = (mean - negative_returns) ** 2
        return semivariance.mean()

    def compute_sortino_ratio(
        self, returns: pd.Series, risk_free_rate: pd.Series
    ) -> float:
        """
        Compute the Sortino ratio for the given returns and risk-free rate.

        Args:
            returns (pd.Series): The returns of the asset.
            risk_free_rate (pd.Series): The risk-free rate.

        Returns:
            float: The Sortino ratio.
        """
        excess_returns = returns - risk_free_rate
        downside_deviation = self.compute_semivariance(excess_returns)
        return excess_returns.mean() / downside_deviation**0.5

    def compute_beta(self, symbol: str, benchmark: str = "SPY") -> float:
        """
        Compute the beta of the given stock relative to a benchmark.

        Notes:
            Beta > 1: More volatile than the market

            Beta < 1: Less volatile than the market

            Beta < 0: Moves inversely to the market

        Args:
            symbol (str): The stock symbol to compute beta for.
            benchmark (str): The benchmark symbol to compare against (default is "SPY").

        Returns:
            float: The beta of the stock.
        """

        returns = self.compute_oc_returns(
            self.dm.get_ohlcv_1d(symbol, *self._get_date_range(timedelta(days=365 * 5)))
        )
        spy_returns = self.compute_oc_returns(
            self.dm.get_ohlcv_1d(
                benchmark, *self._get_date_range(timedelta(days=365 * 5))
            )
        )

        # Align on common dates
        aligned_returns = pd.concat(
            [returns, spy_returns], axis=1, join="inner"
        ).dropna()

        symbol = symbol + "_returns"  # to avoid column name conflict
        aligned_returns.columns = [symbol, benchmark]

        covariance = aligned_returns[symbol].cov(aligned_returns[benchmark])
        variance = float(aligned_returns[benchmark].var())

        return covariance / variance

    def fourier_analysis(self, price_series: pd.Series) -> dict:
        """
        Perform Fourier analysis on the given price series.

        Args:
            price_series (pd.Series): The price series to analyze.

        Returns:
            dict: A dictionary containing the periods, magnitudes, and frequencies.
        """
        # Remove trend (detrend)
        detrended = signal.detrend(price_series)  # type: ignore

        # Apply window function to reduce spectral leakage
        windowed = detrended * np.hanning(len(detrended))

        # Compute FFT
        fft_values = fft(windowed)
        freqs = fftfreq(len(windowed), d=1)  # Daily frequency

        # Get positive frequencies only
        positive_freq_idx = freqs > 0
        freqs_positive = freqs[positive_freq_idx]
        fft_magnitude = np.abs(fft_values[positive_freq_idx])  # type: ignore

        # Convert frequency to periods (in days)
        periods = 1 / freqs_positive  # type: ignore

        results = {
            "periods": periods,
            "magnitudes": fft_magnitude,
            "frequencies": freqs_positive,
        }

        return results

    def monthly_seasonality(
        self, df_1d: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Analyze monthly seasonality in the given price series.

        Args:
            df_1d (pd.DataFrame): The DataFrame containing daily price data.

        Returns:
            pd.DataFrame: A DataFrame containing the average monthly returns.
        """
        returns = self.compute_close_returns(df_1d)

        # Add month column
        data = returns.to_frame(name="returns")
        data["month"] = data.index.month
        data["year"] = data.index.year

        # Group by month and year, cumulatively sum returns
        monthly_returns = (
            data.groupby(["year", "month"])["returns"]
            .apply(lambda x: (1 + x).prod() - 1)  # Cumulative product of returns
            .reset_index()
        )

        monthly_stats = monthly_returns.groupby("month")["returns"].agg(
            ["mean", "std", "count"]
        )

        monthly_stats["sharpe"] = monthly_stats["mean"] / monthly_stats["std"]

        monthly_stats["mean"] = monthly_stats["mean"].dropna()
        monthly_stats["std"] = monthly_stats["std"].dropna()
        monthly_stats["count"] = monthly_stats["count"].dropna()

        return monthly_stats, monthly_returns

    def weekly_seasonality(
        self, df_1d: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Analyze weekly seasonality in the given price series.

        Args:
            df_1d (pd.DataFrame): The DataFrame containing daily price data.

        Returns:
            pd.DataFrame: A DataFrame containing the average weekly returns.
        """
        returns = self.compute_close_returns(df_1d)

        # Add weekday column
        weekly_data = returns.to_frame(name="returns")
        weekly_data["weekday"] = weekly_data.index.day_name()

        # Calculate daily statistics
        weekday_stats = weekly_data.groupby("weekday")["returns"].agg(
            ["mean", "std", "count"]
        )
        weekday_stats["sharpe"] = weekday_stats["mean"] / weekday_stats["std"]

        # Reorder by weekday
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        weekday_stats = weekday_stats.reindex(weekday_order)

        return weekday_stats, weekly_data
