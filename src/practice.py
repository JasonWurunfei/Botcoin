"""This is script to practice trading with the botcoin library."""

import asyncio
from datetime import datetime

# from botcoin.data.tickers import FinnhubTicker
from botcoin.services.tickers import HistoricalTicker
from botcoin.services.broker import SimpleBroker

from botcoin.data.dataclasses.order import MarketOrder, LimitOrder
from botcoin.data.dataclasses.events import PlaceOrderEvent

SYMBOL = "AAPL"  # Example symbol, replace with your desired stock symbol

# ticker = FinnhubTicker([])

start = datetime(year=2025, month=4, day=25, hour=9, minute=30, second=10)
end = datetime(year=2025, month=4, day=25, hour=15, minute=59, second=55)
ticker = HistoricalTicker(start_date=start, end_date=end, real_time=True)

ticker_queue = ticker.get_broadcast_queue()

broker = SimpleBroker(ticker)
broker_queue = broker.get_queue()


async def main():
    """ "Main function to run the backtest."""
    task = asyncio.gather(
        ticker.stream(),
        broker.run(),
    )

    # Make a fake market order to test the broker
    queue = asyncio.Queue()
    order = MarketOrder(order_id="1234", symbol=SYMBOL, quantity=10, direction="sell")
    order_event = PlaceOrderEvent(order=order, reply_to=queue)
    await broker_queue.put(order_event)

    # Make a fake limit order to test the broker
    order = LimitOrder(
        order_id="5678",
        symbol=SYMBOL,
        quantity=5,
        direction="buy",
        limit_price=206.9,
    )
    order_event = PlaceOrderEvent(order=order, reply_to=queue)
    await broker_queue.put(order_event)

    await task


if __name__ == "__main__":
    asyncio.run(main())
