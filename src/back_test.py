"""This script is used to start the Botcoin application."""

import asyncio
from datetime import datetime

from botcoin.utils.rabbitmq.worker import AsyncEventWorker, run_worker


from botcoin.services.stepper import Stepper
from botcoin.services.tickers import SimulatedTicker

from botcoin.data.dataclasses.events import TickEvent


async def main():
    """
    Main function to start the Botcoin application.
    """

    # Initialize the worker
    worker = AsyncEventWorker(qname="botcoin_worker")

    # Set up simulation time frame
    start = datetime(year=2025, month=5, day=13, hour=9, minute=31, second=0)
    end = datetime(year=2025, month=5, day=13, hour=10, minute=30, second=0)

    # Service initialization
    stepper = Stepper(from_=start, to=end, speed=100, freq=100)
    ticker = SimulatedTicker(from_=start, to=end)

    # Register the ticker service with the worker
    worker.add_service(ticker)
    worker.add_service(stepper)

    # Register event receivers
    worker.add_event_receiver(ticker)
    worker.add_event_receiver(stepper)

    # Subscribe to events
    worker.subscribe_events(
        [
            TickEvent,
        ]
    )

    await asyncio.create_task(run_worker(worker))


if __name__ == "__main__":
    asyncio.run(main())
