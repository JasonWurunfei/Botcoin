"""This script is used to start the Botcoin application."""

import signal
import asyncio
from datetime import datetime

from botcoin.utils.log import logging
from botcoin.utils.rabbitmq.worker import AsyncEventWorker


from botcoin.services.stepper import Stepper
from botcoin.services.tickers import SimulatedTicker

from botcoin.data.dataclasses.events import (
    TickEvent,
    TimeStepEvent,
    RequestTickEvent,
    SimStartEvent,
    SimStopEvent,
)


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
    worker = AsyncEventWorker(qname="botcoin_worker")

    # Set up simulation time frame
    start = datetime(year=2025, month=5, day=13, hour=9, minute=31, second=0)
    end = datetime(year=2025, month=5, day=13, hour=10, minute=30, second=0)

    # Service initialization
    stepper = Stepper(from_=start, to=end, speed=100, freq=100)
    ticker = SimulatedTicker(from_=start, to=end)

    # Register the ticker service with the worker
    worker.add_coroutine(coro=stepper.start)
    worker.add_coroutine(coro=ticker.start)

    # Subscribe to events
    worker.subscribe_event(TickEvent)
    worker.subscribe_event(TimeStepEvent)
    worker.subscribe_event(SimStopEvent)
    worker.subscribe_event(SimStartEvent)
    worker.subscribe_event(RequestTickEvent)

    # Start the worker
    worker_task = asyncio.create_task(worker.start())

    try:
        # Main event loop
        while not stop_event.is_set():
            try:
                event = await asyncio.wait_for(worker.worker_queue.get(), timeout=1.0)
                asyncio.create_task(stepper.on_event(event))
                asyncio.create_task(ticker.on_event(event))
            except asyncio.TimeoutError:
                continue  # Check for stop_event periodically
    finally:
        # Cleanup
        await ticker.stop()
        await stepper.stop()
        await worker.stop()
        if worker_task:
            await worker_task
        logger.info("Worker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
