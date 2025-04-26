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
from botcoin.data.tickers import FinnhubTicker
from botcoin.utils.message_queue import BroadcastQueue
from botcoin.data.dataclasses import OrderType, OrderBookItem


class SimpleBroker:
    """
    This class is a simple broker that simulates the behavior of a real broker.

    It always trades immediately at the market price.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(
        self,
        ticker: FinnhubTicker,
        broker_queue: Queue = None,
    ) -> None:
        self.broker_queue = broker_queue or Queue()
        self.ticker = ticker
        self.orderbook = {}

    async def run(self) -> None:
        """
        This method starts the broker.

        It runs in an infinite loop, waiting for orders to be placed.
        """

        while True:
            evt = await self.broker_queue.get()
            if isinstance(evt, PlaceOrderEvent):
                order = evt.order
                self.logger.debug("Received order: %s", order)
                await self.on_order(evt)
            else:
                self.logger.warning("Unknown event type: %s", type(evt))
            self.broker_queue.task_done()

    async def on_order(self, order_event: PlaceOrderEvent) -> None:
        """
        This method is called when an order is placed.

        :param order: The order that was placed.
        """
        reply_to = order_event.reply_to
        order = order_event.order
        if reply_to is not None:
            orderbook_item = await self.place_order(order, reply_to)
            order_status_event = OrderStatusEvent(
                order=order,
                status=orderbook_item.status,
            )

            await reply_to.put(order_status_event)
            self.logger.debug(
                "Order %s processed with status: %s",
                order.order_id,
                order_status_event.status.value,
            )

    async def place_order(self, order: Order, reply_to: Queue) -> dict:
        """
        This method places an order.

        :param order: The order to be placed.
        :param reply_to: The queue to send the order status event.
        """
        await asyncio.sleep(0.1)  # Simulate network delay

        # create a queue for receiving price tick events
        order_queue = asyncio.Queue()

        # register the order to the orderbook
        orderbook_item = OrderBookItem(
            order_id=order.order_id,
            order=order,
            queue=order_queue,
        )
        self.orderbook[order.order_id] = orderbook_item

        # create a task to run the order
        asyncio.create_task(self.run_order(order, order_queue, reply_to))

        return orderbook_item

    async def run_order(
        self, order: Order, order_queue: Queue, reply_to: Queue
    ) -> None:
        """
        This method runs the order.

        :param order: The order to be run.
        """
        orderbook_item = self.orderbook.get(order.order_id)

        # Simulate order execution
        self.logger.debug("Running order: %s", order)

        # register the order queue with the ticker
        ticker_queue: BroadcastQueue = self.ticker.get_broadcast_queue()
        ticker_queue.register(order_queue)

        # subscribe to the ticker for the order symbol
        await self.ticker.subscribe(order.symbol)

        # wait for the events
        while True:
            try:
                # wait for the next price tick event
                price_event = await order_queue.get()
                self.logger.debug("Received price event: %s", price_event)

                # process the price event
                current_price = price_event.price
                if order.order_type == OrderType.MARKET:
                    if self.can_trade_market_order():
                        await self.execute_trade(
                            order=order,
                            traded_price=current_price,
                            reply_to=reply_to,
                        )
                        break

                if order.order_type == OrderType.LIMIT:
                    if self.can_trade_limit_order(current_price, order):
                        await self.execute_trade(
                            order=order,
                            traded_price=current_price,
                            reply_to=reply_to,
                        )
                        break

                if order.order_type == OrderType.STOP:
                    raise NotImplementedError("Stop orders are not implemented yet.")
                if order.order_type == OrderType.OCO:
                    raise NotImplementedError("OCO orders are not implemented yet.")

                self.logger.debug(
                    "%s order %s not executed, current price: %s",
                    order.order_type.value,
                    order.order_id,
                    current_price,
                )

            except asyncio.CancelledError:
                self.logger.debug("Order %s cancelled", order.order_id)
                orderbook_item.status = OrderStatus.CANCELLED
                break

        orderbook_item.status = OrderStatus.CANCELLED
        orderbook_item.queue = None

    def can_trade_limit_order(self, current_price: float, order: Order) -> bool:
        """
        This method checks if a limit order can be executed
        It checks if the order can be executed at the current market price.

        :param cur_price: The current market price.
        :param order: The order to be processed.
        :return: True if the order can be executed, False otherwise.
        """

        if (order.direction == "buy" and current_price <= order.limit_price) or (
            order.direction == "sell" and current_price >= order.limit_price
        ):
            return True
        return False

    def can_trade_market_order(self) -> bool:
        """
        This method checks if a market order can be executed.

        It will return True if the market is open and the order is valid.
        """
        return True

    async def execute_trade(
        self, order: Order, traded_price: float, reply_to: Queue
    ) -> None:
        """
        This method simulates executing a trade.

        :param order: The order to be traded.
        :param traded_price: The price at which the order was traded.
        :param reply_to: The queue to send the order status event.
        :return: None
        """
        order_status_event = OrderStatusEvent(
            order=order,
            status=OrderStatus.TRADED,
        )
        await reply_to.put(order_status_event)
        self.logger.debug(
            "Order %s executed, traded %s stocks of %s at price: %s",
            order.order_id,
            order.quantity,
            order.symbol,
            traded_price,
        )

    def get_queue(self) -> Queue:
        """
        This method returns the broker queue.

        :return: The broker queue.
        """
        return self.broker_queue
