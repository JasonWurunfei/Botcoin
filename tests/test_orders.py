import unittest
from botcoin.data.dataclasses import TradeOrder, MarketOrder, LimitOrder, OcoOrder, OrderType, OrderState

class TestTradeOrders(unittest.TestCase):

    def test_create_market_order(self):
        order = MarketOrder(direction="buy", quantity=100)
        self.assertEqual(order.trade_type, OrderType.MARKET)
        self.assertEqual(order.direction, "buy")
        self.assertEqual(order.quantity, 100)
        self.assertEqual(order.state, OrderState.NOT_TRADED)
        self.assertIsNone(order.traded_price)
        self.assertIsNone(order.price)

    def test_create_limit_order(self):
        order = LimitOrder(direction="sell", quantity=50, price=150.25)
        self.assertEqual(order.trade_type, OrderType.LIMIT)
        self.assertEqual(order.direction, "sell")
        self.assertEqual(order.quantity, 50)
        self.assertEqual(order.state, OrderState.NOT_TRADED)
        self.assertIsNone(order.traded_price)
        self.assertEqual(order.price, 150.25)

    def test_create_oco_order(self):
        order = OcoOrder(direction="buy", quantity=200, limit_price=155.50, stop_price=152.00)
        self.assertEqual(order.trade_type, OrderType.OCO)
        self.assertEqual(order.direction, "buy")
        self.assertEqual(order.quantity, 200)
        self.assertEqual(order.state, OrderState.NOT_TRADED)
        self.assertIsNone(order.traded_price)
        self.assertEqual(order.limit_price, 155.50)
        self.assertEqual(order.stop_price, 152.00)

    def test_default_order_state(self):
        order = TradeOrder(trade_type=OrderType.LIMIT, direction="buy", quantity=100)
        self.assertEqual(order.state, OrderState.NOT_TRADED)

    def test_order_state_after_trade(self):
        order = TradeOrder(trade_type=OrderType.LIMIT, direction="buy", quantity=100, state=OrderState.TRADED)
        self.assertEqual(order.state, OrderState.TRADED)

    def test_invalid_order_type(self):
        with self.assertRaises(ValueError):
            TradeOrder(trade_type="invalid_type", direction="buy", quantity=100)

    def test_invalid_direction(self):
        with self.assertRaises(ValueError):
            # Invalid direction (should be 'buy' or 'sell')
            TradeOrder(trade_type=OrderType.MARKET, direction="invalid_direction", quantity=100)

    def test_invalid_quantity(self):
        with self.assertRaises(ValueError):
            # Invalid quantity (should be > 0)
            TradeOrder(trade_type=OrderType.LIMIT, direction="buy", quantity=0)

        with self.assertRaises(ValueError):
            # Invalid quantity (should be > 0)
            TradeOrder(trade_type=OrderType.LIMIT, direction="buy", quantity=-10)

    def test_invalid_limit_order_price(self):
        with self.assertRaises(TypeError):
            LimitOrder(direction="sell", quantity=50)  # price is missing

    def test_oco_order_with_missing_price(self):
        order = OcoOrder(direction="sell", quantity=100)
        self.assertIsNone(order.limit_price)
        self.assertIsNone(order.stop_price)

    def test_order_type_enum(self):
        # Ensure the Enum values are being used correctly
        self.assertEqual(OrderType.MARKET.value, "market")
        self.assertEqual(OrderType.LIMIT.value, "limit")
        self.assertEqual(OrderType.OCO.value, "oco")
        self.assertEqual(OrderState.NOT_TRADED.value, "not_traded")
