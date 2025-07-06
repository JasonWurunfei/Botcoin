"""This module contains utility functions for visualizing statistics in the Botcoin application."""

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import seaborn as sns


from botcoin.profilers.stock import StockProfiler


def plot_kde_with_stats(data_series: pd.Series, title: str = "KDE Plot") -> None:
    """
    Plots KDE curve with mean and ±1 standard deviation lines,
    with rug scatter of individual data points.

    Parameters:
    - data_series: pd.Series
        The data to plot. Should be numeric.
    - title: str
        The title of the plot.
    """
    # Compute statistics
    mean = data_series.mean()
    std = data_series.std()
    median = data_series.median()

    # Convert to percentage
    data_percent = data_series * 100
    data_percent = data_percent.to_numpy()
    mean_percent = mean * 100
    std_percent = std * 100
    median_percent = median * 100

    # Plot
    plt.figure(figsize=(12, 6))

    # KDE curve
    sns.kdeplot(data_percent, color="blue", linewidth=2, label="KDE")

    # Mean and ±1 std lines
    plt.axvline(
        mean_percent,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mean = {mean_percent:.6f}%",
    )
    plt.axvline(
        median_percent,
        color="orange",
        linestyle="--",
        linewidth=2,
        label=f"Median = {median_percent:.6f}%",
    )
    plt.axvline(
        mean_percent - std_percent,
        color="green",
        linestyle="--",
        linewidth=2,
        label=f"-1 Std = {mean_percent - std_percent:.6f}%",
    )
    plt.axvline(
        mean_percent + std_percent,
        color="green",
        linestyle="--",
        linewidth=2,
        label=f"+1 Std = {mean_percent + std_percent:.6f}%",
    )

    # Rug scatter
    sns.rugplot(data_percent, height=0.05, color="black", alpha=0.3)

    # Final touches
    plt.title(title)
    plt.xlabel("Value (in %)")
    plt.ylabel("Density")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_price_histogram_with_stats(
    price_series: pd.Series,
    current_price: float,
    title: str = "Price Histogram",
    bins: int = 200,
):
    """
    Plots a histogram and KDE of a price series with mean and ±1 std deviation.

    Parameters:
    - price_series: pd.Series
        Series of prices.
    - current_price: float
        Current price to highlight on the plot.
    - title: str
        Title for the plot.
    - bins: int
        Number of histogram bins.
    """
    # Calculate stats
    mean = price_series.mean()
    std = price_series.std()
    median = price_series.median()

    # Plot
    plt.figure(figsize=(12, 6))

    # Histogram + KDE
    sns.histplot(
        price_series.to_numpy(),
        bins=bins,
        kde=True,
        color="skyblue",
        edgecolor="black",
        stat="density",
        label="Histogram + KDE",
    )

    # Vertical lines for mean and ±1 std
    plt.axvline(
        mean,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mean = {mean:.2f}",
    )
    plt.axvline(
        median,
        color="orange",
        linestyle="--",
        linewidth=2,
        label=f"Median = {median:.2f}",
    )
    plt.axvline(
        mean - std,
        color="green",
        linestyle="--",
        linewidth=2,
        label=f"-1 Std = {mean - std:.2f}",
    )
    plt.axvline(
        mean + std,
        color="green",
        linestyle="--",
        linewidth=2,
        label=f"+1 Std = {mean + std:.2f}",
    )
    plt.axvline(
        current_price,
        color="purple",
        linestyle="--",
        linewidth=2,
        label=f"Current Price = {current_price:.2f}",
    )

    # Final touches
    plt.title(title)
    plt.xlabel("Price")
    plt.ylabel("Density")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_fourier_results(
    symbol: str,
    periods: pd.Series,
    magnitudes: pd.Series,
    dominant_periods: pd.Series,
    dominant_magnitudes: pd.Series,
):
    """
    Plots the results of Fourier analysis.

    Parameters:
    - periods: pd.Series
        Series of periods (in days).
    - magnitudes: pd.Series
        Series of magnitudes corresponding to the periods.
    - dominant_periods: pd.Series
        Series of dominant periods to highlight.
    - dominant_magnitudes: pd.Series
        Series of magnitudes corresponding to the dominant periods.
    - title: str
        Title for the plot.
    """
    _, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Plot frequency spectrum
    ax1.plot(periods, magnitudes, alpha=0.7)
    ax1.set_xlim(1, 365 * 2)  # Focus on 1 day to 2 years
    ax1.set_xlabel("Period (Days)")
    ax1.set_ylabel("Magnitude")
    ax1.set_title(f"{symbol} - Frequency Spectrum")
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale("log")

    # Highlight dominant periods
    for i, (period, mag) in enumerate(
        zip(dominant_periods[:5], dominant_magnitudes[:5])
    ):
        if 1 <= period <= 365 * 2:
            ax1.axvline(x=period, color="red", linestyle="--", alpha=0.7)
            ax1.text(
                period,
                mag,
                f"{period:.0f}d",
                rotation=90,
                verticalalignment="bottom",
                fontsize=8,
            )

    # Plot dominant periods as bar chart
    periods_to_show = dominant_periods[dominant_periods <= 365 * 2]
    magnitudes_to_show = dominant_magnitudes[dominant_periods <= 365 * 2]

    ax2.bar(range(len(periods_to_show)), magnitudes_to_show, alpha=0.7)
    ax2.set_xlabel("Rank")
    ax2.set_ylabel("Magnitude")
    ax2.set_title("Top Seasonal Periods")
    ax2.set_xticks(range(len(periods_to_show)))
    ax2.set_xticklabels([f"{p:.0f}d" for p in periods_to_show], rotation=45)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def plot_efficient_frontier(
    symbols: list[str],
    portfolio_weights: list[float] | None = None,
    num_portfolios: int = 1000,
) -> None:
    """
    Plots the efficient frontier for a list of stock symbols.

    Args:
        symbols (list[str]): A list of stock symbols.
        portfolio_weights (list[float]): A list of portfolio weights corresponding to the symbols.
        num_portfolios (int): Number of random portfolios to generate for the frontier.
    """
    profiler = StockProfiler()

    sns.set_theme(style="whitegrid", context="talk")
    plt.figure(figsize=(12, 10))

    ax = plt.gca()  # Get current axes to customize grid later

    # Collect all historical returns data
    all_returns_data = []
    stock_risks = []
    stock_returns = []

    # Plot individual stocks
    for symbol in symbols:
        annual_returns = profiler.get_annual_returns(symbol)
        all_returns_data.append(annual_returns)

        risk = annual_returns.std()
        returns = annual_returns.mean()

        stock_risks.append(risk)
        stock_returns.append(returns)

        sns.scatterplot(
            x=[risk],
            y=[returns],
            label=symbol,
            s=100,
            edgecolor="black",
            alpha=0.8,
        )

    # Create DataFrame and covariance matrix
    returns_df = pd.concat(all_returns_data, axis=1)
    returns_df.columns = symbols
    cov_matrix = returns_df.cov().values
    mean_returns = np.array(stock_returns)

    # Plot portfolio
    w = np.array(portfolio_weights)
    portfolio_return = np.dot(w, mean_returns)
    portfolio_risk = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))

    # Plot a star for the portfolio
    sns.scatterplot(
        x=[portfolio_risk],
        y=[portfolio_return],
        color="red",
        s=200,
        edgecolor="black",
        marker="*",
        label="Portfolio",
    )

    # Plot random portfolios
    for _ in range(num_portfolios):
        # Generate random weights
        weights = np.random.dirichlet(np.ones(len(symbols)) * 0.2)
        weights /= np.sum(weights)  # Normalize to sum to 1

        # Calculate portfolio return and risk
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        # Plot the portfolio on the scatter plot
        sns.scatterplot(
            x=[portfolio_risk],
            y=[portfolio_return],
            color="blue",
            s=10,
            alpha=0.5,
        )

    # Calculate efficient frontier
    # Constraints and bounds for optimization
    constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
    bounds = tuple((0, 1) for _ in range(len(symbols)))

    # Initial guess for weights
    x0 = np.array([1 / len(symbols)] * len(symbols))

    # Find minimum variance portfolio
    min_var_result = minimize(
        lambda x: np.sqrt(np.dot(x.T, np.dot(cov_matrix, x))),
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    min_var_return = np.dot(min_var_result.x, mean_returns)

    # plot minimum variance portfolio
    sns.scatterplot(
        x=[np.sqrt(np.dot(min_var_result.x.T, np.dot(cov_matrix, min_var_result.x)))],
        y=[min_var_return],
        color="purple",
        s=150,
        edgecolor="black",
        marker="*",
        label="Min Variance Portfolio",
    )

    print("Minimum Variance Portfolio Weights:", min_var_result.x)

    max_var_return = mean_returns.max()
    # Generate target returns for efficient frontier
    target_returns = np.linspace(min_var_return, max_var_return, 100)

    efficient_portfolios = []

    risk_free_rate = 0.02  # Assuming a risk-free rate of 2%
    tangency_portfolio = None
    tangency_portfolio_return = 0
    tangency_portfolio_risk = 0
    sharp_ratio = -np.inf
    for target_return in target_returns:
        # Objective function to minimize risk for a given target return
        def objective(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        # Constraints for optimization
        constraints = [
            {"type": "eq", "fun": lambda x: np.sum(x) - 1},  # Weights sum to 1
            {
                "type": "eq",
                "fun": lambda x, target=target_return: np.dot(mean_returns, x) - target,
            },  # Target return
        ]

        # Optimize portfolio weights
        result = minimize(
            objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if result.success:
            efficient_portfolios.append(
                {
                    "risk": np.sqrt(np.dot(result.x.T, np.dot(cov_matrix, result.x))),
                    "return": target_return,
                }
            )

        # Calculate Sharpe ratio
        portfolio_return = np.dot(result.x, mean_returns)
        portfolio_risk = np.sqrt(np.dot(result.x.T, np.dot(cov_matrix, result.x)))
        current_sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_risk
        if current_sharpe_ratio > sharp_ratio:
            sharp_ratio = current_sharpe_ratio
            tangency_portfolio = result.x
            tangency_portfolio_return = portfolio_return
            tangency_portfolio_risk = portfolio_risk

    # Convert to DataFrame for easier plotting
    efficient_df = pd.DataFrame(efficient_portfolios)

    # Plot the maximum Sharpe ratio portfolio
    sns.scatterplot(
        x=[tangency_portfolio_risk],
        y=[tangency_portfolio_return],
        color="orange",
        s=150,
        edgecolor="black",
        marker="*",
        label="Max Sharpe Ratio Portfolio",
    )

    print("Tangency Portfolio Weights:", tangency_portfolio)

    # Plot the Capital Market Line
    sns.lineplot(
        x=[0, tangency_portfolio_risk],
        y=[risk_free_rate, tangency_portfolio_return],
        color="red",
        label="Capital Market Line",
    )

    # Plot the efficient frontier
    sns.lineplot(
        data=efficient_df,
        x="risk",
        y="return",
        color="green",
        label="Efficient Frontier",
    )

    # Add more detailed gridlines
    ax.xaxis.set_major_locator(
        ticker.MultipleLocator(0.05)
    )  # e.g. grid every 0.05 on x-axis
    ax.yaxis.set_major_locator(ticker.MultipleLocator(0.01))
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())

    # Customize tick labels
    plt.xticks(fontsize=10, rotation=30)
    plt.yticks(fontsize=10, rotation=0)

    plt.xlim(left=0)  # x-axis (Risk) starts at 0
    plt.ylim(bottom=0)  # y-axis (Return) starts at 0

    plt.title("Efficient Frontier")
    plt.xlabel("Risk (Standard Deviation)")
    plt.ylabel("Expected Return")
    # Legend outside plot area
    plt.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        borderaxespad=0,
        fontsize=12,
        title="Symbols",
    )
    plt.grid(True)
    plt.show()
