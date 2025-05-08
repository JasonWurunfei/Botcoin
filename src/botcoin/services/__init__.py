"""This module defines the services used in the botcoin application."""

from abc import ABC, abstractmethod


class Service(ABC):
    """
    Abstract base class for all services in the botcoin application.
    """

    @abstractmethod
    async def start(self) -> None:
        """
        Starts the service.
        """

    @abstractmethod
    async def stop(self) -> None:
        """
        Stops the service.
        """
