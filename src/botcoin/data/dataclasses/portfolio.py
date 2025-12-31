"""
Docstring for botcoin.data.dataclasses.portfolio
"""

from dataclasses import dataclass, field


@dataclass(kw_only=True, slots=True, order=True)
class Entry:
    """
    Represents a single entry of a stock in the portfolio.
    """

    symbol: str
    quantity: int
    open_price: float


@dataclass(kw_only=True, slots=True, order=True)
class Stock:
    """
    Represents a stock in the portfolio.
    """

    symbol: str
    currency: str
    entries: list[Entry] = field(default_factory=list)

    @property
    def quantity(self) -> int:
        """
        Returns the total quantity of the stock.
        """
        return sum(entry.quantity for entry in self.entries)

    @property
    def average_open_price(self) -> float:
        """
        Returns the average open price of the stock.
        """
        total_quantity = self.quantity
        if total_quantity == 0:
            return 0.0
        total_cost = sum(entry.open_price * entry.quantity for entry in self.entries)
        return round(total_cost / total_quantity, 2)

    @property
    def total_invested(self) -> float:
        """
        Returns the total invested amount in the stock.
        """
        return sum(entry.open_price * entry.quantity for entry in self.entries)

    def add_entry(self, symbol: str, open_price: float, quantity: int) -> None:
        """
        Adds an entry to the stock.
        """
        if symbol != self.symbol:
            raise ValueError("Entry symbol does not match stock symbol")
        entry = Entry(symbol=symbol, open_price=open_price, quantity=quantity)
        self.entries.append(entry)

    def remove(self, quantity: int) -> None:
        """
        Removes a quantity of the stock.
        """
        if quantity > self.quantity:
            raise ValueError("Insufficient stock quantity to remove")

        remaining_quantity = quantity
        new_entries = []
        for entry in self.entries:
            if remaining_quantity == 0:
                new_entries.append(entry)
                continue
            if entry.quantity <= remaining_quantity:
                remaining_quantity -= entry.quantity
            else:
                entry.quantity -= remaining_quantity
                new_entries.append(entry)
                remaining_quantity = 0
        self.entries = new_entries


@dataclass(kw_only=True, slots=True, order=True)
class Portfolio:
    """
    Represents a trading portfolio.
    """

    stocks: dict[str, Stock] = field(default_factory=dict)
    cash: float = 0.0
    reserved_cash: float = 0.0

    @property
    def invested_value(self) -> float:
        """
        Returns the total invested value in stocks.
        """
        return sum(stock.total_invested for stock in self.stocks.values())

    def buy_stock(self, symbol: str, quantity: int, open_price: float):
        """
        Buys a stock and adds it to the portfolio.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if quantity * open_price > self.cash:
            raise ValueError("Insufficient cash to buy stock")

        if symbol not in self.stocks:
            self.stocks[symbol] = Stock(symbol=symbol, currency="USD")
        self.stocks[symbol].add_entry(
            symbol=symbol,
            open_price=open_price,
            quantity=quantity,
        )
        self.cash -= open_price * quantity

    def sell_stock(self, symbol: str, quantity: int, sell_price: float):
        """
        Sells a stock from the portfolio.
        """
        if symbol not in self.stocks:
            raise ValueError("Stock not found in portfolio")
        stock = self.stocks[symbol]
        total_quantity = stock.quantity
        if quantity <= 0:
            raise ValueError(" Quantity must be positive")
        if quantity > total_quantity:
            raise ValueError("Insufficient stock quantity to sell")

        stock.remove(quantity=quantity)
        self.cash += sell_price * quantity
        if stock.quantity == 0:
            del self.stocks[symbol]
