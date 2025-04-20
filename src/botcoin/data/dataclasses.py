from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import pytz

US_EASTERN = pytz.timezone("US/Eastern")

@dataclass(frozen=True, kw_only=True, slots=True, order=True)
class PriceTick:
    symbol: str
    price: float
    timestamp: datetime


class OrderState(Enum):
    NOT_TRADED = "not_traded"
    TRADED = "traded"
    CANCELLED = "cancelled"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    OCO = "oco"

@dataclass(kw_only=True)
class TradeOrder:
    trade_type: OrderType   # Type of order (market, limit, OCO)
    direction: str          # 'buy' or 'sell'
    quantity: int           # Number of units being traded
    state: OrderState = OrderState.NOT_TRADED   # State of the order (not_traded, traded, cancelled)
    traded_price: Optional[float] = None        # Price at which the order was executed (None if not traded)

    def __post_init__(self):
        if self.trade_type not in OrderType:
            raise ValueError(f"Invalid order type: {self.trade_type}")
        if self.direction not in ["buy", "sell"]:
            raise ValueError(f"Invalid direction: {self.direction}")
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be greater than zero: {self.quantity}")

@dataclass(kw_only=True)
class MarketOrder(TradeOrder):
    trade_type: OrderType = OrderType.MARKET
    price: Optional[float] = None  # No price for market orders

@dataclass(kw_only=True)
class LimitOrder(TradeOrder):
    trade_type: OrderType = OrderType.LIMIT
    price: float

@dataclass(kw_only=True)
class OcoOrder(TradeOrder):
    trade_type: OrderType = OrderType.OCO
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

