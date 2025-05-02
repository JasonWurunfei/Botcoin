"""This module contains the data classes used in the botcoin framework."""

from dataclasses import dataclass, field
from typing import Union
from datetime import datetime
from enum import Enum
from asyncio import Queue

import pytz

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


class OrderStatus(Enum):
    """
    Represents the status of an order.
    This can be used to track the state of an order in the system.
    """

    NOT_TRADED = "not_traded"
    TRADED = "traded"
    CANCELLED = "cancelled"


class OrderType(Enum):
    """
    Represents the type of an order.
    This can be used to specify the execution method of an order.
    """

    MARKET = "market"
    LIMIT = "limit"
    OCO = "oco"
    STOP = "stop"


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Order:
    """
    Represents an order in the botcoin framework.
    This class contains the details of an order including its ID, symbol,
    quantity, direction, and type.
    """

    order_id: str
    symbol: str
    quantity: int
    direction: str  # 'buy' or 'sell'
    timestamp: datetime = field(default_factory=now_us_east)

    def __post_init__(self):
        if self.direction not in ["buy", "sell"]:
            raise ValueError(f"Invalid direction: {self.direction}")
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be greater than zero: {self.quantity}")


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class MarketOrder(Order):
    """
    Represents a market order.
    This order is executed at the current market price.
    """

    order_type: OrderType = OrderType.MARKET

    def __repr__(self):
        return (
            f"MarketOrder(order_id={self.order_id}, symbol={self.symbol},"
            + f" quantity={self.quantity}, direction={self.direction})"
        )


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class LimitOrder(Order):
    """
    Represents a limit order.
    This order is executed at a specified price or better.
    """

    order_type: OrderType = OrderType.LIMIT
    limit_price: float

    def __post_init__(self):
        if self.direction not in ["buy", "sell"]:
            raise ValueError(f"Invalid direction: {self.direction}")
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be greater than zero: {self.quantity}")
        if self.limit_price <= 0:
            raise ValueError(
                f"Limit price must be greater than zero: {self.limit_price}"
            )

    def __repr__(self):
        return (
            f"LimitOrder(order_id={self.order_id}, symbol={self.symbol}, "
            + f"quantity={self.quantity}, direction={self.direction}, "
            + f"limit_price={self.limit_price})"
        )


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class OcoOrder(Order):
    """
    Represents an OCO (One Cancels Other) order.
    This order consists of two orders: a limit order and a stop order.
    If one order is executed, the other is cancelled.
    """

    order_type: OrderType = OrderType.OCO
    limit_price: float
    stop_price: float

    def __post_init__(self):
        if self.direction not in ["buy", "sell"]:
            raise ValueError(f"Invalid direction: {self.direction}")
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be greater than zero: {self.quantity}")
        if self.limit_price <= 0:
            raise ValueError(
                f"Limit price must be greater than zero: {self.limit_price}"
            )
        if self.stop_price <= 0:
            raise ValueError(f"Stop price must be greater than zero: {self.stop_price}")

    def __repr__(self):
        return (
            f"OcoOrder(order_id={self.order_id}, symbol={self.symbol}, "
            + f"quantity={self.quantity}, direction={self.direction}, "
            + f"limit_price={self.limit_price}, stop_price={self.stop_price})"
        )


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


@dataclass(kw_only=True, slots=True, order=True)
class OrderBookItem:
    """
    Represents an order book item.
    """

    order_id: str
    order: Order
    queue: Queue
    status: OrderStatus = OrderStatus.NOT_TRADED

    def __repr__(self):
        return (
            f"OrderBookItem(order_id={self.order_id}, order={self.order}, "
            + f"status={self.status.value})"
        )
