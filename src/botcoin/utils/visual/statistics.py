"""This module contains utility functions for visualizing statistics in the Botcoin application."""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


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
