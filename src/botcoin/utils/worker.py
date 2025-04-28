"""
This module manages a RabbitMQ worker process for the botcoin framework.
"""

import os
import json
import asyncio
from typing import Callable

from dotenv import load_dotenv
import aio_pika


load_dotenv()
RABBITMQ_USER: str = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD")
RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST")
RABBITMQ_URL: str = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}/"


class RabbitMQAdapterWorker:
    """
    This class is a adapter for the RabbitMQ worker process.
    It manages the worker process and allows for tasks to be added to it.
    """

    def __init__(self) -> None:
        self.rabbitmq_url = RABBITMQ_URL
        self.callables = []
        self.tasks = []

    def add_task(self, task: Callable) -> None:
        """
        Register a task to be run in the worker process.

        Args:
            task (Callable): The coroutine function to be run in the worker process.
        """
        self.callables.append(task)

    async def start(self) -> None:
        """
        The entry point for the worker async loop.
        This function is run in the worker process.
        It sets up the asyncio event loop and starts the worker function.
        """
        tasks = self._worker_tasks()
        await asyncio.gather(*tasks, return_exceptions=True)

    def _worker_tasks(self) -> asyncio.Future:
        """
        This function gathers all tasks to be run in the worker process.

        Returns:
            asyncio.Future: A future representing the completion of the tasks.
        """
        listener_task = asyncio.create_task(self.command_listener())
        for callable_ in self.callables:
            self.tasks.append(asyncio.create_task(callable_()))
        return self.tasks + [listener_task]

    async def command_listener(self) -> None:
        """
        Listen for commands from the parent process.

        This function runs in the worker process and listens for commands sent through the pipe.
        When a command is received, it checks if it's a stop command and stops the worker.

        Args:
            conn (Pipe): The pipe connection to the parent process.
        """
        connection = None
        channel = None
        queue = None

        while True:
            if connection is None or connection.is_closed:
                connection = await aio_pika.connect_robust(RABBITMQ_URL)
                channel = await connection.channel()
                queue = await channel.declare_queue("botcoin", durable=True)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        body = json.loads(message.body)
                        if body.get("command") == "start":
                            print("Starting tasks...")
                            await self.start_tasks()
                        elif body.get("command") == "stop":
                            print("Stopping tasks...")
                            await self.stop_tasks()
                        else:
                            print(f"Unknown command: {body.get('command')}")

    async def stop_tasks(self) -> None:
        """
        Stop all tasks running in the worker process.
        This function is called when a stop command is received from the queue.
        """
        for task in self.tasks:
            task.cancel()

        # Wait for all tasks to complete or cancel
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def start_tasks(self) -> None:
        """
        Start all tasks running in the worker process.
        This function is called when a start command is received from the queue.
        """
        self.tasks = []
        for callable_ in self.callables:
            self.tasks.append(asyncio.create_task(callable_()))
