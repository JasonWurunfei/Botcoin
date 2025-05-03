"""This module contains the event data classes used in the botcoin framework."""

from typing import Union, ClassVar
from asyncio import Queue
from datetime import datetime
from dataclasses import dataclass, field

import pytz

from botcoin.data.dataclasses.order import (
    MarketOrder,
    LimitOrder,
    OcoOrder,
    Order,
    OrderStatus,
)

US_EAST = pytz.timezone("US/Eastern")


def now_us_east():
    """Shortcut to get the current time in US/Eastern timezone."""
    return datetime.now(US_EAST)


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Event:
    """
    Base class for all events in the botcoin framework.
    """

    event_type: ClassVar[str]
    event_time: datetime = field(default_factory=now_us_east)

    def __repr__(self):
        return (
            f"Event(event_type={self.event_type}, "
            + f"event_time={self.event_time.isoformat()})"
        )

    def to_json(self):
        """
        Convert the event to a JSON serializable format.
        """
        raise NotImplementedError("Subclasses must implement to_json method")

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to an event object.
        """
        raise NotImplementedError("Subclasses must implement from_json method")


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class TickEvent(Event):
    """
    Represents a market tick event.
    This event is triggered when a new market tick is received.
    """

    event_type: ClassVar[str] = "tick"
    symbol: str
    price: float

    def __repr__(self):
        return (
            f"TickEvent(symbol={self.symbol}, price={self.price}, "
            + f"event_time={self.event_time.isoformat()})"
        )

    def to_json(self):
        """
        Convert the tick event to a JSON serializable format.
        """
        return {
            "event_type": self.event_type,
            "symbol": self.symbol,
            "price": self.price,
            "event_time": self.event_time.isoformat(),
        }

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to a tick event object.
        """
        if json_data.get("event_type") != "tick":
            raise ValueError("Invalid event type for TickEvent")

        return cls(
            symbol=json_data.get("symbol"),
            price=json_data.get("price"),
            event_time=datetime.fromisoformat(json_data.get("event_time")),
        )


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class RequestTickEvent(Event):
    """
    Represents a request for a market ticker in the botcoin framework
    to start emitting tick events.
    """

    event_type: ClassVar[str] = "request_tick"
    symbol: str

    def __repr__(self):
        return f"RequestTickEvent(symbol={self.symbol})"

    def to_json(self):
        """
        Convert the request tick event to a JSON serializable format.
        """
        return {
            "event_type": self.event_type,
            "symbol": self.symbol,
        }

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to a request tick event object.
        """
        if json_data.get("event_type") != "request_tick":
            raise ValueError("Invalid event type for RequestTickEvent")

        return cls(symbol=json_data.get("symbol"))


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class StartEvent(Event):
    """
    Represents the start event for async event workers
    """

    event_type: ClassVar[str] = "start"

    def __repr__(self):
        return f"StartEvent(event_time={self.event_time.isoformat()})"

    def to_json(self):
        """
        Convert the event to a JSON serializable format.
        """
        return {
            "event_type": self.event_type,
            "event_time": self.event_time.isoformat(),
        }

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to an event object.
        """
        if json_data.get("event_type") != "start":
            raise ValueError("Invalid event type for StartEvent")

        return cls(event_time=datetime.fromisoformat(json_data.get("event_time")))


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class StopEvent(Event):
    """
    Represents the stop event for async event workers
    """

    event_type: ClassVar[str] = "stop"

    def __repr__(self):
        return f"StopEvent(event_time={self.event_time.isoformat()})"

    def to_json(self):
        """
        Convert the event to a JSON serializable format.
        """
        return {
            "event_type": self.event_type,
            "event_time": self.event_time.isoformat(),
        }

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to an event object.
        """
        if json_data.get("event_type") != "stop":
            raise ValueError("Invalid event type for StopEvent")

        return cls(event_time=datetime.fromisoformat(json_data.get("event_time")))


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class PlaceOrderEvent(Event):
    """
    Represents an event to place an order.
    This event is used to send an order to the broker for execution.
    """

    event_type: ClassVar[str] = "place_order"
    order: Union[MarketOrder, LimitOrder, OcoOrder]
    reply_to: Queue

    def __repr__(self):
        return f"PlaceOrderEvent(order={self.order})"

    def to_json(self):
        """
        Convert the event to a JSON serializable format.
        """
        return {
            "event_type": self.event_type,
            "order": self.order.to_json(),
            "reply_to": self.reply_to,
        }

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to a place order event object.
        """
        if json_data.get("event_type") != "place_order":
            raise ValueError("Invalid event type for PlaceOrderEvent")

        return cls(
            order=Order.from_json(json_data["order"]),
            reply_to=json_data["reply_to"],
        )


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class OrderStatusEvent(Event):
    """
    Represents an event that contains the status of an order.
    This event is used to notify the system about the status of an order.
    """

    event_type: ClassVar[str] = "order_status"
    order: Order
    status: OrderStatus

    def __repr__(self):
        return f"OrderStatusEvent(order={self.order}, status={self.status.value})"

    def to_json(self):
        """
        Convert the event to a JSON serializable format.
        """
        return {
            "event_type": self.event_type,
            "order": self.order.to_json(),
            "status": self.status.value,
        }

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to an order status event object.
        """
        if json_data.get("event_type") != "order_status":
            raise ValueError("Invalid event type for OrderStatusEvent")

        return cls(
            order=Order.from_json(json_data["order"]),
            status=OrderStatus(json_data["status"]),
        )
