"""This module is ued to implement a simulated broker for the botcoin framework."""

import asyncio
from asyncio import Queue


from botcoin.utils.log import logging
from botcoin.data.dataclasses import (
    Order,
    OrderStatusEvent,
    PlaceOrderEvent,
    OrderStatus,
)


class SimpleBroker:
    """
    This class is a simple broker that simulates the behavior of a real broker.

    It always trades immediately at the market price.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(self, broker_queue: Queue = None):
        self.broker_queue = broker_queue or Queue()

    async def run(self) -> None:
        """
        This method starts the broker.

        It runs in an infinite loop, waiting for orders to be placed.
        """

        while True:
            order = await self.broker_queue.get()
            await self.on_order(order)
            self.broker_queue.task_done()

    def get_queue(self) -> Queue:
        """
        This method returns the broker queue.

        :return: The broker queue.
        """
        return self.broker_queue

    async def place_order(self, order: Order) -> dict:
        """
        This method places an order.

        :param order: The order to be placed.
        """
        await asyncio.sleep(0.1)  # Simulate network delay
        return {
            "order_id": order.order_id,
            "status": OrderStatus.NOT_TRADED,
        }

    async def on_order(self, order_event: PlaceOrderEvent) -> None:
        """
        This method is called when an order is placed.

        :param order: The order that was placed.
        """
        reply_to = order_event.reply_to
        order = order_event.order
        if reply_to is not None:
            res = await self.place_order(order)
            order_status_event = OrderStatusEvent(
                order=order,
                status=res["status"],
            )

            await reply_to.put(order_status_event)
            self.logger.debug(
                "Order %s processed with status: %s",
                order.order_id,
                res["status"].value,
            )
            asyncio.create_task(self.simulate_trade(order, reply_to))

    async def simulate_trade(self, order: Order, reply_to: Queue) -> None:
        """
        This method simulates a trade.

        :param order: The order to be traded.
        """
        # random sleep to simulate trade execution time
        await asyncio.sleep(2)
        order_status_event = OrderStatusEvent(
            order=order,
            status=OrderStatus.TRADED,
        )
        await reply_to.put(order_status_event)
        self.logger.debug(
            "Order %s traded with status: %s",
            order.order_id,
            order_status_event.status.value,
        )
