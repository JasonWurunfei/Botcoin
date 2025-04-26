"""This script is used to plot the historical data of a stock ticker."""

from datetime import datetime
import plotly.graph_objects as go
from botcoin.data.historical import YfDataManager

hdm = YfDataManager(ticker="AAPL")

# Create a naive datetime
start = datetime(year=2025, month=4, day=15, hour=0, minute=0, second=0)
end = datetime(year=2025, month=4, day=16, hour=0, minute=0, second=0)

start = hdm.tz.localize(start)
end = hdm.tz.localize(end)

df = hdm.get_data(start=start, end=end)

# Plot candlestick chart
fig = go.Figure(
    data=[
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="AAPL",
        )
    ]
)

fig.update_layout(
    title="AAPL 1-Min Candlestick Chart",
    xaxis_title="Time",
    yaxis_title="Price (USD)",
    xaxis_rangeslider_visible=False,
    template="plotly_white",
    height=600,
)

# Hide weekends and non-trading hours using range breaks
fig.update_layout(
    xaxis=dict(
        rangeslider_visible=False,
        rangebreaks=[
            dict(bounds=["sat", "mon"]),  # Skip weekends
            dict(
                bounds=[16, 9.5], pattern="hour"
            ),  # Skip outside market hours (4 PM - 9:30 AM)
        ],
    ),
)

fig.show()
