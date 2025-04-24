"""
This script is used to run a backtest using the botcoin framework.
"""

import asyncio
from datetime import datetime

from botcoin.data.data_fetcher import PriceTicker
from botcoin.broker.simulated import SimpleBroker
from botcoin.runner import StrategyRunner

from botcoin.data.dataclasses import TickEvent


ticker = PriceTicker(["MSTR"])

broker = SimpleBroker()
broker_queue = broker.get_queue()

runner_queue = asyncio.Queue()
sr = StrategyRunner(runner_queue=runner_queue, broker_queue=broker_queue)
ticker_queue = ticker.get_broadcast_queue()
ticker_queue.register(runner_queue)


async def main():
    """ "Main function to run the backtest."""
    task = asyncio.gather(
        # ticker.connect(),  # uncomment this when you want live data
        broker.run(),
        sr.run(),
    )
    print("Starting broker and strategy runner...")
    await asyncio.sleep(1)  # Give some time for the broker and strategy runner to start

    # Simulate a price tick
    tick = TickEvent(
        symbol="MSTR", price=100.0, event_time=datetime.now(ticker.tz)  # Example price
    )
    await ticker_queue.publish(tick)
    print("Published price tick:", tick)

    await task


if __name__ == "__main__":
    asyncio.run(main())
