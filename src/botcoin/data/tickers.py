"""This module contains diferent types of price tickers."""

import os
import json
import asyncio
from datetime import datetime

import pytz
import websockets
from dotenv import load_dotenv

from botcoin.utils.log import logging
from botcoin.data.dataclasses import TickEvent
from botcoin.utils.message_queue import BroadcastQueue

# Load variables from .env file into environment
load_dotenv()


class FinnhubTicker:
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
        self.ws = None

    async def connect(self):
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
        Subscribes to the given tickers.
        """
        for ticker in self.tickers:
            await ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))
            self.logger.info("Subscribed to %s", ticker)

    async def subscribe(self, symbol: str):
        """
        Subscribes to a new ticker symbol.
        """
        try:
            if not self.ws:
                raise ValueError("WebSocket connection is not established.")
            if symbol not in self.tickers:
                self.tickers.append(symbol)
                await self.ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
                self.logger.info("Subscribed to %s", symbol)
        except ValueError as e:
            self.logger.error("WebSocket connection error: %s", e)
            return

    async def unsubscribe(self, symbol: str):
        """
        Unsubscribes from a ticker symbol.
        """
        try:
            if not self.ws:
                raise ValueError("WebSocket connection is not established.")

            if symbol in self.tickers:
                self.tickers.remove(symbol)
                await self.ws.send(
                    json.dumps({"type": "unsubscribe", "symbol": symbol})
                )
                self.logger.info("Unsubscribed from %s", symbol)
            else:
                self.logger.warning(
                    "Symbol %s not found in subscribed tickers.", symbol
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
