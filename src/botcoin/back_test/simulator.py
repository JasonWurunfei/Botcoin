"""
Docstring for botcoin.back_test.simulator
"""

from typing import cast

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf
import pandas as pd
from pandas import MultiIndex
from botcoin.data.dataclasses.portfolio import Portfolio


class Simulator:
    """
    A simple back test simulator for botcoin.
    """

    def __init__(
        self,
        portfolio: Portfolio,
        required_symbols: list[str],
        benchmark_symbol: str,
        start_date: str,
        end_date: str,
        strategy: callable = None,  # type: ignore
    ) -> None:
        self.portfolio = portfolio
        self.required_symbols = required_symbols
        self.benchmark_symbol = benchmark_symbol
        self.start_date = start_date
        self.end_date = end_date
        self.data = pd.DataFrame()
        self.strategy = strategy
        self.portfolio_values = pd.DataFrame()

    def load_data(self) -> None:
        """
        Loads historical data for the required symbols.
        """
        if not self.required_symbols:
            raise ValueError("No required symbols provided for data loading.")
        if not self.start_date or not self.end_date:
            raise ValueError("Start date and end date must be provided.")
        if self.start_date >= self.end_date:
            raise ValueError("Start date must be earlier than end date.")
        if not self.benchmark_symbol:
            raise ValueError("Benchmark symbol must be provided.")
        if self.benchmark_symbol not in self.required_symbols:
            self.required_symbols.append(self.benchmark_symbol)

        data = yf.download(
            tickers=self.required_symbols,
            start=self.start_date,
            end=self.end_date,
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
        )
        data = cast(pd.DataFrame, data)

        # --- keep only rows where ALL symbols have Close data ---
        close_df = data.xs("Close", axis=1, level=1)
        valid_idx = close_df.dropna(how="any").index

        # check if all required symbols are in the data and
        for symbol in self.required_symbols:
            columns = cast(MultiIndex, data.columns)
            if symbol not in columns.levels[0]:
                raise ValueError(f"Data for required symbol {symbol} is missing.")

        self.data = data.loc[valid_idx]

    def run(self):
        """
        Computes the portfolio values over time.
        """
        if self.data is None or self.data.empty:
            raise ValueError(
                "No data loaded. Please load data before computing portfolio values."
            )

        close_df = self.data.xs("Close", axis=1, level=1)

        values = []
        for date, row in close_df.iterrows():
            if self.strategy:
                self.strategy(self.portfolio, date, self.data)
            for symbol, stock in self.portfolio.stocks.items():
                if symbol in row and not pd.isna(row[symbol]):
                    stock.market_price = row[symbol]
            values.append((date, self.portfolio.total_value))

        self.portfolio_values = pd.DataFrame(
            values, columns=["Date", "Total Value"]
        ).set_index("Date")

    def plot(self):
        """
        Plots the historical data for the required symbols.
        """
        if self.data is None or self.data.empty:
            raise ValueError("No data loaded. Please load data before plotting.")

        plt.figure(figsize=(12, 6))

        # Plot benchmark
        benchmark_close = self.data[self.benchmark_symbol]["Close"]
        benchmark_normalized = (
            benchmark_close.loc[benchmark_close.index[0] :]
            .div(benchmark_close.loc[benchmark_close.index[0]])
            .sub(1)
            .mul(100)
        )
        plt.plot(
            benchmark_normalized.index,
            benchmark_normalized,
            label=self.benchmark_symbol,
            linewidth=2,
            color="gray",
        )

        # Plot portfolio value
        if self.portfolio_values.empty:
            raise ValueError(
                "No portfolio values computed. Please run the simulator before plotting."
            )

        portfolio_normalized = (
            self.portfolio_values.loc[self.portfolio_values.index[0] :]
            .div(self.portfolio_values.loc[self.portfolio_values.index[0]])
            .sub(1)
            .mul(100)
        )
        plt.plot(
            portfolio_normalized.index,
            portfolio_normalized["Total Value"],
            label="Portfolio",
            linewidth=2,
            color="purple",
        )
        plt.title("Cumulative Return (%)")
        plt.xlabel("Date")
        plt.ylabel("Return (%)")
        plt.axhline(0, color="black", linewidth=0.8)
        plt.legend()

        # --- X-axis formatting ---
        ax = plt.gca()
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.show()
