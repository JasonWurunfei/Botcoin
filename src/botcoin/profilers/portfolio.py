"""This module provides functions to profile portfolio statistics, including the efficient frontier and the Capital Market Line (CML)."""

from datetime import date

import pandas as pd
import numpy as np
from scipy.optimize import minimize

from botcoin.profilers.stock import StockProfiler


class PortfolioProfiler:
    """A class to profile portfolio statistics."""

    def __init__(self, symbols: list[str], holdings: list[float], duration: int = 6):
        self.symbols = symbols
        self.holdings = holdings
        self.duration = duration

        self._profiler = StockProfiler()
        self._quotes = [self._profiler.get_quote(symbol) for symbol in symbols]
        self.values = [
            quote * holding for quote, holding in zip(self._quotes, holdings)
        ]
        self.dfs_1d = {}
        self.portfolio_value = sum(self.values)
        self.weights = np.array([value / self.portfolio_value for value in self.values])

        all_annual_returns = []
        self.stock_std_risks = []
        self.stock_mean_returns = []
        for symbol in symbols:
            df = self._profiler.get_ohlcv_1d(symbol, years=duration)
            df["close_returns"] = df["Close"].pct_change()
            df = df.dropna(subset=["close_returns"])
            self.dfs_1d[symbol] = df

            annual_returns = self.compute_annual_returns(df)
            all_annual_returns.append(annual_returns)

            risk = annual_returns.std()
            returns = annual_returns.mean()

            self.stock_std_risks.append(risk)
            self.stock_mean_returns.append(returns)

        self.df_1d = pd.concat(
            [df["close_returns"] for df in self.dfs_1d.values()],
            axis=1,
            keys=self.symbols,
        )
        self.df_1d = self.df_1d.dropna()

        self.returns_df = pd.concat(all_annual_returns, axis=1)
        self.returns_df.columns = self.symbols
        self.cov_matrix = self.returns_df.cov()
        self.mean_returns = np.array(self.stock_mean_returns)
        self.exp_return = self.compute_return(self.weights)
        self.exp_risk = self.compute_risk(self.weights)

    def compute_min_var_portfolio(self) -> np.ndarray:
        """Compute the minimum variance portfolio weights."""
        # Constraints and bounds for optimization
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bounds = tuple((0, 1) for _ in range(len(self.symbols)))

        # Initial guess for weights
        x0 = np.array([1 / len(self.symbols)] * len(self.symbols))

        # Minimize the portfolio risk
        result = minimize(
            fun=self.compute_risk,
            x0=x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
        if not result.success:
            raise ValueError("Optimization failed.")
        return result.x

    def compute_efficient_frontier(self, num_points=100) -> list[dict]:
        """Calculate the efficient frontier."""

        min_var_weights = self.compute_min_var_portfolio()
        min_var_return = self.compute_return(min_var_weights)
        max_var_return = self.mean_returns.max()

        # Generate target returns for efficient frontier
        target_returns = np.linspace(min_var_return, max_var_return, num_points)

        efficient_portfolios = []
        for target_return in target_returns:
            portfolio = self.compute_target_return_portfolio(target_return)
            efficient_portfolios.append(portfolio)

        return efficient_portfolios

    def compute_target_return_portfolio(self, target_return: float) -> dict:
        """Compute the portfolio weights for a given target return."""
        # Add constraint for target return
        constraints = [
            {"type": "eq", "fun": lambda x: np.sum(x) - 1},
            {
                "type": "eq",
                "fun": lambda x, target=target_return: np.dot(self.mean_returns, x)
                - target,
            },
        ]

        # Constraints and bounds for optimization
        bounds = tuple((0, 1) for _ in range(len(self.symbols)))
        x0 = np.array([1 / len(self.symbols)] * len(self.symbols))

        result = minimize(
            fun=self.compute_risk,
            x0=x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if not result.success:
            raise ValueError("Optimization failed.")

        p_return = self.compute_return(result.x)
        p_risk = self.compute_risk(result.x)

        return {"return": p_return, "risk": p_risk, "weights": result.x}

    def compute_cor_matrix(self) -> pd.DataFrame:
        """Compute the correlation matrix of the portfolio."""
        if self.returns_df.empty:
            raise ValueError("Returns DataFrame is empty. Fetch data first.")
        return self.returns_df.corr()

    def compute_return(self, weights: np.ndarray) -> float:
        """Compute the portfolio return given the weights."""
        if len(weights) != len(self.symbols):
            raise ValueError("Weights length must match number of symbols.")
        w = np.array(weights)
        weighted_returns = w.T @ self.mean_returns
        return float(weighted_returns)

    def compute_risk(self, weights: np.ndarray) -> float:
        """Compute the portfolio risk given the weights."""
        if len(weights) != len(self.symbols):
            raise ValueError("Weights length must match number of symbols.")
        w = np.array(weights)
        weighted_cov = w.T @ self.cov_matrix @ w
        return float(np.sqrt(weighted_cov))

    def weights_to_values(self, weights: np.ndarray) -> np.ndarray:
        """Convert portfolio weights to values based on the portfolio value."""
        if len(weights) != len(self.symbols):
            raise ValueError("Weights length must match number of symbols.")
        return np.array([weight * self.portfolio_value for weight in weights])

    def values_to_holdings(self, values: np.ndarray) -> np.ndarray:
        """Convert portfolio values to holdings based on the portfolio value."""
        if len(values) != len(self.symbols):
            raise ValueError("Values length must match number of symbols.")
        return np.array([value / quote for value, quote in zip(values, self._quotes)])

    def weights_to_holdings(self, weights: np.ndarray) -> np.ndarray:
        """Convert portfolio weights to holdings based on the portfolio value."""
        if len(weights) != len(self.symbols):
            raise ValueError("Weights length must match number of symbols.")
        values = self.weights_to_values(weights)
        return self.values_to_holdings(values)

    def _get_quote(self, symbol: str) -> float:
        """Get the stock quote for the given stock symbol."""
        idx = self.symbols.index(symbol)
        if idx == -1:
            raise ValueError(f"Symbol {symbol} not found in portfolio.")
        return self._quotes[idx]

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

    def compute_daily_portfolio_value(self, weights: np.ndarray) -> pd.Series:
        """
        Compute the daily portfolio value over time using daily close-to-close returns.

        Args:
            weights (np.ndarray): Portfolio weights.

        Returns:
            pd.Series: Time series of daily portfolio value.
        """

        if len(weights) != len(self.symbols):
            raise ValueError("Weights length must match number of symbols.")

        # Compute weighted portfolio daily returns
        portfolio_daily_returns = self.df_1d @ weights

        # Simulate portfolio value: start at self.portfolio_value and apply cumulative returns
        portfolio_values = (
            1 + portfolio_daily_returns
        ).cumprod() * self.portfolio_value

        return portfolio_values

    def compute_spy_portfolio_value(
        self, start_date: date, end_date: date
    ) -> pd.Series:
        """
        Compute the daily portfolio value over time using SPY as a benchmark.

        Returns:
            pd.Series: Time series of daily portfolio value.
        """

        # Fetch SPY data
        spy_df = self._profiler.dm.get_ohlcv_1d(
            "SPY", start_date=start_date, end_date=end_date
        )
        spy_df["close_returns"] = spy_df["Close"].pct_change()
        spy_df = spy_df.dropna(subset=["close_returns"])

        # Calculate SPY daily returns
        spy_daily_returns = spy_df["close_returns"]

        # Simulate SPY portfolio value: start at self.portfolio_value and apply cumulative returns
        spy_portfolio_values = (1 + spy_daily_returns).cumprod() * self.portfolio_value

        return spy_portfolio_values

    def compute_t_stats(self, weights: np.ndarray) -> dict:
        """
        Compute the T-stats for the portfolio.

        Args:
            weights (np.ndarray): Portfolio weights.

        Returns:
            dict: A dictionary containing the T-stats.
        """
        if len(weights) != len(self.symbols):
            raise ValueError("Weights length must match number of symbols.")

        # Compute daily portfolio returns
        daily_returns = self.df_1d @ weights

        # Calculate mean and standard deviation of daily returns
        mean_return = daily_returns.mean()
        std = daily_returns.std()

        # Calculate T-statistic
        t_stat = mean_return / (std / np.sqrt(len(daily_returns)))

        return {"mean_return": mean_return, "std": std, "t_stat": t_stat}
