import unittest
from datetime import datetime
from botcoin.data.dataclasses import PriceTick


class TestPriceTick(unittest.TestCase):

    def setUp(self):
        self.symbol = "AAPL"
        self.price = 178.52
        self.timestamp = datetime(2024, 4, 20, 15, 30)

    def test_keyword_only_instantiation(self):
        tick = PriceTick(
            symbol=self.symbol,
            price=self.price,
            timestamp=self.timestamp
        )
        self.assertEqual(tick.symbol, self.symbol)
        self.assertEqual(tick.price, self.price)
        self.assertEqual(tick.timestamp, self.timestamp)

    def test_positional_args_raise_typeerror(self):
        with self.assertRaises(TypeError):
            # Positional arguments not allowed due to kw_only=True
            PriceTick(self.symbol, self.price, self.timestamp)

    def test_immutable(self):
        tick = PriceTick(
            symbol=self.symbol,
            price=self.price,
            timestamp=self.timestamp
        )
        with self.assertRaises(Exception):  # FrozenInstanceError is a subclass of AttributeError
            tick.price = 200.00

