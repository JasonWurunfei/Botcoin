"""This module contains the event data classes used in the botcoin framework."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Union, ClassVar
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
class Event(ABC):
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

    @abstractmethod
    def serialize(self):
        """
        Convert the event to a JSON serializable format.
        """

    @classmethod
    @abstractmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to an event object.
        """


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

    def serialize(self):
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

    def serialize(self):
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
class RequestStopTickEvent(Event):
    """
    Represents a request for a market ticker in the botcoin framework
    to stop emitting tick events.
    """

    event_type: ClassVar[str] = "request_stop_tick"
    symbol: str

    def __repr__(self):
        return f"RequestStopTickEvent(symbol={self.symbol})"

    def serialize(self):
        """
        Convert the request stop tick event to a JSON serializable format.
        """
        return {
            "event_type": self.event_type,
            "symbol": self.symbol,
        }

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to a request stop tick event object.
        """
        if json_data.get("event_type") != "request_stop_tick":
            raise ValueError("Invalid event type for RequestStopTickEvent")

        return cls(symbol=json_data.get("symbol"))


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class StartEvent(Event):
    """
    Represents the start event for async event workers
    """

    event_type: ClassVar[str] = "start"

    def __repr__(self):
        return f"StartEvent(event_time={self.event_time.isoformat()})"

    def serialize(self):
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

    def serialize(self):
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


def deserialize_order(json_data) -> Union[MarketOrder, LimitOrder, OcoOrder]:
    """
    Deserialize JSON data to an order object.
    """
    order_type = json_data.get("order_type")
    if order_type == "market":
        return MarketOrder.from_json(json_data)
    elif order_type == "limit":
        return LimitOrder.from_json(json_data)
    elif order_type == "oco":
        return OcoOrder.from_json(json_data)
    else:
        raise ValueError(f"Invalid order type: {order_type}")


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class PlaceOrderEvent(Event):
    """
    Represents an event to place an order.
    This event is used to send an order to the broker for execution.
    """

    event_type: ClassVar[str] = "place_order"
    order: Union[MarketOrder, LimitOrder, OcoOrder]

    def __repr__(self):
        return f"PlaceOrderEvent(order={self.order})"

    def serialize(self):
        """
        Convert the event to a JSON serializable format.
        """
        return {
            "event_type": self.event_type,
            "order": self.order.serialize(),
        }

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to a place order event object.
        """
        if json_data.get("event_type") != "place_order":
            raise ValueError("Invalid event type for PlaceOrderEvent")

        order = deserialize_order(json_data.get("order"))
        return cls(order=order)


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class CancelOrderEvent(Event):
    """
    Represents an event to cancel an order.
    This event is used to send a cancellation request to the broker.
    """

    event_type: ClassVar[str] = "cancel_order"
    order: Order

    def __repr__(self):
        return f"CancelOrderEvent(order={self.order})"

    def serialize(self):
        """
        Convert the event to a JSON serializable format.
        """
        return {
            "event_type": self.event_type,
            "order": self.order.serialize(),
        }

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to a cancel order event object.
        """
        if json_data.get("event_type") != "cancel_order":
            raise ValueError("Invalid event type for CancelOrderEvent")

        order = deserialize_order(json_data.get("order"))
        return cls(order=order)


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class ModifyOrderEvent(Event):
    """
    Represents an event to modify an order.
    This event is used to send a modification request to the broker.
    """

    event_type: ClassVar[str] = "modify_order"
    modified_order: Order

    def __repr__(self):
        return f"ModifyOrderEvent(modified_order={self.modified_order})"

    def serialize(self):
        """
        Convert the event to a JSON serializable format.
        """
        return {
            "event_type": self.event_type,
            "modified_order": self.modified_order.serialize(),
        }

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to a modify order event object.
        """
        if json_data.get("event_type") != "modify_order":
            raise ValueError("Invalid event type for ModifyOrderEvent")

        modified_order = deserialize_order(json_data.get("modified_order"))
        return cls(modified_order=modified_order)


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class OrderModifiedEvent(Event):
    """
    Represents an event that contains the modified order details.
    This event is used to notify the system about the modified order.
    """

    event_type: ClassVar[str] = "order_modified"
    modified_order: Order

    def __repr__(self):
        return f"OrderModifiedEvent(modified_order={self.modified_order})"

    def serialize(self):
        """
        Convert the event to a JSON serializable format.
        """
        return {
            "event_type": self.event_type,
            "modified_order": self.modified_order.serialize(),
        }

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to an order modified event object.
        """
        if json_data.get("event_type") != "order_modified":
            raise ValueError("Invalid event type for OrderModifiedEvent")

        modified_order = deserialize_order(json_data.get("modified_order"))
        return cls(modified_order=modified_order)


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

    def serialize(self):
        """
        Convert the event to a JSON serializable format.
        """
        return {
            "event_type": self.event_type,
            "order": self.order.serialize(),
            "status": self.status.value,
        }

    @classmethod
    def from_json(cls, json_data):
        """
        Convert JSON data to an order status event object.
        """
        if json_data.get("event_type") != "order_status":
            raise ValueError("Invalid event type for OrderStatusEvent")

        order = deserialize_order(json_data["order"])

        return cls(
            order=order,
            status=OrderStatus(json_data["status"]),
        )
