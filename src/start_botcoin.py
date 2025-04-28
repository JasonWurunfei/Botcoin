"""This script is used to start the Botcoin application."""

import asyncio
from botcoin.utils.worker import RabbitMQAdapterWorker


async def test_function() -> None:
    while True:
        print("Test function running...")
        await asyncio.sleep(1)


if __name__ == "__main__":
    # Start the RabbitMQ worker process
    worker = RabbitMQAdapterWorker()
    worker.add_task(test_function)
    asyncio.run(worker.start())
