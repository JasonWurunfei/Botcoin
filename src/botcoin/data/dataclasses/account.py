"""This module handles account data for the botcoin application."""

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class Stock:
    """
    Represents a stock in the account.
    """

    symbol: str
    quantity: int
    open_price: float


@dataclass(kw_only=True, slots=True, order=True)
class Account:
    """
    Represents a trading account.
    This account can hold cash and stocks.
    """

    cash: float = 0.0
    stocks: dict[str, Stock] = field(default_factory=dict)
    account_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def value(self) -> float:
        """
        Returns the total value of the account, including cash and stocks.
        """
        total_value = self.cash
        for stock in self.stocks.values():
            total_value += stock.quantity * stock.open_price
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
            raise ValueError("Insufficient cash balance")
        self.cash -= amount

    def add_stock(self, stock: Stock) -> None:
        """
        Adds a stock to the account.
        If the stock already exists, it updates the quantity and open price.
        """
        if stock.symbol in self.stocks:
            existing_stock = self.stocks[stock.symbol]
            existing_stock.quantity += stock.quantity
            existing_stock.open_price = (
                existing_stock.open_price * existing_stock.quantity
                + stock.open_price * stock.quantity
            ) / (existing_stock.quantity + stock.quantity)
        else:
            self.stocks[stock.symbol] = stock

    def trade_stock(self, stock: Stock, quantity: int, price: float) -> None:
        """
        Trades certain quantity of a stock for a given price.
        """
        # Check if the stock exists in the account
        if stock.symbol not in self.stocks:
            raise ValueError("Stock not found in account")

        # Check if the stock quantity is sufficient
        existing_stock = self.stocks[stock.symbol]
        if quantity > existing_stock.quantity:
            raise ValueError("Insufficient stock quantity")

        existing_stock.quantity -= quantity
        self.cash += quantity * price

    def can_deduct_cash(self, amount: float) -> bool:
        """
        Checks if the account can deduct the specified amount of cash.
        """
        return amount <= self.cash

    def get_cash_balance(self) -> float:
        """
        Returns the current cash balance of the account.
        """
        return self.cash

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
