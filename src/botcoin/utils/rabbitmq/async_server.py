"""This script contains an implementaion of an async resolver server over AMQP protocol"""

import re
import json
import asyncio
from typing import Callable, Dict, Any
from urllib.parse import urlparse, parse_qs

import aio_pika

from botcoin.utils.log import logging


class AsyncAMQPServer:
    """
    A server to handle requests from an AMQP client using async communication.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(
        self,
        rabbitmq_hostname: str,
        server_qname: str,
        rabbitmq_port: int = 5672,
    ) -> None:
        """
        Initializes the AMQPServer with the server's hostname and queue name.

        Args:
            rabbitmq_hostname (str): The hostname of the RabbitMQ server.
            rabbitmq_port (int): The port of the RabbitMQ Server
            server_qname (str): The name of the server queue to send requests to.

        """
        self.rabbitmq_hostname: str = rabbitmq_hostname
        self.rabbitmq_port = rabbitmq_port
        self.server_qname: str = server_qname
        self.connection = None
        self.channel = None
        self.handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    async def connect(self):
        """
        Establishes a connection to the AMQP server and sets up the channel and queue.
        """
        self.logger.info(
            "Trying to establish connection with RabbitMQ server @%s.",
            self.rabbitmq_hostname,
        )

        connected = False
        while not connected:
            try:
                self.connection = await aio_pika.connect_robust(
                    host=self.rabbitmq_hostname, port=self.rabbitmq_port
                )
                self.channel = await self.connection.channel()

                # Declare and queue
                await self.channel.declare_queue(self.server_qname, durable=True)

                connected = True
                self.logger.info(
                    "Connection with RabbitMQ server @%s established.",
                    self.rabbitmq_hostname,
                )
            except aio_pika.exceptions.AMQPError as e:
                self.logger.error("Connection error: %s. Retrying in 5 seconds...", e)
                await asyncio.sleep(5)

    async def handle_request(self, message: aio_pika.IncomingMessage):
        """
        Handles an incoming request message, processes it, and sends the response back.

        Args:
            message (aio_pika.IncomingMessage): The incoming message to process.
        """
        async with message.process():
            self.logger.info(
                "Received message with correlation_id: %s", message.correlation_id
            )
            request = json.loads(message.body.decode())

            # Process the request by dispatching to the correct handler
            response = await self.dispatch_handler(request)

            # Send the response back to the client
            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(response).encode(),
                    correlation_id=message.correlation_id,
                    content_type="application/json",
                ),
                routing_key=message.reply_to,
            )

    async def dispatch_handler(self, request: dict) -> dict:
        """
        Dispatches the request to the registered handler based on the URL.

        Args:
            request (dict): The request data sent by the client.

        Returns:
            dict: The response data to send back to the client.
        """
        url = request["url"]
        # Parse the URL
        parsed_url = urlparse(url)
        # Extract the base URL (path)
        base_url = parsed_url.path
        request["base_url"] = base_url
        # Extract the query parameters
        query_params = parse_qs(parsed_url.query)
        request["query_params"] = query_params

        self.logger.info("Dispatching request for URL: %s", url)

        for pattern, handler in self.handlers.items():
            if re.match(pattern, url):
                self.logger.info("Found handler for URL: %s", url)
                return await handler(request)

        self.logger.warning("No handler found for URL: %s", url)
        return {
            "status": "error",
            "message": f"No handler found for URL: {url}",
        }

    def register_handler(
        self, pattern: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """
        Registers a handler for a specific URL pattern.

        Args:
            pattern (str): The URL pattern to match.
            handler (Callable): The handler function to call when the URL matches.
        """
        self.handlers[f"^{pattern}"] = handler
        self.logger.info("Registered handler for pattern: %s", pattern)

    async def start(self):
        """
        Starts the server to listen and process incoming requests.
        """

        try:
            await self.connect()

            queue = await self.channel.declare_queue(self.server_qname, durable=True)
            await queue.consume(self.handle_request)

            self.logger.info("Server is listening for requests...")

            # Keep the server running
            await asyncio.Future()

        finally:
            await self.stop()

    async def stop(self) -> None:
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

        self.logger.info("AsyncAMQPServer clean up finished.")
