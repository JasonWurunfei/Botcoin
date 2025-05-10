"""This module is ued to implement a simulated broker for the botcoin framework."""

import asyncio
from abc import ABC, abstractmethod


from botcoin.utils.log import logging
from botcoin.data.dataclasses.order import Order, OrderType, OrderStatus, OrderBookItem
from botcoin.data.dataclasses.events import (
    Event,
    TickEvent,
    OrderStatusEvent,
    PlaceOrderEvent,
    CancelOrderEvent,
    ModifyOrderEvent,
    OrderModifiedEvent,
    RequestTickEvent,
    RequestStopTickEvent,
)
from botcoin.services import Service
from botcoin.utils.rabbitmq.async_client import AsyncAMQPClient
from botcoin.utils.rabbitmq.event import EventReceiver


class Broker(Service, EventReceiver, ABC):
    """
    Abstract base class for a broker.

    This class is used to implement a broker for the botcoin framework.
    """

    @abstractmethod
    async def start(self) -> None:
        """
        This method starts the broker.
        """

    @abstractmethod
    async def stop(self) -> None:
        """
        This method stops the broker.
        """

    @abstractmethod
    async def place_order(self, order: Order) -> None:
        """
        This method places an order.

        :param order: The order to be placed.
        """

    @abstractmethod
    async def cancel_order(self, order: Order) -> None:
        """
        This method cancels an order.

        :param order: The order to be cancelled.
        """

    @abstractmethod
    async def modify_order(self, modified_order: Order) -> None:
        """
        This method modifies an order.

        :param modified_order: The order to be modified.
        """

    async def on_event(self, event: Event) -> None:
        if isinstance(event, PlaceOrderEvent):
            asyncio.create_task(self.place_order(event.order))
        elif isinstance(event, CancelOrderEvent):
            asyncio.create_task(self.cancel_order(event.order))
        elif isinstance(event, ModifyOrderEvent):
            asyncio.create_task(self.modify_order(event.modified_order))


class SimulatedBroker(Broker, ABC):
    """
    This class is a simulated broker that simulates the behavior of a real broker.
    """

    @abstractmethod
    async def trade_order(self, order: Order, price: float) -> None:
        """
        This method trades an order.

        :param order: The order to be traded.
        :param price: The price at which the order is traded.
        """

    @abstractmethod
    async def on_tick_event(self, tick_event: TickEvent) -> None:
        """
        This method is called when a tick event is received.
        It is used to trigger the order execution.

        :param tick_event: The tick event that was received.
        """

    async def on_event(self, event: Event) -> None:
        await super().on_event(event)
        if isinstance(event, TickEvent):
            asyncio.create_task(self.on_tick_event(event))


class SimpleBroker(SimulatedBroker):
    """
    This class is a simple broker that simulates the behavior of a real broker.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(self) -> None:
        self._order_book: dict[str, OrderBookItem] = {}
        self._async_client = AsyncAMQPClient()
        self._async_client.set_logger_name("SimpleBroker")

    async def start(self) -> None:
        await self._async_client.connect()
        self.logger.info("SimpleBroker started.")

    async def stop(self) -> None:
        await self._async_client.close()
        self.logger.info("SimpleBroker stopped.")

    async def place_order(self, order: Order) -> None:
        self._order_book[order.order_id] = OrderBookItem(
            order_id=order.order_id,
            order=order,
            status=OrderStatus.NOT_TRADED,
        )
        if self._is_last_order_for_symbol(order):
            self._async_client.emit_event(
                event=RequestTickEvent(
                    symbol=order.symbol,
                ),
            )

    async def cancel_order(self, order: Order) -> None:
        if order.order_id in self._order_book:
            order_book_item = self._order_book[order.order_id]
            order_book_item.status = OrderStatus.CANCELLED
            self._async_client.emit_event(
                event=OrderStatusEvent(
                    order=order,
                    status=OrderStatus.CANCELLED,
                ),
            )
            if self._is_last_order_for_symbol(order):
                self._async_client.emit_event(
                    event=RequestStopTickEvent(
                        symbol=order.symbol,
                    ),
                )

            self.logger.info("Order %s cancelled", order.order_id)
        else:
            self.logger.warning("Order %s not found in order book", order.order_id)

    async def modify_order(self, modified_order: Order) -> None:
        if modified_order.order_id in self._order_book:
            order_book_item = self._order_book[modified_order.order_id]
            order_book_item.order = modified_order
            self._async_client.emit_event(
                event=OrderModifiedEvent(
                    modified_order=modified_order,
                ),
            )

            self.logger.info("Order %s modified", modified_order.order_id)
        else:
            self.logger.warning(
                "Order %s not found in order book for modification",
                modified_order.order_id,
            )

    async def trade_order(self, order: Order, price: float) -> None:
        order_book_item = self._order_book[order.order_id]
        order_book_item.status = OrderStatus.TRADED

        self._async_client.emit_event(
            event=OrderStatusEvent(
                order=order,
                status=OrderStatus.TRADED,
            ),
        )

        if self._is_last_order_for_symbol(order):
            self._async_client.emit_event(
                event=RequestStopTickEvent(
                    symbol=order.symbol,
                ),
            )

        self.logger.info(
            "Order %s executed, traded %s stocks of %s at price: %s",
            order.order_id,
            order.quantity,
            order.symbol,
            price,
        )

    async def on_tick_event(self, tick_event: TickEvent) -> None:
        symbol = tick_event.symbol
        price = tick_event.price

        related_orders = [
            item.order for item in self._order_book.values() if item.order.symbol == symbol
        ]

        for order in related_orders:
            if self._is_tradeable(order, price):
                await self.trade_order(order, price)
            else:
                self.logger.debug(
                    "Order %s not tradeable at price %s",
                    order.order_id,
                    price,
                )

    def _is_tradeable(self, order: Order, price: float) -> bool:
        """
        This method checks if an order is tradeable.

        It checks if the order can be executed at the current market price.
        :param order: The order to be processed.
        :param price: The current market price.
        :return: True if the order can be executed, False otherwise.
        """
        if order.order_type == OrderType.MARKET:
            return True
        elif order.order_type == OrderType.LIMIT:
            if (order.direction == "buy" and price <= order.limit_price) or (
                order.direction == "sell" and price >= order.limit_price
            ):
                return True
        elif order.order_type == OrderType.STOP:
            raise NotImplementedError("Stop orders are not implemented yet.")
        elif order.order_type == OrderType.OCO:
            raise NotImplementedError("OCO orders are not implemented yet.")
        else:
            self.logger.warning("Unknown order type: %s", order.order_type)
            return False

    def _is_last_order_for_symbol(self, order: Order) -> bool:
        """
        This method checks if the order is the last order for the symbol.

        :param order: The order to be processed.
        :return: True if the order is the last order for the symbol, False otherwise.
        """
        return (
            len([item for item in self._order_book.values() if item.order.symbol == order.symbol])
            == 1
        )
