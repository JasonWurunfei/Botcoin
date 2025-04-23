from asyncio import Queue


class BroadcastQueue:
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
