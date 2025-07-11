"""
This module manages a RabbitMQ async worker process for the botcoin framework.
"""

import asyncio
import json
import signal
import traceback
from typing import Callable, Coroutine, Any, Type

import aio_pika

from botcoin.services import Service
from botcoin.utils.log import logging
from botcoin.utils.rabbitmq.conn import new_connection, RABBITMQ_EXCHANGE
from botcoin.data.dataclasses.events import Event
from botcoin.utils.rabbitmq.event import EventReceiver


class AsyncEventWorker:
    """
    This class is an adapter for the RabbitMQ async worker process.

    """

    logger = logging.getLogger(__qualname__)

    def __init__(self, qname: str) -> None:
        self.coroutines = []
        self.tasks = []
        self.events = {}
        self.worker_queue = asyncio.Queue()
        self.status = "stopped"
        self._connection = None
        self._channel = None
        self._daemon_task = None
        self.qname = qname
        self.event_receiver: list[EventReceiver] = []
        self.services = []

    def get_queue(self) -> asyncio.Queue:
        """
        Get the worker queue.

        Returns:
            asyncio.Queue: The worker queue.
        """
        return self.worker_queue

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
                self.logger.error("Stack trace:\n%s", traceback.format_exc())
                raise

        self.coroutines.append(wrapper)

    def add_service(self, service: Service) -> None:
        """
        Register a service to the worker process.

        Args:
            service: The service to be registered.
        """
        if not isinstance(service, Service):
            raise TypeError("Service must be an instance of Service")

        if service not in self.services:
            self.services.append(service)
            self.logger.info("Service registered: %s", service.__class__.__name__)
            self.add_coroutine(service.start)

    def add_event_receiver(self, receiver: EventReceiver) -> None:
        """
        Register an event receiver to the worker process.

        Args:
            receiver: The event receiver to be registered.
        """
        if not isinstance(receiver, EventReceiver):
            raise TypeError("Receiver must be an instance of EventReceiver")

        if receiver not in self.event_receiver:
            self.event_receiver.append(receiver)
            self.logger.info(
                "Event receiver registered: %s", receiver.__class__.__name__
            )

    def _regitser_events(self) -> None:
        """
        Register all events from the event receivers to the worker process.
        """
        events = set()
        for receiver in self.event_receiver:
            for event in receiver.subscribedEvents:
                if event not in events:
                    self.subscribe_event(event)
                    events.add(event)

    def notify_event_receivers(self, event: Event) -> None:
        """
        Notify all registered event receivers about an event.

        Args:
            event: The event to be notified.
        """
        for receiver in self.event_receiver:
            asyncio.create_task(receiver.on_event(event))

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
        if event_class.cls_event_type not in self.events:
            self.events[event_class.cls_event_type] = event_class
            self.logger.info("Event registered: %s", event_class.cls_event_type)

    def subscribe_events(self, events: list[Type[Event]]) -> None:
        """
        Subscribe multiple events to monitor in the worker process.

        Args:
            events: A list of event classes to be registered.
        """
        for event in events:
            self.subscribe_event(event)

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
        self._connection = await new_connection()

        # Create a channel and declare the exchange and queue
        self._channel = await self._connection.channel()

        exchange = await self._channel.declare_exchange(
            RABBITMQ_EXCHANGE, aio_pika.ExchangeType.FANOUT, durable=True
        )

        queue = await self._channel.declare_queue(self.qname, durable=True)
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
                        event = self.events[event_type].from_dict(body)
                        await self.worker_queue.put(event)
                    else:
                        self.logger.warning("Unknown event type: %s", event_type)

    async def start(self) -> None:
        """
        The entry point for the worker async loop.
        """
        self.logger.info("Starting worker...")

        async def daemon_wrapper():
            """Daemon wrapper to print out exceptions."""
            try:
                await self._daemonize()
            except Exception as e:
                self.logger.error("Error in daemon: %s", e)
                self.logger.error("Stack trace:\n%s", traceback.format_exc())
                # Restart the daemon to continue listening for events
                self._daemon_task = asyncio.create_task(daemon_wrapper())
                raise e

        self._daemon_task = asyncio.create_task(daemon_wrapper())
        await self._start_coroutines()

    async def stop(self) -> None:
        """
        Gracefully stop all coroutines and RabbitMQ connection.
        """
        self.logger.info("Stopping worker...")

        # Stop coroutines
        await self._stop_coroutines()

        # Stop all registered services
        for service in self.services:
            await service.stop()

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


async def run_worker(worker: AsyncEventWorker) -> None:
    """
    Run the worker in an asyncio event loop.
    """
    stop_event = asyncio.Event()

    def shutdown():
        """
        Shutdown handler to stop the worker gracefully.
        """
        stop_event.set()

    # Register shutdown signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    # Start the worker
    worker_queue = worker.get_queue()
    worker_task = asyncio.create_task(worker.start())

    try:
        # Main event loop
        while not stop_event.is_set():
            try:
                event = await asyncio.wait_for(worker_queue.get(), timeout=1.0)
                worker.notify_event_receivers(event)
            except asyncio.TimeoutError:
                continue  # Check for stop_event periodically
    finally:
        # Cleanup
        await worker.stop()
        if worker_task:
            await worker_task
