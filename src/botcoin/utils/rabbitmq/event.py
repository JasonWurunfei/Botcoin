"""This module handles the RabbitMQ events for the Botcoin application."""

import json
from abc import ABC, abstractmethod

import aio_pika
from aio_pika.abc import AbstractChannel

from botcoin.utils.rabbitmq.conn import RABBITMQ_URL, RABBITMQ_EXCHANGE
from botcoin.data.dataclasses.events import Event


class EventReceiver(ABC):
    """
    Abstract base class for event receivers.
    """

    @abstractmethod
    async def on_event(self, event: Event) -> None:
        """
        Abstract method to handle incoming events.

        Args:
            event (Event): The event to be handled.
        """


async def emit_event(
    event: Event,
    routing_key: str = "",
) -> None:
    """
    Emit an event to RabbitMQ.

    Args:
        exchange_name (str): The name of the exchange to publish the event to.
        body (dict): The body of the event to be published.
        routing_key (str, optional): The routing key for the event. Defaults to "".
    """
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.get_exchange(RABBITMQ_EXCHANGE)

        body = event.serialize()

        message = aio_pika.Message(
            body=json.dumps(body).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await exchange.publish(message, routing_key=routing_key)


async def emit_event_with_channel(
    event: Event,
    channel: AbstractChannel,
    exchange_name: str = RABBITMQ_EXCHANGE,
    routing_key: str = "",
) -> None:
    """
    Emit an event to RabbitMQ using an existing channel.

    Args:
        event (Event): The event to be emitted.
        channel (AbstractChannel): The existing channel to use for publishing.
        routing_key (str, optional): The routing key for the event. Defaults to "".
    """

    exchange = await channel.get_exchange(exchange_name)

    body = event.serialize()

    message = aio_pika.Message(
        body=json.dumps(body).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )

    await exchange.publish(message, routing_key=routing_key)
