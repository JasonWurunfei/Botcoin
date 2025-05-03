"""This script is used to start the Botcoin application."""

import os
import asyncio

from dotenv import load_dotenv

from botcoin.utils.rabbitmq.worker import AsyncEventWorker

from botcoin.data.tickers import FakeTicker
from botcoin.data.dataclasses.events import Event, RequestTickEvent

load_dotenv()
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "botcoin")


async def main():
    """
    Main function to start the Botcoin application.
    """

    # Initialize the worker
    worker_queue = asyncio.Queue()
    worker = AsyncEventWorker(
        worker_queue=worker_queue,
        rabbitmq_user=RABBITMQ_USER,
        rabbitmq_pass=RABBITMQ_PASS,
        rabbitmq_host=RABBITMQ_HOST,
        rabbitmq_qname="ticker",
        rabbitmq_exchange=RABBITMQ_EXCHANGE,
        rabbitmq_port=RABBITMQ_PORT,
    )

    # Define the service to be run
    ticker = FakeTicker()

    # Register the ticker service with the worker
    worker.add_coroutine(coro=ticker.start)
    worker.subscribe_event(RequestTickEvent)

    # Start the worker
    asyncio.create_task(worker.start())

    # Listen for events
    while True:
        event = await worker.worker_queue.get()
        if isinstance(event, RequestTickEvent):
            await ticker.subscribe(event.symbol)


if __name__ == "__main__":
    asyncio.run(main())
