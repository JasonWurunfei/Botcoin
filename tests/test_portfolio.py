import unittest

from botcoin.data.dataclasses.portfolio import Stock, Portfolio


class TestStock(unittest.TestCase):
    def setUp(self):
        self.stock = Stock(symbol="AAPL", currency="USD")

    def test_quantity_empty(self):
        self.assertEqual(self.stock.quantity, 0)

    def test_quantity_with_entries(self):
        self.stock.add_entry(symbol="AAPL", open_price=100.0, quantity=2)
        self.stock.add_entry(symbol="AAPL", open_price=110.0, quantity=3)
        self.assertEqual(self.stock.quantity, 5)

    def test_average_open_price_empty(self):
        self.assertEqual(self.stock.average_open_price, 0.0)

    def test_average_open_price_weighted(self):
        # Weighted avg = (100*2 + 110*3) / 5 = 106.0
        self.stock.add_entry(symbol="AAPL", open_price=100.0, quantity=2)
        self.stock.add_entry(symbol="AAPL", open_price=110.0, quantity=3)
        self.assertEqual(self.stock.average_open_price, 106.0)

    def test_average_open_price_rounding(self):
        # (10*1 + 11*2) / 3 = 10.666... -> 10.67
        self.stock.add_entry(symbol="AAPL", open_price=10.0, quantity=1)
        self.stock.add_entry(symbol="AAPL", open_price=11.0, quantity=2)
        self.assertEqual(self.stock.average_open_price, 10.67)

    def test_total_invested(self):
        self.stock.add_entry(symbol="AAPL", open_price=100.0, quantity=2)
        self.stock.add_entry(symbol="AAPL", open_price=110.0, quantity=3)
        self.assertEqual(self.stock.total_invested, 100.0 * 2 + 110.0 * 3)

    def test_add_entry_symbol_mismatch_raises(self):
        with self.assertRaises(ValueError):
            self.stock.add_entry(symbol="MSFT", open_price=100.0, quantity=1)

    def test_remove_more_than_owned_raises(self):
        self.stock.add_entry(symbol="AAPL", open_price=100.0, quantity=2)
        with self.assertRaises(ValueError):
            self.stock.remove(quantity=3)

    def test_remove_exact_one_lot(self):
        self.stock.add_entry(symbol="AAPL", open_price=100.0, quantity=2)
        self.stock.remove(quantity=2)
        self.assertEqual(self.stock.quantity, 0)
        self.assertEqual(len(self.stock.entries), 0)

    def test_remove_across_multiple_lots(self):
        # Start with 2 + 3 = 5, remove 4 => remaining 1 (from the last lot)
        self.stock.add_entry(symbol="AAPL", open_price=100.0, quantity=2)
        self.stock.add_entry(symbol="AAPL", open_price=110.0, quantity=3)

        self.stock.remove(quantity=4)

        self.assertEqual(self.stock.quantity, 1)
        self.assertEqual(len(self.stock.entries), 1)
        self.assertEqual(self.stock.entries[0].open_price, 110.0)
        self.assertEqual(self.stock.entries[0].quantity, 1)

    def test_remove_partial_first_lot(self):
        # Start with 5 in one lot, remove 2 => remaining 3 in same entry
        self.stock.add_entry(symbol="AAPL", open_price=100.0, quantity=5)
        self.stock.remove(quantity=2)

        self.assertEqual(self.stock.quantity, 3)
        self.assertEqual(len(self.stock.entries), 1)
        self.assertEqual(self.stock.entries[0].quantity, 3)


class TestPortfolio(unittest.TestCase):
    def setUp(self):
        self.p = Portfolio(cash=1000.0, reserved_cash=50.0)

    def test_invested_value_empty(self):
        self.assertEqual(self.p.invested_value, 0.0)

    def test_invested_value_with_stocks(self):
        s1 = Stock(symbol="AAPL", currency="USD")
        s1.add_entry(symbol="AAPL", open_price=100.0, quantity=2)  # 200
        s2 = Stock(symbol="MSFT", currency="USD")
        s2.add_entry(symbol="MSFT", open_price=50.0, quantity=3)  # 150
        self.p.stocks = {"AAPL": s1, "MSFT": s2}

        self.assertEqual(self.p.invested_value, 350.0)

    def test_buy_stock_quantity_must_be_positive(self):
        with self.assertRaises(ValueError):
            self.p.buy_stock(symbol="AAPL", quantity=0, open_price=10.0)
        with self.assertRaises(ValueError):
            self.p.buy_stock(symbol="AAPL", quantity=-1, open_price=10.0)

    def test_buy_stock_insufficient_cash_raises(self):
        # would cost 2000 > cash 1000
        with self.assertRaises(ValueError):
            self.p.buy_stock(symbol="AAPL", quantity=20, open_price=100.0)

    def test_buy_stock_creates_stock_and_reduces_cash(self):
        self.p.buy_stock(symbol="AAPL", quantity=2, open_price=100.0)

        self.assertIn("AAPL", self.p.stocks)
        self.assertEqual(self.p.stocks["AAPL"].quantity, 2)
        self.assertEqual(self.p.stocks["AAPL"].average_open_price, 100.0)
        self.assertEqual(self.p.cash, 1000.0 - 200.0)

    def test_buy_stock_adds_to_existing_stock(self):
        self.p.buy_stock(symbol="AAPL", quantity=2, open_price=100.0)
        self.p.buy_stock(symbol="AAPL", quantity=3, open_price=110.0)

        s = self.p.stocks["AAPL"]
        self.assertEqual(s.quantity, 5)
        self.assertEqual(s.total_invested, 2 * 100.0 + 3 * 110.0)
        self.assertEqual(self.p.cash, 1000.0 - (2 * 100.0 + 3 * 110.0))

    def test_sell_stock_stock_not_found_raises(self):
        with self.assertRaises(ValueError):
            self.p.sell_stock(symbol="AAPL", quantity=1, sell_price=10.0)

    def test_sell_stock_quantity_must_be_positive(self):
        self.p.buy_stock(symbol="AAPL", quantity=2, open_price=100.0)

        with self.assertRaises(ValueError):
            self.p.sell_stock(symbol="AAPL", quantity=0, sell_price=10.0)
        with self.assertRaises(ValueError):
            self.p.sell_stock(symbol="AAPL", quantity=-1, sell_price=10.0)

    def test_sell_stock_insufficient_quantity_raises(self):
        self.p.buy_stock(symbol="AAPL", quantity=2, open_price=100.0)
        with self.assertRaises(ValueError):
            self.p.sell_stock(symbol="AAPL", quantity=3, sell_price=150.0)

    def test_sell_stock_reduces_quantity_increases_cash(self):
        self.p.buy_stock(symbol="AAPL", quantity=5, open_price=100.0)  # cash 500
        self.p.sell_stock(symbol="AAPL", quantity=2, sell_price=120.0)  # +240

        self.assertIn("AAPL", self.p.stocks)
        self.assertEqual(self.p.stocks["AAPL"].quantity, 3)
        self.assertEqual(self.p.cash, 500.0 + 240.0)

    def test_sell_stock_deletes_stock_when_zero(self):
        self.p.buy_stock(symbol="AAPL", quantity=2, open_price=100.0)  # cash 800
        self.p.sell_stock(symbol="AAPL", quantity=2, sell_price=90.0)  # +180

        self.assertNotIn("AAPL", self.p.stocks)
        self.assertEqual(self.p.cash, 800.0 + 180.0)
