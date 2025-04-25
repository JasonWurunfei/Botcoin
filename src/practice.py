"""This is script to practice trading with the botcoin library."""

import asyncio

from botcoin.data.data_fetcher import PriceTicker
from botcoin.broker.simulated import SimpleBroker

from botcoin.data.dataclasses import (
    MarketOrder,
    LimitOrder,
    PlaceOrderEvent,
    TickEvent,
    now_us_east,
)


ticker = PriceTicker([])
ticker_queue = ticker.get_broadcast_queue()

broker = SimpleBroker(ticker)
broker_queue = broker.get_queue()


async def main():
    """ "Main function to run the backtest."""
    task = asyncio.gather(
        # ticker.connect(),  # uncomment this when you want live data, make sure market open
        broker.run(),
    )

    await asyncio.sleep(1)
    queue = asyncio.Queue()

    # Make a fake market order to test the broker
    order = MarketOrder(order_id="1234", symbol="MSTR", quantity=10, direction="sell")
    order_event = PlaceOrderEvent(order=order, reply_to=queue)
    await broker_queue.put(order_event)

    # Make a fake limit order to test the broker
    order = LimitOrder(
        order_id="5678",
        symbol="MSTR",
        quantity=5,
        direction="buy",
        limit_price=400.0,
    )
    order_event = PlaceOrderEvent(order=order, reply_to=queue)
    await broker_queue.put(order_event)

    # Simulate a price tick
    await asyncio.sleep(1)  # Simulate some delay before the tick
    tick = TickEvent(
        symbol="MSTR", price=321.0, event_time=now_us_east()  # Example price
    )
    await ticker_queue.publish(tick)

    await task


if __name__ == "__main__":
    asyncio.run(main())
