"""This module contains the event data classes used in the botcoin framework."""

from abc import ABC
from datetime import datetime
from typing import Optional, ClassVar, override
from dataclasses import dataclass, field

import pytz

from botcoin.data.dataclasses.order import (
    Order,
    OrderStatus,
    deserialize_order,
)

from botcoin.data.dataclasses import JSONSerializable

US_EAST = pytz.timezone("US/Eastern")


def now_us_east():
    """Shortcut to get the current time in US/Eastern timezone."""
    return datetime.now(US_EAST)


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Event(JSONSerializable, ABC):
    """
    Represents a new event in the botcoin framework.
    This event is used to notify the system about a new event.
    """

    cls_event_type: ClassVar[str] = "new_event"
    event_type: Optional[str] = field(default=None)
    event_time: datetime = field(default_factory=now_us_east)

    def __post_init__(self):
        if self.event_type is None:
            object.__setattr__(self, "event_type", self.cls_event_type)

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
            if k == "event_time":
                continue
            if k == "event_type":
                continue
            child_entities_str += f"{k}={v}, "

        return (
            f"{self.__class__.__name__}({child_entities_str}"
            + f"event_time={self.event_time.isoformat()})"
        )

    @classmethod
    def _validate(cls, dict_data: dict) -> None:
        """
        Validate the event type in the object data.
        """
        obj_type = dict_data.get("event_type")
        if obj_type is None:
            raise ValueError("Missing 'event_type' in the object data")
        if cls.cls_event_type != obj_type:
            raise ValueError(f"Invalid event type: {obj_type}. Expected: {cls.cls_event_type}")
        if "event_time" not in dict_data:
            raise ValueError("Missing 'event_time' in the object data")

    @override
    @classmethod
    def from_dict(cls, dict_data: dict) -> "Event":
        """
        Convert dictionary data to a new event object.
        """
        cls._validate(dict_data)
        return super(Event, cls).from_dict(dict_data)


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class TickEvent(Event):
    """
    Represents a market tick event.
    This event is triggered when a new market tick is received.
    """

    cls_event_type: ClassVar[str] = "tick"

    symbol: str
    price: float


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class RequestTickEvent(Event):
    """
    Represents a request for a market ticker in the botcoin framework
    to start emitting tick events.
    """

    cls_event_type: ClassVar[str] = "request_tick"
    symbol: str


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class RequestStopTickEvent(Event):
    """
    Represents a request for a market ticker in the botcoin framework
    to stop emitting tick events.
    """

    cls_event_type: ClassVar[str] = "request_stop_tick"
    symbol: str


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class StartEvent(Event):
    """
    Represents the start event for async event workers
    """

    cls_event_type: ClassVar[str] = "start"


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class StopEvent(Event):
    """
    Represents the stop event for async event workers
    """

    cls_event_type: ClassVar[str] = "stop"


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class OrderEvent(Event, ABC):
    """
    Represents an event related to an order.
    This event is used to notify the system about an order-related event.
    """

    order: Order

    @override
    @classmethod
    def _validate(cls, dict_data: dict) -> None:
        """
        Validate the event type in the object data.
        """
        super(OrderEvent, cls)._validate(dict_data)
        if "order" not in dict_data:
            raise ValueError("Missing 'order' in the object data")
        order = dict_data.get("order")
        if not isinstance(order, dict):
            raise ValueError("'order' must be a dictionary")

    @override
    @classmethod
    def from_dict(cls, dict_data: dict) -> "OrderEvent":
        """
        Convert dictionary data to an order event object.
        """
        cls._validate(dict_data)
        event = super(OrderEvent, cls).from_dict(dict_data)
        order = deserialize_order(dict_data.get("order"))
        object.__setattr__(event, "order", order)
        return event


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class PlaceOrderEvent(OrderEvent):
    """
    Represents an event to place an order.
    This event is used to send an order to the broker for execution.
    """

    cls_event_type: ClassVar[str] = "place_order"


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class CancelOrderEvent(OrderEvent):
    """
    Represents an event to cancel an order.
    This event is used to send a cancellation request to the broker.
    """

    cls_event_type: ClassVar[str] = "cancel_order"


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class ModifyOrderEvent(OrderEvent):
    """
    Represents an event to modify an order.
    This event is used to send a modification request to the broker.
    """

    cls_event_type: ClassVar[str] = "modify_order"


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class OrderModifiedEvent(OrderEvent):
    """
    Represents an event that contains the modified order details.
    This event is used to notify the system about the modified order.
    """

    cls_event_type: ClassVar[str] = "order_modified"


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class OrderStatusEvent(Event):
    """
    Represents an event that contains the status of an order.
    This event is used to notify the system about the status of an order.
    """

    cls_event_type: ClassVar[str] = "order_status"
    order: Order
    status: OrderStatus

    @override
    @classmethod
    def _validate(cls, dict_data: dict) -> None:
        """
        Validate the event type in the object data.
        """
        super(OrderStatusEvent, cls)._validate(dict_data)
        if "order" not in dict_data:
            raise ValueError("Missing 'order' in the object data")
        order = dict_data.get("order")
        if not isinstance(order, dict):
            raise ValueError("'order' must be a dictionary")
        if "status" not in dict_data:
            raise ValueError("Missing 'status' in the object data")

    @override
    @classmethod
    def from_dict(cls, dict_data: dict) -> "OrderStatusEvent":
        """
        Convert dictionary data to an order status event object.
        """
        cls._validate(dict_data)
        event = super(OrderStatusEvent, cls).from_dict(dict_data)
        order = deserialize_order(dict_data.get("order"))
        status = OrderStatus(dict_data.get("status"))
        object.__setattr__(event, "status", status)
        object.__setattr__(event, "order", order)
        return event
