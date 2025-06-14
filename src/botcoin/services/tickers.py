"""This module contains diferent types of price tickers."""

import json
import random
import asyncio
from typing import Optional, override
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
    TimeStepEvent,
)
from botcoin.services import Service
from botcoin.data.historical import YfDataManager
from botcoin.utils.rabbitmq.async_client import AsyncAMQPClient
from botcoin.utils.rabbitmq.event import EventReceiver


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
        self._async_client = AsyncAMQPClient()
        self._async_client.set_logger_name("FinnhubTicker")

    async def start(self) -> None:
        """
        Connects to the websocket and starts streaming price data.
        """
        try:
            self.logger.info("Finnhub ticker started.")
            await self._async_client.connect()
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
                self._async_client.emit_event(tick_evt)

    async def stop(self) -> None:
        """
        Stops the ticker service and closes RabbitMQ resources.
        """
        await self._async_client.close()

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
        self._async_client = AsyncAMQPClient()
        self._async_client.set_logger_name("HistoricalTicker")

    def get_historical_data(self, symbol: str) -> pd.DataFrame:
        """
        Fetches historical data for the given symbol.
        """
        hdm = YfDataManager(tz=str(self.tz))
        df = hdm.get_ohlcv_1min(
            symbol, start_date=self.start_date.date(), end_date=self.end_date.date()
        )
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
            await self._async_client.connect()
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
                event_time=pd.to_datetime(index, unit="s"),
                symbol=symbol,
                price=round(row["price"], 3),  # round to 3 decimal places
            )
            self.logger.info(tick_evt)

            # publish the tick event to the RabbitMQ channel
            self._async_client.emit_event(tick_evt)

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
        await self._async_client.close()

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
        self._async_client = AsyncAMQPClient()
        self._async_client.set_logger_name("FakeTicker")

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
            await self._async_client.connect()
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
                self._async_client.emit_event(tick_evt)
                await asyncio.sleep(1)

        finally:
            await self.stop()

    async def stop(self) -> None:
        """
        Stops the ticker service and closes RabbitMQ resources.
        """
        await self._async_client.close()
        self.logger.info("Fake ticker stopped.")


class SimulatedTicker(Ticker):
    """
    A class to manage and fetch simulated price data for a list of stock symbols.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(self, from_: datetime, to: datetime, tz: str = "US/Eastern"):
        """
        Initializes the simulated ticker with a time range and timezone.

        Args:
            from_ (datetime): The start date and time for the simulation.
            to (datetime): The end date and time for the simulation.
            tz (str): The timezone for the simulation. Default is "US/Eastern".
        """

        self.tz = pytz.timezone(tz)
        self.symbols = {}
        self._async_client = AsyncAMQPClient()
        self._async_client.set_logger_name("SimulatedTicker")
        self.from_ = from_
        self.to = to

        # localize the start and end dates if they are naive
        if self.from_.tzinfo is None:
            self.from_ = self.tz.localize(self.from_)
        else:
            # if the from_ date is not naive, convert it to the specified timezone
            if self.from_.tzinfo != self.tz:
                self.from_ = self.from_.astimezone(self.tz)

        if self.to.tzinfo is None:
            self.to = self.tz.localize(self.to)
        else:
            if self.to.tzinfo != self.tz:
                self.to = self.to.astimezone(self.tz)

    async def start(self) -> None:
        """
        Starts the simulated ticker service.
        """
        try:
            self.logger.info("Simulated ticker started.")
            await self._async_client.connect()

            await asyncio.Event().wait()  # blocks forever

        finally:
            await self.stop()

    async def stop(self):
        """
        Stops the simulated ticker service and closes RabbitMQ resources.
        """
        await self._async_client.close()
        self.logger.info("Simulated ticker stopped.")

    def _get_historical_data(self, symbol: str) -> pd.DataFrame:
        """
        Fetches historical data for the given symbol.
        """
        hdm = YfDataManager(tz=str(self.tz))
        df = hdm.get_ohlcv_1min(
            symbol,
            start_date=self.from_.date(),
            end_date=self.to.date(),
        )
        return df

    def _generate_price_stream(self, symbol: str) -> pd.DataFrame:
        """
        Generates a price stream from historical data for the given symbol.
        """
        df = self._get_historical_data(symbol)
        prices = generate_price_stream(df)
        return prices

    def get_price_generator(self, symbol: str, timestamp: float):
        """
        Returns a generator that yields price data for the given symbol.
        the price data will be generated after the given timestamp.
        Args:
            symbol (str): The stock symbol to fetch price data for.
            timestamp (float): The timestamp after which to start generating price data.
        """
        prices = self._generate_price_stream(symbol)

        # Filter the prices to only include those after the given timestamp
        prices = prices[prices.index > timestamp]
        if prices.empty:
            raise ValueError(f"No price data available for {symbol} after {timestamp}")

        for index, row in prices.iterrows():
            yield (index, row["price"])

    async def subscribe(self, symbol: str) -> None:
        """
        Subscribes to a new ticker symbol.
        """
        if symbol not in self.symbols:
            self.symbols[symbol] = {
                "next_timestamp": None,
                "next_price": None,
                "generator": None,
            }
            self.logger.info("Subscribed to %s", symbol)

    async def unsubscribe(self, symbol: str) -> None:
        """
        Unsubscribes from a symbol.
        """
        if symbol in self.symbols:
            del self.symbols[symbol]
            self.logger.info("Unsubscribed from %s", symbol)
        else:
            self.logger.warning("Symbol %s not found in subscribed symbols.", symbol)

    async def tick(self, timestamp: float) -> None:
        """
        Generates a tick event for the given timestamp.
        """
        for symbol, data in self.symbols.items():
            generator = data.get("generator")

            # if the generator is not initialized, before first tick
            if generator is None:
                generator = self.get_price_generator(symbol, timestamp)
                ts, price = next(generator)
                data["generator"] = generator
                data["next_price"] = price
                data["next_timestamp"] = ts
                continue

            next_timestamp = data.get("next_timestamp")
            if timestamp > next_timestamp:
                # if the current timestamp is greater than the next timestamp
                # create a tick event
                ts = next_timestamp
                price = data["next_price"]
                tick_evt = TickEvent(
                    event_time=datetime.fromtimestamp(ts, tz=self.tz),
                    symbol=symbol,
                    price=round(price, 3),  # round to 3 decimal places
                )
                self.logger.info(tick_evt)

                # publish the tick event to the RabbitMQ channel
                self._async_client.emit_event(tick_evt)

                # Get the next price and timestamp
                try:
                    data["next_timestamp"], data["next_price"] = next(generator)
                except StopIteration as e:
                    # if the generator is exhausted, remove the symbol from the list
                    self.logger.info("Simulation for %s finished", symbol)
                    raise e

    @override
    async def on_event(self, event: Event) -> None:
        await super().on_event(event)
        if isinstance(event, TimeStepEvent):
            asyncio.create_task(self.tick(event.timestamp))
