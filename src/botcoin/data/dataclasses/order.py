"""This module contains the data classes related to orders in the botcoin framework."""

import uuid
from abc import ABC
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
from typing import Union

import pytz

from botcoin.data.dataclasses import JSONSerializable

US_EAST = pytz.timezone("US/Eastern")


def now_us_east():
    """Shortcut to get the current time in US/Eastern timezone."""
    return datetime.now(US_EAST)


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
class Order(JSONSerializable, ABC):
    """
    Represents an order in the botcoin framework.
    This class contains the details of an order including its ID, symbol,
    quantity, direction, and type.
    """

    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    quantity: int
    direction: str  # 'buy' or 'sell'
    timestamp: datetime = field(default_factory=now_us_east)

    def __post_init__(self):
        if self.direction not in ["buy", "sell"]:
            raise ValueError(f"Invalid direction: {self.direction}")
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be greater than zero: {self.quantity}")

    def __repr__(self):
        return self.to_string()

    def __str__(self):
        return self.to_string()

    def to_string(self):
        """
        Convert the event to a string representation.
        """

        child_entities = self.serialize()
        child_entities_str = ""

        for k, v in child_entities.items():
            if k == "timestamp":
                continue
            if isinstance(v, Enum):
                child_entities_str += f"{k}={v.value}, "
                continue
            child_entities_str += f"{k}={v}, "

        return (
            f"{self.__class__.__name__}({child_entities_str}"
            + f"timestamp={self.timestamp.isoformat()})"
        )


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class MarketOrder(Order):
    """
    Represents a market order.
    This order is executed at the current market price.
    """

    order_type: OrderType = OrderType.MARKET


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
            raise ValueError(f"Limit price must be greater than zero: {self.limit_price}")


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
            raise ValueError(f"Limit price must be greater than zero: {self.limit_price}")
        if self.stop_price <= 0:
            raise ValueError(f"Stop price must be greater than zero: {self.stop_price}")


def deserialize_order(order_data: dict) -> Union[MarketOrder, LimitOrder, OcoOrder]:
    """
    Deserialize order data to an order object.
    """
    order_type = order_data.get("order_type")
    if order_type == "market":
        return MarketOrder.from_dict(order_data)
    if order_type == "limit":
        return LimitOrder.from_dict(order_data)
    if order_type == "oco":
        return OcoOrder.from_dict(order_data)

    raise ValueError(f"Invalid order type: {order_type}")


@dataclass(kw_only=True, slots=True, order=True)
class OrderBookItem:
    """
    Represents an order book item.
    """

    order_id: str
    order: Order
    status: OrderStatus = OrderStatus.NOT_TRADED

    def __repr__(self):
        return (
            f"OrderBookItem(order_id={self.order_id}, order={self.order.order_id}, "
            + f"status={self.status.value})"
        )
