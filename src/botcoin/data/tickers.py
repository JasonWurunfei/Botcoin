"""This module contains diferent types of price tickers."""

import os
import json
import asyncio
from datetime import datetime

import pytz
import websockets
import pandas as pd
from dotenv import load_dotenv

from botcoin.utils.log import logging
from botcoin.utils.message_queue import BroadcastQueue
from botcoin.utils.stream_data import generate_price_stream

from botcoin.data.dataclasses import TickEvent
from botcoin.data.historical import YfDataManager


# Load variables from .env file into environment
load_dotenv()


class FinnhubTicker:
    """
    An async class to manage and fetch real-time price data for a list of stock symbols.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(
        self,
        tz: str = "US/Eastern",
        symbols: list[str] = None,
        tick_broadcast: BroadcastQueue = None,
    ):
        self.symbols = symbols or []
        self.tz = pytz.timezone(tz)
        self.url = f"wss://ws.finnhub.io?token={os.getenv('FINNHUB_TOKEN')}"
        self.tick_queue = tick_broadcast or BroadcastQueue()
        self.ws = None

    def stream(self) -> None:
        """
        Starts the WebSocket connection and begins streaming price data.
        """
        return asyncio.create_task(self._stream())

    async def _stream(self):
        """
        Connects to the websocket and starts streaming price data.
        """
        while True:
            try:
                async with websockets.connect(self.url) as ws:
                    self.ws = ws
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
        Subscribes to the given symbols.
        """
        for ticker in self.symbols:
            await ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))
            self.logger.info("Subscribed to %s", ticker)

    async def subscribe(self, symbol: str):
        """
        Subscribes to a new ticker symbol.
        """
        try:
            if not self.ws:
                raise ValueError("WebSocket connection is not established.")
            if symbol not in self.symbols:
                self.symbols.append(symbol)
                await self.ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
                self.logger.info("Subscribed to %s", symbol)
        except ValueError as e:
            self.logger.error("WebSocket connection error: %s", e)
            return

    async def unsubscribe(self, symbol: str):
        """
        Unsubscribes from a symbol symbol.
        """
        try:
            if not self.ws:
                raise ValueError("WebSocket connection is not established.")

            if symbol in self.symbols:
                self.symbols.remove(symbol)
                await self.ws.send(
                    json.dumps({"type": "unsubscribe", "symbol": symbol})
                )
                self.logger.info("Unsubscribed from %s", symbol)
            else:
                self.logger.warning(
                    "Symbol %s not found in subscribed symbols.", symbol
                )

        except ValueError as e:
            self.logger.error("WebSocket connection error: %s", e)
            return

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


class HistoricalTicker:
    """
    A price ticker class that generates simulated price ticks
    from historical OHLC data.
    This class is used for backtesting and simulating price streams.
    It generates price ticks based on historical data and simulates real-time updates.
    It uses a Poisson distribution to determine the number of price points to simulate
    within a given candle duration.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        symbols: list[str] = None,
        tz: str = "US/Eastern",
        real_time: bool = True,
        candle_duration="1min",
        avg_freq_per_minute=12,
        tick_broadcast: BroadcastQueue = None,
    ):
        self.symbols = symbols or []
        self.tz = pytz.timezone(tz)
        self.start_date = self.tz.localize(start_date)
        self.end_date = self.tz.localize(end_date)
        self.real_time = real_time
        self.candle_duration = candle_duration
        self.avg_freq_per_minute = avg_freq_per_minute
        self.tick_queue = tick_broadcast or BroadcastQueue()
        self.streaming_symbols = {}

    def get_historical_data(self, symbol: str) -> pd.DataFrame:
        """
        Fetches historical data for the given symbol.
        """
        hdm = YfDataManager(symbol=symbol)
        df = hdm.get_data(start=self.start_date, end=self.end_date)
        return df

    def generate_price_stream(self, symbol: str) -> pd.DataFrame:
        """
        Generates a price stream from historical data for the given symbol.
        """
        df = self.get_historical_data(symbol)
        prices = generate_price_stream(
            df,
            candle_duration=self.candle_duration,
            avg_freq_per_minute=self.avg_freq_per_minute,
        )
        return prices

    async def stream(self) -> None:
        """
        Starts the price stream generation for all symbols.
        """
        tasks = []
        for symbol in self.symbols:
            task = self.stream_symbol(symbol)
            tasks.append(task)
        await asyncio.gather(*tasks)

    def stream_symbol(self, symbol: str) -> None:
        """
        Starts the price stream generation for a specific symbol.
        """
        prices = self.generate_price_stream(symbol)
        task = asyncio.create_task(
            self.replay_price_stream(symbol, prices, real_time=self.real_time)
        )
        self.streaming_symbols[symbol] = task
        self.logger.info("Started streaming for %s", symbol)
        return task

    async def subscribe(self, symbol: str) -> None:
        """
        Subscribes to a new ticker symbol and starts streaming its price data.
        """
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            self.stream_symbol(symbol)
            self.logger.info("Subscribed to %s", symbol)

    async def unsubscribe(self, symbol: str) -> None:
        """
        Unsubscribes from a symbol and stops streaming its price data.
        """
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            task = self.streaming_symbols.pop(symbol, None)
            if task:
                task.cancel()
                self.logger.info("Unsubscribed from %s", symbol)
            else:
                self.logger.warning("No active stream for %s", symbol)
        else:
            self.logger.warning("Symbol %s not found in subscribed symbols.", symbol)

    async def replay_price_stream(
        self, symbol, prices: pd.DataFrame, real_time: bool = True
    ) -> None:
        """
        Simulates the replay of price ticks from the generated price stream.

        args:
            prices (pd.DataFrame): A DataFrame containing price data with timestamps.
            real_time (bool): If True, simulates real-time updates. Defaults to True.
                              If False, replays all data in sequential order without delay.
        """
        for index, row in prices.iterrows():
            tick_evt = TickEvent(
                event_time=index.to_pydatetime(),
                symbol=symbol,
                price=row["price"],
            )
            self.logger.info(tick_evt)

            await self.tick_queue.publish(tick_evt)

            if real_time and index != prices.index[-1]:
                next_index = prices.index[prices.index.get_loc(index) + 1]
                # Calculate the time to sleep until the next timestamp
                sleep_time = (next_index - index).total_seconds()
                await asyncio.sleep(sleep_time)

    def get_broadcast_queue(self) -> BroadcastQueue:
        """
        Returns the broadcast queue for price ticks.
        """
        return self.tick_queue
