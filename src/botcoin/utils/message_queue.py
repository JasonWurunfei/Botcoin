"""This module contains the utility classes and methods used in the botcoin framework."""

from asyncio import Queue


class BroadcastQueue:
    """This class manages multiple consumer queues for broadcasting messages."""

    def __init__(self):
        self.queues: list[Queue] = []

    def register(self, q: Queue) -> None:
        """
        Registers a new consumer queue.
        """
        self.queues.append(q)

    async def publish(self, item):
        """
        Publishes a message to all registered consumers.
        """
        for q in self.queues:
            await q.put(item)
