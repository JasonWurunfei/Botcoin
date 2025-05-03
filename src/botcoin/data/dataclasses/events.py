"""This module contains the data classes used in the botcoin framework."""

from typing import Union
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

    event_type: str
    event_time: datetime = field(default_factory=now_us_east)

    def __repr__(self):
        return f"Event(event_type={self.event_type}, event_time={self.event_time.isoformat()})"


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class TickEvent(Event):
    """
    Represents a market tick event.
    This event is triggered when a new market tick is received.
    """

    event_type: str = "tick"
    symbol: str
    price: float

    def __repr__(self):
        return (
            f"TickEvent(symbol={self.symbol}, price={self.price}, "
            + f"event_time={self.event_time.isoformat()})"
        )


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class StartEvent(Event):
    """
    Represents the start event for async event workers
    """

    event_type: str = "start"

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
        event_type = json_data.get("event_type")
        event_time = datetime.fromisoformat(json_data.get("event_time"))
        return StartEvent(event_type=event_type, event_time=event_time)


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class StopEvent(Event):
    """
    Represents the stop event for async event workers
    """

    event_type: str = "stop"

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
        event_type = json_data.get("event_type")
        event_time = datetime.fromisoformat(json_data.get("event_time"))
        return StopEvent(event_type=event_type, event_time=event_time)


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class PlaceOrderEvent(Event):
    """
    Represents an event to place an order.
    This event is used to send an order to the broker for execution.
    """

    event_type: str = "place_order"
    order: Union[MarketOrder, LimitOrder, OcoOrder]
    reply_to: Queue

    def __repr__(self):
        return f"PlaceOrderEvent(order={self.order})"


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class OrderStatusEvent(Event):
    """
    Represents an event that contains the status of an order.
    This event is used to notify the system about the status of an order.
    """

    event_type: str = "order_status"
    order: Order
    status: OrderStatus

    def __repr__(self):
        return f"OrderStatusEvent(order={self.order}, status={self.status.value})"
