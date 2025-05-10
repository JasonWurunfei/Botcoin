"""This script contains an implementaion of an async client over AMQP protocol"""

import uuid
import json
import asyncio

import aio_pika

from botcoin.utils.log import logging

from botcoin.data.dataclasses.events import Event
from botcoin.utils.rabbitmq.conn import new_connection, RABBITMQ_EXCHANGE


class AsyncAMQPClient:
    """
    A client to communicate with an AMQP server using RPC-like calls.

    This client allows you to send messages to an AMQP server and receive
    responses. Each request is sent with a unique correlation ID, and the
    response is matched based on this ID.
    """

    def __init__(self) -> None:
        """
        Initializes the AMQPClient with the server's hostname and queue name.
        """
        self.connection = None
        self.channel = None
        self.logger = logging.getLogger("AsyncAMQPClient")

    async def connect(self):
        """
        Establishes a connection to the AMQP server and sets up the channel,
        callback queue, and basic consumer.
        """
        self.connection = await new_connection()
        self.channel = await self.connection.channel()
        self.logger.info("Connection with RabbitMQ server established.")

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

        await self._reconnect_if_needed()

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

    def emit_event(
        self,
        event: Event,
        routing_key: str = "",
        exchange_name: str = None,
    ) -> None:
        """
        Emit an event to RabbitMQ. By default, it uses the exchange defined in
        the RABBITMQ_EXCHANGE constant.

        This method serializes the event and sends it to the specified exchange
        with the given routing key. The routing key is empty by default as the default
        exchange is fanout.

        Args:
            event (Event): The event to be emitted.
            routing_key (str): The routing key for the event.
            exchange_name (str): The name of the exchange to publish the event to.
        """

        async def emit() -> None:
            await self._reconnect_if_needed()

            exchange = await self.channel.get_exchange(exchange_name or RABBITMQ_EXCHANGE)

            body = event.serialize()

            message = aio_pika.Message(
                body=json.dumps(body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )

            await exchange.publish(message, routing_key=routing_key)

            self.logger.info("Event emitted: %s", event)

        asyncio.create_task(emit())

    async def _reconnect_if_needed(self) -> None:
        """
        Reconnects to the RabbitMQ server if the connection is closed.
        """
        if self.connection is None or self.connection.is_closed:
            self.logger.debug("RabbitMQ connection is not active. Reconnecting to RabbitMQ server.")
            await self.connect()
        elif self.channel is None or self.channel.is_closed:
            self.logger.debug("RabbitMQ channel is not active. Reconnecting to RabbitMQ server.")
            self.channel = await self.connection.channel()

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

    def set_logger_name(self, caller_name: str) -> None:
        """
        Sets the logger name for the client.
        This method is used to set the logger name for the client. It can be
        useful for debugging purposes.
        Args:
            caller_name (str): The name of the caller.
        """
        self.logger = logging.getLogger(f"{caller_name}.AsyncAMQPClient")
