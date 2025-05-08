"""This module contains diferent types of price tickers."""

import json
import random
import asyncio
from typing import Optional
from datetime import datetime
from abc import ABC, abstractmethod

import pytz
import websockets
import pandas as pd

from botcoin.utils.log import logging
from botcoin.utils.stream_data import generate_price_stream

from botcoin.data.dataclasses.events import (
    Event,
    TickEvent,
    RequestTickEvent,
    RequestStopTickEvent,
)
from botcoin.services import Service
from botcoin.data.historical import YfDataManager
from botcoin.utils.rabbitmq.conn import new_connection
from botcoin.utils.rabbitmq.event import emit_event_with_channel, EventReceiver


class Ticker(Service, EventReceiver, ABC):
    """
    Abstract base class to manage and fetch real-time price data for a list of stock symbols.
    """

    @abstractmethod
    async def subscribe(self, symbol: str) -> None:
        """Subscribes to a new ticker symbol."""

    @abstractmethod
    async def unsubscribe(self, symbol: str) -> None:
        """Unsubscribes from a ticker symbol."""

    async def on_event(self, event: Event) -> None:
        if isinstance(event, RequestTickEvent):
            asyncio.create_task(self.subscribe(event.symbol))
        elif isinstance(event, RequestStopTickEvent):
            asyncio.create_task(self.unsubscribe(event.symbol))


class FinnhubTicker(Ticker):
    """
    An async class to manage and fetch real-time price data for a list of stock symbols.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(
        self,
        api_key: str,
        tz: str = "US/Eastern",
        symbols: Optional[list[str]] = None,
    ):
        self.symbols = symbols or []
        self.tz = pytz.timezone(tz)
        self.url = f"wss://ws.finnhub.io?token={api_key}"
        self.ws = None
        self.rabbitmq_conn = None
        self.rabbitmq_channel = None

    async def start(self) -> None:
        """
        Connects to the websocket and starts streaming price data.
        """
        try:
            self.logger.info("Finnhub ticker started.")
            self.rabbitmq_conn = await new_connection()
            self.rabbitmq_channel = await self.rabbitmq_conn.channel()
            self.logger.info("RabbitMQ connection established.")
            self.ws = await websockets.connect(self.url)
            self.logger.info("WebSocket connection established.")

            # Subscribe to the symbols if any are provided
            if self.symbols:
                for symbol in self.symbols:
                    await self.ws.send(
                        json.dumps({"type": "subscribe", "symbol": symbol})
                    )

            async for message in self.ws:
                json_message = json.loads(message)
                await self._handle_message(json_message)

        finally:
            await self.stop()

    async def subscribe(self, symbol: str) -> None:
        """
        Subscribes to a new ticker symbol.
        """
        if not self.ws:
            raise ValueError("WebSocket connection is not established.")

        if symbol not in self.symbols:
            self.symbols.append(symbol)
            await self.ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
            self.logger.info("Subscribed to %s", symbol)

    async def unsubscribe(self, symbol: str) -> None:
        """
        Unsubscribes from a symbol symbol.
        """
        if not self.ws:
            raise ValueError("WebSocket connection is not established.")

        if symbol in self.symbols:
            self.symbols.remove(symbol)
            await self.ws.send(json.dumps({"type": "unsubscribe", "symbol": symbol}))
            self.logger.info("Unsubscribed from %s", symbol)
        else:
            self.logger.warning("Symbol %s not found in subscribed symbols.", symbol)

    async def _handle_message(self, message: dict):
        """
        Handles incoming WebSocket messages.
        """

        records = message.get("data")
        if records:
            for record in records:
                # Extract the relevant fields from the message
                t = datetime.fromtimestamp(record["t"] / 1000, tz=self.tz)
                p = float(record["p"])
                s = record["s"]

                # Create a TickEvent object and log it
                tick_evt = TickEvent(
                    event_time=t,
                    symbol=s,
                    price=p,
                )
                self.logger.debug(tick_evt)

                # Publish the tick event to the RabbitMQ channel
                asyncio.create_task(
                    emit_event_with_channel(tick_evt, self.rabbitmq_channel)
                )

    async def stop(self) -> None:
        """
        Stops the ticker service and closes RabbitMQ resources.
        """
        if self.rabbitmq_channel and not self.rabbitmq_channel.is_closed:
            await self.rabbitmq_channel.close()
            self.logger.debug("RabbitMQ channel closed.")
        self.rabbitmq_channel = None

        if self.rabbitmq_conn and not self.rabbitmq_conn.is_closed:
            await self.rabbitmq_conn.close()
            self.logger.debug("RabbitMQ connection closed.")
        self.rabbitmq_conn = None

        if self.ws and not self.ws.closed:
            await self.ws.close()
            self.logger.debug("WebSocket connection closed.")
        self.ws = None

        self.logger.info("Finnhub ticker stopped.")


class HistoricalTicker(Ticker):
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
    ):
        self.symbols = symbols or []
        self.tz = pytz.timezone(tz)
        self.start_date = self.tz.localize(start_date)
        self.end_date = self.tz.localize(end_date)
        self.real_time = real_time
        self.candle_duration = candle_duration
        self.avg_freq_per_minute = avg_freq_per_minute
        self.streaming_symbols = {}
        self.rabbitmq_conn = None
        self.rabbitmq_channel = None

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

    async def start(self) -> None:
        """
        Starts the price stream generation for all symbols.
        """
        try:
            self.logger.info("Historical price ticker started.")
            self.rabbitmq_conn = await new_connection()
            self.rabbitmq_channel = await self.rabbitmq_conn.channel()
            self.logger.info("RabbitMQ connection established.")
            if self.symbols:
                tasks = []
                for symbol in self.symbols:
                    task = self.stream_symbol(symbol)
                    tasks.append(task)
                await asyncio.gather(*tasks)
            else:
                await asyncio.Event().wait()  # Will never be set, so blocks forever

        finally:
            await self.stop()

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
            # create a tick event
            tick_evt = TickEvent(
                event_time=index.to_pydatetime(),
                symbol=symbol,
                price=row["price"],
            )
            self.logger.info(tick_evt)

            # publish the tick event to the RabbitMQ channel
            asyncio.create_task(
                emit_event_with_channel(tick_evt, self.rabbitmq_channel)
            )

            # if real_time, sleep until the next timestamp
            if real_time and index != prices.index[-1]:
                next_index = prices.index[prices.index.get_loc(index) + 1]
                # Calculate the time to sleep until the next timestamp
                sleep_time = (next_index - index).total_seconds()
                await asyncio.sleep(sleep_time)

    async def stop(self) -> None:
        """
        Stops the historical ticker service and closes RabbitMQ resources.
        """
        if self.rabbitmq_channel and not self.rabbitmq_channel.is_closed:
            await self.rabbitmq_channel.close()
            self.logger.debug("RabbitMQ channel closed.")
        self.rabbitmq_channel = None

        if self.rabbitmq_conn and not self.rabbitmq_conn.is_closed:
            await self.rabbitmq_conn.close()
            self.logger.debug("RabbitMQ connection closed.")
        self.rabbitmq_conn = None

        # Cancel all streaming tasks
        for symbol, task in self.streaming_symbols.items():
            if not task.done():
                task.cancel()
                self.logger.debug("Cancelled streaming task for %s", symbol)

        await asyncio.gather(*self.streaming_symbols.values(), return_exceptions=True)
        self.streaming_symbols.clear()

        self.logger.info("Historical ticker stopped.")


class FakeTicker(Ticker):
    """
    A class to manage and fetch fake price data for a list of stock symbols.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(self, tz: str = "US/Eastern"):
        self.tz = pytz.timezone(tz)
        self.symbols = set()
        self.rabbitmq_conn = None
        self.rabbitmq_channel = None

    async def subscribe(self, symbol: str) -> None:
        """
        Subscribes to a new ticker symbol.
        """
        self.symbols.add(symbol)
        self.logger.info("Subscribed to %s", symbol)

    async def unsubscribe(self, symbol: str) -> None:
        """
        Unsubscribes from a symbol.
        """
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            self.logger.info("Unsubscribed from %s", symbol)
        else:
            self.logger.warning("Symbol %s not found in subscribed symbols.", symbol)

    async def start(self) -> None:
        """
        Starts the ticker service.
        """
        try:
            self.logger.info("Fake ticker started.")
            self.rabbitmq_conn = await new_connection()
            self.rabbitmq_channel = await self.rabbitmq_conn.channel()
            while True:
                if not self.symbols:
                    await asyncio.sleep(0.1)
                    continue

                # Randomly pick a symbol and generate a fake price
                symbol = random.choice(list(self.symbols))
                price = random.uniform(100, 200)

                tick_evt = TickEvent(
                    symbol=symbol,
                    price=price,
                )

                self.logger.info(tick_evt)
                asyncio.create_task(
                    emit_event_with_channel(tick_evt, self.rabbitmq_channel)
                )
                await asyncio.sleep(1)

        finally:
            await self.stop()

    async def stop(self) -> None:
        """
        Stops the ticker service and closes RabbitMQ resources.
        """
        if self.rabbitmq_channel and not self.rabbitmq_channel.is_closed:
            await self.rabbitmq_channel.close()
            self.logger.debug("RabbitMQ channel closed.")
        self.rabbitmq_channel = None

        if self.rabbitmq_conn and not self.rabbitmq_conn.is_closed:
            await self.rabbitmq_conn.close()
            self.logger.debug("RabbitMQ connection closed.")
        self.rabbitmq_conn = None

        self.logger.info("Fake ticker stopped.")
