"""This script contains an implementaion of an async client over AMQP protocol"""

import uuid
import json

import aio_pika

from botcoin.utils.log import logging


class AsyncAMQPClient:
    """
    A client to communicate with an AMQP server using RPC-like calls.

    This client allows you to send messages to an AMQP server and receive
    responses. Each request is sent with a unique correlation ID, and the
    response is matched based on this ID.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(self, rabbitmq_hostname: str = None, rabbitmq_port: int = 5672) -> None:
        """
        Initializes the AMQPClient with the server's hostname and queue name.

        Args:
            rabbitmq_hostname (str): The hostname of the RabbitMQ server.
            rabbitmq_port (int): The port of the RabbitMQ Server
        """
        self.rabbitmq_hostname: str = rabbitmq_hostname or "localhost"
        self.rabbitmq_port: int = rabbitmq_port
        self.connection = None
        self.channel = None

    async def connect(self):
        """
        Establishes a connection to the AMQP server and sets up the channel,
        callback queue, and basic consumer.
        """
        self.logger.info("Trying to establish connection with server @%s.", self.rabbitmq_hostname)

        self.connection = await aio_pika.connect_robust(
            host=self.rabbitmq_hostname, port=self.rabbitmq_port
        )
        self.channel = await self.connection.channel()
        self.logger.info("Connection with server @%s established.", self.rabbitmq_hostname)

    async def call(self, url: str, server_qname: str) -> dict:
        """
        Sends a request message to the server with the specified URL and waits
        for the response.

        Args:
            url (str): The URL to send as part of the request.
            server_qname (str): The name of the server queue to send for this request.

        Returns:
            dict: The decoded JSON response from the server.
        """
        corr_id = str(uuid.uuid4())

        req = {"url": url}

        if self.connection is None or self.connection.is_closed:
            if self.channel is None or self.channel.is_closed:
                self.logger.debug(
                    "RabbitMQ connection is not active. Reconnecting to server @%s.",
                    self.rabbitmq_hostname,
                )
                await self.connect()
            else:
                self.logger.debug(
                    "RabbitMQ channel is not active. Reconnecting to server @%s.",
                    self.rabbitmq_hostname,
                )
                self.channel = await self.connection.channel()

        callback_queue = await self.channel.declare_queue("", auto_delete=True, exclusive=True)

        # Declare server queue in case the queue is not created.
        await self.channel.declare_queue(server_qname, durable=True)

        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(req).encode(),
                reply_to=callback_queue.name,
                correlation_id=corr_id,
                content_type="application/json",
            ),
            routing_key=server_qname,
        )

        self.logger.info(
            "Request: %s sent to server queue: %s with correlation_id: %s",
            url,
            server_qname,
            corr_id,
        )

        resp = None

        async with callback_queue.iterator() as queue_iter:
            async for message in queue_iter:
                msg_body = message.body.decode()
                if message.correlation_id == corr_id:
                    self.logger.info("Message id: %s received.", corr_id)
                    async with message.process():
                        resp = json.loads(msg_body)
                        break

        return resp

    async def close(self) -> None:
        """
        Closes the connection to the AMQP server.
        """
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
            self.logger.debug("RabbitMQ channel closed.")
        self.channel = None

        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            self.logger.debug("RabbitMQ connection closed.")
        self.connection = None
        self.logger.info("AsyncAMQPClient clean up finished.")
