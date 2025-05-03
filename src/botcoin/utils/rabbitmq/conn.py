"""This module handles the connection to RabbitMQ for message publishing and subscribing."""

import os

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from dotenv import load_dotenv


load_dotenv()
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "botcoin")
RABBITMQ_URL: str = (
    f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}"
)


async def new_connection() -> AbstractRobustConnection:
    """
    Get the RabbitMQ connection string.

    Returns:
        AbstractRobustConnection: The RabbitMQ connection object.
    """
    return await aio_pika.connect_robust(RABBITMQ_URL)
