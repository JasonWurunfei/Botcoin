"""This module defines event related classes and interfaces passed to the RabbitMQ."""

from typing import Type
from abc import ABC, abstractmethod

from botcoin.data.dataclasses.events import Event


class EventReceiver(ABC):
    """
    Abstract base class for event receivers.
    """

    subscribedEvents: set[Type[Event]] = set()

    @abstractmethod
    async def on_event(self, event: Event) -> None:
        """
        Abstract method to handle incoming events.

        Args:
            event (Event): The event to be handled.
        """
