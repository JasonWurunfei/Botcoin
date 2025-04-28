"""This script is used to start the Botcoin application."""

import asyncio
from datetime import datetime

from botcoin.utils.worker import RabbitMQAdapterWorker
from botcoin.data.tickers import HistoricalTicker


start = datetime(year=2025, month=4, day=25, hour=9, minute=30, second=10)
end = datetime(year=2025, month=4, day=25, hour=15, minute=59, second=55)
ticker = HistoricalTicker(
    symbols=["AAPL"], start_date=start, end_date=end, real_time=True
)

if __name__ == "__main__":
    # Start the RabbitMQ worker process
    worker = RabbitMQAdapterWorker()
    worker.add_task(ticker.stream)
    asyncio.run(worker.start())
