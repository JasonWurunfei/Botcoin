"""This module contains the data classes related to orders in the botcoin framework."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from asyncio import Queue

import pytz

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
