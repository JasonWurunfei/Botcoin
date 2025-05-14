"""This module handles account data for the botcoin application."""

import uuid
from dataclasses import dataclass, field

from botcoin.data.finnhub.client import FinnhubClient


@dataclass(kw_only=True, slots=True, order=True)
class Stock:
    """
    Represents a stock in the account.
    """

    symbol: str
    quantity: int
    open_price: float

    def serialize(self) -> dict:
        """
        Converts the stock to a JSON-compatible dictionary.
        """
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "open_price": self.open_price,
        }


@dataclass(kw_only=True, slots=True, order=True)
class Account:
    """
    Represents a trading account.
    This account can hold cash and stocks.
    """

    cash: float = 0.0
    reserved_cash: float = 0.0
    stocks: dict[str, Stock] = field(default_factory=dict)
    account_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def value(self) -> float:
        """
        Returns the total value of the account, including cash and stocks.
        """
        total_value = self.cash + self.reserved_cash
        finnhub_client = FinnhubClient()
        for stock in self.stocks.values():
            current_price = finnhub_client.quote_sync(stock.symbol)["c"]
            total_value += stock.quantity * current_price
        return total_value

    def increase_cash(self, amount: float) -> None:
        """
        Increases the cash balance of the account.
        """
        if amount < 0:
            raise ValueError("Amount must be positive")
        self.cash += amount

    def decrease_cash(self, amount: float) -> None:
        """
        Decreases the cash balance of the account.
        """
        if amount < 0:
            raise ValueError("Amount must be positive")
        if amount > self.cash:
            raise ValueError(
                f"Insufficient cash balance, current balance: {self.cash}, requested: {amount}."
            )
        self.cash -= amount

    def buy_stock(self, stock: Stock) -> None:
        """
        Adds a stock to the account.
        If the stock already exists, it updates the quantity and open price.
        """
        # Check have enough cash to buy the stock
        if stock.open_price <= 0:
            raise ValueError("Stock price must be greater than zero")
        if stock.quantity <= 0:
            raise ValueError("Stock quantity must be greater than zero")
        if not self.can_deduct_cash(stock.quantity * stock.open_price):
            raise ValueError(
                f"Insufficient cash balance, current balance: {self.cash}, "
                + f"requested: {stock.quantity * stock.open_price}."
            )
        if stock.symbol in self.stocks:
            existing_stock = self.stocks[stock.symbol]
            existing_stock.quantity += stock.quantity
            existing_stock.open_price = (
                existing_stock.open_price * existing_stock.quantity
                + stock.open_price * stock.quantity
            ) / (existing_stock.quantity + stock.quantity)
        else:
            self.stocks[stock.symbol] = stock
        self.cash -= stock.quantity * stock.open_price

    def sell_stock(self, symbol: str, quantity: int, price: float) -> None:
        """
        Trades certain quantity of a stock for a given price.
        """
        # Check if the stock exists in the account
        if symbol not in self.stocks:
            raise ValueError(f"Stock {symbol} not found in account")

        # Check if the quantity is valid
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")

        # Check if the price is valid
        if price <= 0:
            raise ValueError("Price must be greater than zero")

        # Check if the stock quantity is sufficient
        existing_stock = self.stocks[symbol]
        if quantity > existing_stock.quantity:
            raise ValueError(
                f"Insufficient stock quantity, available: {existing_stock.quantity}, "
                + f"requested: {quantity}."
            )

        existing_stock.quantity -= quantity
        if existing_stock.quantity == 0:
            del self.stocks[symbol]
        self.cash += quantity * price

    def can_deduct_cash(self, amount: float) -> bool:
        """
        Checks if the account can deduct the specified amount of cash.
        """
        return amount <= self.cash

    def reserve_cash(self, amount: float) -> None:
        """
        Reserves a certain amount of cash in the account.
        """
        if amount < 0:
            raise ValueError("Amount must be positive")
        if amount > self.cash:
            raise ValueError(
                f"Insufficient cash balance, current balance: {self.cash}, requested: {amount}."
            )
        self.reserved_cash += amount
        self.cash -= amount

    def release_reserved_cash(self, amount: float) -> None:
        """
        Releases a certain amount of reserved cash in the account.
        """
        if amount < 0:
            raise ValueError("Amount must be positive")
        if amount > self.reserved_cash:
            raise ValueError(
                "Insufficient reserved cash balance, current reserved balance: "
                + f"{self.reserved_cash}, requested: {amount}."
            )
        self.reserved_cash -= amount
        self.cash += amount

    def get_cash_balance(self) -> float:
        """
        Returns the current cash balance of the account.
        """
        return self.cash

    def get_reserved_cash(self) -> float:
        """
        Returns the current reserved cash balance of the account.
        """
        return self.reserved_cash

    def get_stocks(self) -> dict[str, Stock]:
        """
        Returns the stocks in the account.
        """
        return self.stocks

    def get_stock(self, symbol: str) -> Stock:
        """
        Returns the stock with the specified symbol from the account.
        """
        return self.stocks.get(symbol, None)

    def get_id(self) -> str:
        """
        Returns the account ID.
        """
        return self.account_id

    def serialize(self) -> dict:
        """
        Converts the account to a JSON-compatible dictionary.
        """
        return {
            "account_id": self.account_id,
            "cash": self.cash,
            "reserved_cash": self.reserved_cash,
            "stocks": {symbol: stock.serialize() for symbol, stock in self.stocks.items()},
            "total_value": self.value,
        }
