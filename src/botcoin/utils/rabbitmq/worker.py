"""
This module manages a RabbitMQ async worker process for the botcoin framework.
"""

import json
import asyncio
from typing import Callable, Coroutine, Any, Type

import aio_pika

from botcoin.utils.log import logging
from botcoin.data.dataclasses.events import Event


class AsyncEventWorker:
    """
    This class is an adapter for the RabbitMQ async worker process.

    """

    logger = logging.getLogger(__qualname__)

    def __init__(
        self,
        worker_queue: asyncio.Queue,
        rabbitmq_user: str,
        rabbitmq_pass: str,
        rabbitmq_host: str,
        rabbitmq_qname: str,
        rabbitmq_exchange: str,
        rabbitmq_port: int = 5672,
    ) -> None:
        self.rabbitmq_user = rabbitmq_user
        self.rabbitmq_pass = rabbitmq_pass
        self.rabbitmq_host = rabbitmq_host
        self.rabbitmq_port = rabbitmq_port
        self.rabbitmq_qname = rabbitmq_qname
        self.rabbitmq_exchange = rabbitmq_exchange
        self.coroutines = []
        self.tasks = []
        self.events = {}
        self.worker_queue = worker_queue or asyncio.Queue()
        self.status = "stopped"
        self._connection = None
        self._channel = None
        self._daemon_task = None

    def add_coroutine(
        self,
        coro: Callable[..., Coroutine[Any, Any, Any]],
        *args,
    ) -> None:
        """
        Register a task to be run in the worker process.

        Args:
            coro: The coroutine function to be run in the worker process.
            event_queue: The message queue to be used for the async task to receive events.
        """

        # Get class name and method name
        class_name = (
            coro.__self__.__class__.__name__ if hasattr(coro, "__self__") else None
        )
        method_name = coro.__name__

        async def wrapper():
            try:
                res = await coro(*args)
                self.logger.info(
                    "Coroutine %s.%s completed with result: %s",
                    class_name,
                    method_name,
                    res,
                )
                return res
            except asyncio.CancelledError:

                if class_name:
                    self.logger.info(
                        "Coroutine %s.%s was cancelled.", class_name, method_name
                    )
                else:
                    self.logger.info("Coroutine %s was cancelled.", method_name)
            except Exception as e:
                self.logger.error("Error in coroutine: %s", e)
                raise

        self.coroutines.append(wrapper)

    async def _start_coroutines(self) -> None:
        """
        Start all coroutines in the worker.
        """
        if self.status == "running":
            self.logger.warning("Worker is already running.")
            return

        self.tasks = []
        for coro in self.coroutines:
            self.tasks.append(asyncio.create_task(coro()))
        self.status = "running"

    async def _stop_coroutines(self) -> None:
        """
        Stop all coroutines in the worker.
        """
        if self.status == "stopped":
            self.logger.warning("Worker is already stopped.")
            return

        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete or cancel
        results = await asyncio.gather(*self.tasks, return_exceptions=True)

        for result in results:
            # Check if the result is an exception
            if isinstance(result, Exception):
                self.logger.error("Task failed with exception: %s", result)
            elif isinstance(result, asyncio.CancelledError):
                self.logger.info("Task was cancelled.")
            else:
                self.logger.info("Task completed with result: %s", result)
        self.status = "stopped"

    def subscribe_event(self, event_class: Type[Event]) -> None:
        """
        Subscribe a event to monitor in the worker process.

        Args:
            event_class: The event class to be registered.
        """
        if event_class.event_type not in self.events:
            self.events[event_class.event_type] = event_class
            self.logger.info("Event registered: %s", event_class.event_type)

    def remove_event(self, event_type: str) -> None:
        """
        Remove an event from the worker process.

        Args:
            event_type: The type of the event to be removed.
        """
        if event_type in self.events:
            del self.events[event_type]
            self.logger.info("Event removed: %s", event_type)
        else:
            self.logger.warning("Event not found: %s", event_type)

    async def _daemonize(self) -> None:
        """
        This function is run in the worker process.
        It listens for events from a fanout exchange in RabbitMQ and broadcasts
        them to the worker process.
        """

        # Connect to RabbitMQ server
        self._connection = await aio_pika.connect_robust(
            host=self.rabbitmq_host,
            port=self.rabbitmq_port,
            login=self.rabbitmq_user,
            password=self.rabbitmq_pass,
        )
        self.logger.info(
            "Connected to RabbitMQ server at %s:%d",
            self.rabbitmq_host,
            self.rabbitmq_port,
        )

        # Create a channel and declare the exchange and queue
        self._channel = await self._connection.channel()

        exchange = await self._channel.declare_exchange(
            self.rabbitmq_exchange, aio_pika.ExchangeType.FANOUT, durable=True
        )

        queue = await self._channel.declare_queue(self.rabbitmq_qname, durable=True)
        await queue.bind(exchange)

        # Listen for messages in the queue
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    body = json.loads(message.body)
                    event_type = body.get("event_type")

                    # Check if the event type is None or empty
                    if event_type is None:
                        self.logger.warning("No event type found in message body")
                        continue

                    # Check if the event type is StartEvent or StopEvent
                    if event_type == "start":
                        self.logger.info("Received start event")
                        await self._start_coroutines()
                    elif event_type == "stop":
                        self.logger.info("Received stop event")
                        await self._stop_coroutines()

                    # Check if the event type is registered
                    elif event_type in self.events:
                        event = self.events[event_type].from_json(body)
                        self.logger.info("Received event: %s", event)
                        await self.worker_queue.put(event)
                    else:
                        self.logger.warning("Unknown event type: %s", event_type)

    async def start(self) -> None:
        """
        The entry point for the worker async loop.
        """
        self.logger.info("Starting worker...")
        self._daemon_task = asyncio.create_task(self._daemonize())
        await self._start_coroutines()

    async def stop(self) -> None:
        """
        Gracefully stop all coroutines and RabbitMQ connection.
        """
        self.logger.info("Stopping worker...")

        # Stop coroutines
        await self._stop_coroutines()

        # Cancel daemon task if running
        if self._daemon_task:
            self._daemon_task.cancel()
            try:
                await self._daemon_task
            except asyncio.CancelledError:
                self.logger.info("Daemon task cancelled.")

        # Close RabbitMQ channel and connection
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
            self.logger.info("RabbitMQ channel closed.")

        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            self.logger.info("RabbitMQ connection closed.")

        self.logger.info("Worker stopped cleanly.")
