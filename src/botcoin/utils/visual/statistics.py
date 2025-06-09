"""This module contains utility functions for visualizing statistics in the Botcoin application."""

import matplotlib.pyplot as plt
import seaborn as sns


def plot_kde_with_stats(data_series, title="KDE Plot"):
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

    # Convert to percentage
    data_percent = data_series * 100
    mean_percent = mean * 100
    std_percent = std * 100

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
