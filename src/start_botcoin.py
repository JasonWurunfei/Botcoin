"""This script is used to start the Botcoin application."""

import os
import signal
import asyncio

from dotenv import load_dotenv

from botcoin.utils.log import logging
from botcoin.utils.rabbitmq.worker import AsyncEventWorker

from botcoin.data.tickers import FinnhubTicker
from botcoin.data.dataclasses.events import RequestTickEvent, TickEvent

load_dotenv()
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "botcoin")
FINNHUB_API_KEY = os.getenv("FINNHUB_TOKEN")

stop_event = asyncio.Event()

logger = logging.getLogger("start_botcoin")


def shutdown():
    """
    Signal handler to set the stop event when a shutdown signal is received.
    """
    logger.info("Received shutdown signal. Stopping...")
    stop_event.set()


async def main():
    """
    Main function to start the Botcoin application.
    """
    # Register shutdown signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

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
    ticker = FinnhubTicker(
        api_key=FINNHUB_API_KEY,
    )

    # Register the ticker service with the worker
    worker.add_coroutine(coro=ticker.start)
    worker.subscribe_event(RequestTickEvent)
    worker.subscribe_event(TickEvent)

    # Start the worker
    worker_task = asyncio.create_task(worker.start())

    try:
        # Main event loop
        while not stop_event.is_set():
            try:
                event = await asyncio.wait_for(worker.worker_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue  # Check for stop_event periodically
            if isinstance(event, RequestTickEvent):
                await ticker.subscribe(event.symbol)
    finally:
        # Cleanup
        await worker.stop()
        if worker_task:
            await worker_task
        logger.info("Worker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
