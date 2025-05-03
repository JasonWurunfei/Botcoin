"""
This module manages a RabbitMQ async worker process for the botcoin framework.
"""

import json
import asyncio
from typing import Callable, Coroutine, Any

import aio_pika

from botcoin.utils.log import logging
from botcoin.data.dataclasses import Event
from botcoin.utils.message_queue import BroadcastQueue


class AsyncEventWorker:
    """
    This class is an adapter for the RabbitMQ async worker process.

    """

    logger = logging.getLogger(__qualname__)

    def __init__(
        self,
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
        self.broadcast_queue = BroadcastQueue()
        self.status = "stopped"

    def add_coroutine(
        self,
        coro: Callable[..., Coroutine[Any, Any, Any]],
        event_queue: asyncio.Queue,
        *args,
    ) -> None:
        """
        Register a task to be run in the worker process.

        Args:
            coro: The coroutine function to be run in the worker process.
            event_queue: The message queue to be used for the async task to receive events.
        """

        async def wrapper():
            try:
                self.broadcast_queue.register(event_queue)
                return await coro(*args)
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

    def add_event(self, event_type: str, event_factory: Callable[..., Event]) -> None:
        """
        Register a event to monitor in the worker process.

        Args:
            event_type: The type of the event to be registered.
            event_factory: The factory function to create the event.
        """
        if event_type not in self.events:
            self.events[event_type] = event_factory
            self.logger.info("Event registered: %s", event_type)

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
        It listens for events from a fanout exchange in RabbitMQ and broadcasts them to the worker process.
        """

        # Connect to RabbitMQ server
        connection = await aio_pika.connect_robust(
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
        channel = await connection.channel()

        exchange = await channel.declare_exchange(
            self.rabbitmq_exchange, aio_pika.ExchangeType.FANOUT, durable=True
        )

        queue = await channel.declare_queue(self.rabbitmq_qname, durable=True)
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
                        await self.broadcast_queue.publish(event)
                    else:
                        self.logger.warning("Unknown event type: %s", event_type)

    async def start(self) -> None:
        """
        The entry point for the worker async loop.
        """
        self.logger.info("Starting worker...")
        await asyncio.gather(self._start_coroutines(), self._daemonize())
