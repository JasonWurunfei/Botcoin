"""This script is used to start the Botcoin application."""

import os
import asyncio
from datetime import datetime

from dotenv import load_dotenv

from botcoin.utils.rabbitmq.worker import AsyncEventWorker

from botcoin.data.tickers import HistoricalTicker

load_dotenv()
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "botcoin")

start = datetime(year=2025, month=4, day=25, hour=9, minute=30, second=10)
end = datetime(year=2025, month=4, day=25, hour=15, minute=59, second=55)
ticker = HistoricalTicker(
    symbols=["AAPL"], start_date=start, end_date=end, real_time=True
)

if __name__ == "__main__":
    # Start the RabbitMQ worker process
    worker = AsyncEventWorker(
        rabbitmq_user=RABBITMQ_USER,
        rabbitmq_pass=RABBITMQ_PASS,
        rabbitmq_host=RABBITMQ_HOST,
        rabbitmq_qname="ticker",
        rabbitmq_exchange=RABBITMQ_EXCHANGE,
        rabbitmq_port=RABBITMQ_PORT,
    )
    ticker_queue = asyncio.Queue()
    worker.add_coroutine(coro=ticker.stream, event_queue=ticker_queue)
    asyncio.run(worker.start())
