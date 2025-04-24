"""This module is used to fetch historical and real-time data for stock tickers."""

import os
import json
import asyncio
from datetime import datetime, timedelta

import websockets
import pytz
import numpy as np
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

from botcoin.utils.message_queue import BroadcastQueue
from botcoin.utils.log import logging
from botcoin.data.dataclasses import TickEvent

# Load variables from .env file into environment
load_dotenv()


class HistoricalDataManager:
    """
    A class to manage and fetch 1-minute candlestick data from Yahoo Finance.
    Data is stored locally to avoid repeated requests for the same data.

    Attributes:
        ticker (str): The stock ticker symbol.
        data_folder (str): Folder where data will be saved locally.
        tz (str): Timezone for the data, default is 'US/Eastern'.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(self, ticker: str, data_folder: str = "data", tz: str = "US/Eastern"):
        """
        Initializes the HistoricalDataManager with the given ticker and data folder.

        Args:
            ticker (str): The stock ticker symbol to fetch data for.
            data_folder (str, optional): Folder to store local data. Defaults to 'data'.
        """
        self.ticker = ticker
        self.data_folder = data_folder
        self.tz = pytz.timezone(tz)
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
        self.data = self._load_local_data()

    def _get_local_data_path(self) -> str:
        """
        Returns the local file path where the data for the ticker is stored.

        Returns:
            str: Local path to the data file.
        """
        return os.path.join(self.data_folder, f"{self.ticker}_1min_data.parquet")

    def _fetch_data(self, start: datetime, end: datetime) -> pd.DataFrame:
        """
        Fetches 1-minute interval candlestick data from Yahoo Finance, split into chunks if necessary.

        Args:
            start (datetime): Start date and time for the data request.
            end (datetime): End date and time for the data request.

        Returns:
            pd.DataFrame: DataFrame containing the 1-minute candlestick data.
        """
        max_days = 7  # Yahoo Finance limits to ~7 days for 1m interval
        all_data = []

        current_start = start
        while current_start < end:
            current_end = min(current_start + timedelta(days=max_days), end)
            self.logger.info("Fetching data from %s to %s", current_start, current_end)

            # Fetch data from yfinance
            df = yf.download(
                self.ticker,
                start=current_start,
                end=current_end,
                interval="1m",
                progress=False,
                multi_level_index=False,
            )

            if not df.empty:
                df.index = pd.to_datetime(df.index)
                df.index = df.index.tz_convert(self.tz)
                df = df[~df.index.duplicated(keep="last")]  # Remove duplicated index
                all_data.append(df)

            current_start = current_end

        return pd.concat(all_data) if all_data else pd.DataFrame()

    def check_data_in_local(self, start: datetime, end: datetime) -> bool:
        """
        Checks if data for the given date range already exists in local storage.

        Args:
            start (datetime): Start date and time for the data request.
            end (datetime): End date and time for the data request.

        Returns:
            bool: True if the data exists in local storage, False otherwise.
        """
        data_path = self._get_local_data_path()

        if os.path.exists(data_path):
            local_data = self.data
            local_start = local_data.index.min()
            local_end = local_data.index.max()

            # If the requested range is within the range of the local data, no need to fetch
            if local_start <= start and local_end >= end:
                return True
        return False

    def _load_local_data(self) -> pd.DataFrame:
        """
        Loads the data from local storage.

        Returns:
            pd.DataFrame: DataFrame containing the local data.
        """
        data_path = self._get_local_data_path()
        if os.path.exists(data_path):
            df = pd.read_parquet(data_path)
            df.index = pd.to_datetime(df.index)
            df.index = df.index.tz_convert(self.tz)
            return df
        return pd.DataFrame()

    def _merge_data(self, new_data: pd.DataFrame) -> None:
        """
        Merges new data into the existing local data.

        Args:
            new_data (pd.DataFrame): New data to be merged.
        """
        if not new_data.empty:
            # Concatenate new data with existing data
            self.data = pd.concat([self.data, new_data])
            # Drop duplicates and sort by index
            self.data = self.data[~self.data.index.duplicated(keep="last")].sort_index()
            # Save the merged data back to local storage
            self.data.to_parquet(self._get_local_data_path())
            self.logger.info("Data merged and saved to %s", self._get_local_data_path())
        else:
            self.logger.warning("No new data to merge.")

    def get_data(self, start: datetime, end: datetime) -> pd.DataFrame:
        """
        Retrieves 1-minute candlestick data for the specified date range.
        If data is available locally, it will be used. If not, it will be fetched from Yahoo Finance.

        Args:
            start (datetime): Start date and time for the data request.
            end (datetime): End date and time for the data request.

        Returns:
            pd.DataFrame: DataFrame containing the 1-minute candlestick data.
        """
        # Ensure the start is before the end
        if start > end:
            raise ValueError("Start date must be before end date.")

        # Ensure the date range is within the last 30 days
        today = datetime.today().replace(tzinfo=self.tz)
        if start < today - timedelta(days=30):
            raise ValueError("Data requests cannot go beyond 30 days in the past.")

        # Check if data is already available locally
        if self.check_data_in_local(start, end):
            self.logger.info("Data is already available locally.")
            return self.data[(self.data.index >= start) & (self.data.index <= end)]

        # Fetch data from Yahoo Finance if not available locally
        self.logger.info("Fetching data from Yahoo Finance.")
        df = self._fetch_data(start, end)

        # Save the fetched data locally for future use
        if not df.empty:
            self._merge_data(df)

        return df


class PriceTicker:
    """
    An async class to manage and fetch real-time price data for a list of stock tickers.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(
        self,
        tickers: list[str],
        tz: str = "US/Eastern",
        tick_broadcast: BroadcastQueue = None,
    ):
        self.tickers = tickers
        self.tz = pytz.timezone(tz)
        self.url = f"wss://ws.finnhub.io?token={os.getenv('FINNHUB_TOKEN')}"
        self.tick_queue = tick_broadcast or BroadcastQueue()

    async def connect(self):
        """
        Connects to the websocket and starts streaming price data.
        """
        while True:
            try:
                async with websockets.connect(self.url) as ws:
                    await self._subscribe(ws)
                    self.logger.info("WebSocket connection established.")

                    while True:
                        message = await ws.recv()
                        await self._handle_message(message)

            except websockets.ConnectionClosed:
                self.logger.warning(
                    "WebSocket connection closed. Reconnecting in 5 seconds..."
                )
                await asyncio.sleep(5)

            except asyncio.TimeoutError as e:
                self.logger.exception("Unexpected error: %s", e)
                await asyncio.sleep(5)

    async def _subscribe(self, ws):
        """
        Subscribes to the given tickers.
        """
        for ticker in self.tickers:
            await ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))
            self.logger.info("Subscribed to %s", ticker)

    async def _handle_message(self, message: str):
        """
        Handles incoming WebSocket messages.
        """
        try:
            msg = json.loads(message)
            records = msg.get("data", None)
            if records:
                for record in records:
                    t = datetime.fromtimestamp(record["t"] / 1000, tz=self.tz)
                    p = float(record["p"])
                    s = record["s"]
                    await self.on_message(s, t, p)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.warning("Failed to parse message: %s", e)

    async def on_message(self, s: str, t: datetime, p: float):
        """
        Called when a new price tick is received.
        Override or hook into this for custom behavior.
        """
        tick_evt = TickEvent(
            event_type="tick",
            event_time=t,
            symbol=s,
            price=p,
        )
        self.logger.info(tick_evt)

        await self.tick_queue.publish(tick_evt)

    def get_broadcast_queue(self) -> BroadcastQueue:
        """
        Returns the broadcast queue for price ticks.
        """
        return self.tick_queue


def generate_price_stream(
    ohlc_df, candle_duration="1min", avg_freq_per_minute=10, seed=None
):
    """
    Simulate real-time price updates from historical OHLC data.

    Args:
        ohlc_df (pd.DataFrame): DataFrame with ['DatetimeIndex', 'open', 'high', 'low', 'close', 'volume'].
        candle_duration (str): Duration of each OHLC candle (e.g., '1min', '5min').
        avg_freq_per_minute (int): Average number of price points to simulate per minute.
        seed (int): Random seed for reproducibility.

    Returns:
        pd.DataFrame: DataFrame with ['DatetimeIndex', 'price'].
    """
    if seed is not None:
        np.random.seed(seed)

    result = []

    for idx, row in ohlc_df.iterrows():
        start_time = idx.to_pydatetime()
        duration = pd.to_timedelta(candle_duration)

        # Number of points for this candle
        n_points = np.random.poisson(
            avg_freq_per_minute * duration / pd.Timedelta("1min")
        )
        n_points = max(n_points, 4)  # ensure at least open, high, low, close

        # Generate random timestamps within the candle period
        random_offsets = sorted(
            np.random.uniform(0, duration.total_seconds(), size=n_points)
        )
        timestamps = [
            start_time + timedelta(seconds=offset) for offset in random_offsets
        ]

        # Ensure first, high, low, and last prices are in the stream
        prices = [row["Open"], row["High"], row["Low"], row["Close"]]

        # Fill the rest with random prices between low and high
        remaining = n_points - 4
        if remaining > 0:
            random_prices = np.random.uniform(
                row["Low"], row["High"], size=remaining
            ).tolist()
            prices.extend(random_prices)

        # Shuffle all prices except open, high, low, close for randomness
        np.random.shuffle(prices[1:-1])  # keep open at start and close at end

        # Pair timestamps with sorted (by time) prices
        stream = list(zip(timestamps, prices))
        stream.sort(key=lambda x: x[0])  # sort by timestamp again

        result.extend(stream)

    return pd.DataFrame(result, columns=["timestamp", "price"]).set_index("timestamp")
