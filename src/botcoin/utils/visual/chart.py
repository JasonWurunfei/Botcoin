"""Visual chart utilities for Botcoin."""

import pandas as pd

import plotly.graph_objects as go


def plot_candlestick(
    df: pd.DataFrame,
    title: str | None = None,
    xaxis_title: str | None = None,
    yaxis_title: str | None = None,
) -> go.Figure:
    """Plot a candlestick chart using Plotly.

    Args:
        df (DataFrame): DataFrame containing 'Open', 'High', 'Low', 'Close' columns.
        title (str): Title of the chart.
        xaxis_title (str): Title of the x-axis.
        yaxis_title (str): Title of the y-axis.

    Returns:
        Figure: A Plotly figure object.
    """
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
            )
        ]
    )

    title = title or "Candlestick Chart"
    xaxis_title = xaxis_title or "Time"
    yaxis_title = yaxis_title or "Price (USD)"

    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        height=600,
    )

    # Hide weekends and non-trading hours using range breaks
    fig.update_layout(
        xaxis={
            "rangeslider_visible": False,
            "rangebreaks": [
                {"bounds": ["sat", "mon"]},  # Skip weekends
                {
                    "bounds": [16, 9.5],
                    "pattern": "hour",
                },  # Skip outside market hours (4 PM - 9:30 AM)
            ],
        },
    )

    return fig
