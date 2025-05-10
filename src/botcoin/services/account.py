"""This module handles the account service for the botcoin application."""

import os

from dotenv import load_dotenv

from botcoin.services import Service
from botcoin.utils.log import logging
from botcoin.data.dataclasses.account import Account, Stock
from botcoin.utils.rabbitmq.async_server import AsyncAMQPServer

# Load environment variables from .env file
load_dotenv()
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
SERVICE_QUEUE = os.getenv("SERVICE_QUEUE", "account_service")


class AccountService(Service):
    """
    This class handles the account service for the botcoin application.
    It manages the connection to the RabbitMQ server and processes incoming requests.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(
        self,
        account: Account = None,
        rabbitmq_hostname: str = None,
        rabbitmq_port: int = None,
        service_queue: str = None,
    ) -> None:
        """
        Initializes the AccountService with the RabbitMQ server details.
        """
        self._account = account or Account()
        self.rabbitmq_host = rabbitmq_hostname or RABBITMQ_HOST
        self.rabbitmq_port = rabbitmq_port or RABBITMQ_PORT
        self.service_queue = service_queue or SERVICE_QUEUE

        self.server = AsyncAMQPServer(
            rabbitmq_hostname=self.rabbitmq_host,
            server_qname=self.service_queue,
            rabbitmq_port=self.rabbitmq_port,
        )

        async def handle_inc_cash_req(request: dict) -> None:
            """request handler for increasing cash"""
            try:
                amount = float(request["query_params"]["amount"][0])
                self._account.increase_cash(amount)
                self.logger.info(
                    "Increased cash by %s. New cash balance: %s",
                    amount,
                    self.get_balance(),
                )
            except KeyError:
                if "amount" not in request["query_params"]:
                    return {
                        "code": 400,
                        "status": "error",
                        "message": "Missing query parameter 'amount'",
                    }
            except ValueError as e:
                return {"code": 400, "status": "error", "message": str(e)}

            return {
                "code": 200,
                "status": "success",
                "message": f"Cash increased by {amount}. New balance: {self.get_balance()}",
            }

        async def handle_dec_cash_req(request: dict) -> None:
            """request handler for decreasing cash"""
            try:
                amount = float(request["query_params"]["amount"][0])
                self._account.decrease_cash(amount)
                self.logger.info(
                    "Decreased cash by %s. New cash balance: %s",
                    amount,
                    self.get_balance(),
                )
            except KeyError:
                if "amount" not in request["query_params"]:
                    return {
                        "code": 400,
                        "status": "error",
                        "message": "Missing query parameter 'amount'",
                    }
            except ValueError as e:
                return {"code": 400, "status": "error", "message": str(e)}

            return {
                "code": 200,
                "status": "success",
                "message": f"Cash decreased by {amount}. New balance: {self.get_balance()}",
            }

        async def handle_buy_stock_req(request: dict) -> None:
            """request handler for buying stock"""
            try:
                query_params = request["query_params"]
                symbol = query_params["symbol"][0]
                quantity = int(query_params["quantity"][0])
                price = float(query_params["price"][0])
                stock = Stock(
                    symbol=symbol,
                    quantity=quantity,
                    open_price=price,
                )
                self._account.buy_stock(stock)
                self.logger.info(
                    "Bought stock %s with quantity %s and price %s.", symbol, quantity, price
                )
            except KeyError:
                missing_params = []
                if "symbol" not in query_params:
                    missing_params.append("symbol")
                if "quantity" not in query_params:
                    missing_params.append("quantity")
                if "price" not in query_params:
                    missing_params.append("price")

                return {
                    "code": 400,
                    "status": "error",
                    "message": f"Missing query parameters: {', '.join(missing_params)}.",
                }

            except ValueError as e:
                return {"code": 400, "status": "error", "message": str(e)}

            return {
                "code": 200,
                "status": "success",
                "message": f"Bought stock {symbol} with quantity {quantity} and price {price}.",
            }

        async def handle_sell_stock_req(request: dict) -> None:
            """request handler for trading stock"""
            try:
                query_params = request["query_params"]
                symbol = query_params["symbol"][0]
                quantity = int(query_params["quantity"][0])
                price = float(query_params["price"][0])
                self._account.sell_stock(symbol, quantity, price)
                self.logger.info(
                    "Sold stock %s with quantity %s at price %s.", symbol, quantity, price
                )
            except KeyError:
                missing_params = []
                if "symbol" not in query_params:
                    missing_params.append("symbol")
                if "quantity" not in query_params:
                    missing_params.append("quantity")
                if "price" not in query_params:
                    missing_params.append("price")

                return {
                    "code": 400,
                    "status": "error",
                    "message": f"Missing query parameters: {', '.join(missing_params)}.",
                }

            except ValueError as e:
                return {"code": 400, "status": "error", "message": str(e)}

            return {
                "code": 200,
                "status": "success",
                "message": f"Sold stock {symbol} with quantity {quantity} and price {price}.",
            }

        async def handle_get_account_banlance(_: dict) -> None:
            """request handler for getting account balance"""
            return {
                "code": 200,
                "status": "success",
                "balance": self.get_balance(),
            }

        async def handle_get_account_stocks(_: dict) -> None:
            """request handler for getting account stocks"""
            return {
                "code": 200,
                "status": "success",
                "stocks": self.get_account_stocks(),
            }

        async def handle_get_account_value(_: dict) -> None:
            """request handler for getting account value"""
            return {
                "code": 200,
                "status": "success",
                "value": self.get_account_value(),
            }

        self.server.register_handler(pattern="/increase_cash", handler=handle_inc_cash_req)
        self.server.register_handler(pattern="/decrease_cash", handler=handle_dec_cash_req)
        self.server.register_handler(pattern="/buy_stock", handler=handle_buy_stock_req)
        self.server.register_handler(pattern="/sell_stock", handler=handle_sell_stock_req)
        self.server.register_handler(
            pattern="/account/balance", handler=handle_get_account_banlance
        )
        self.server.register_handler(pattern="/account/stocks", handler=handle_get_account_stocks)
        self.server.register_handler(pattern="/account/value", handler=handle_get_account_value)

    def get_balance(self) -> float:
        """
        Returns the current cash balance of the account.
        """
        return self._account.cash

    def get_account_value(self) -> float:
        """
        Returns the total value of the account, including cash and stocks.
        """
        return self._account.value

    def get_account_stocks(self) -> dict:
        """
        Returns the stocks held in the account.
        """
        return {
            stock.symbol: {
                "quantity": stock.quantity,
                "open_price": stock.open_price,
            }
            for stock in self._account.stocks.values()
        }

    def get_account_details(self) -> dict:
        """
        Returns the details of the account.
        """
        return self._account.serialize()

    async def start(self) -> None:
        """
        Starts the AccountService by establishing a connection to the RabbitMQ server.
        """
        await self.server.start()

    async def stop(self) -> None:
        """
        Stops the AccountService by closing the connection to the RabbitMQ server.
        """
        await self.server.stop()
