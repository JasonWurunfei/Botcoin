import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd

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

    @patch("botcoin.data.dataclasses.portfolio.yf.Ticker")
    def test_market_value_success(self, mock_ticker_cls):
        # Setup: quantity = 4, closing price = 12.5 => market value = 50.0
        self.stock.add_entry(symbol="AAPL", open_price=100.0, quantity=4)

        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        hist_df = pd.DataFrame({"Close": [12.5]})
        mock_ticker.history.return_value = hist_df

        d = date(2025, 1, 2)
        mv = self.stock.market_value(d)

        self.assertEqual(mv, 50.0)
        mock_ticker_cls.assert_called_once_with("AAPL")
        mock_ticker.history.assert_called_once()  # details checked below if you want

        # If you want to assert exact args:
        _, kwargs = mock_ticker.history.call_args
        self.assertEqual(kwargs["start"], d)
        self.assertEqual(kwargs["end"], date(2025, 1, 3))

    @patch("botcoin.data.dataclasses.portfolio.yf.Ticker")
    def test_market_value_no_data_raises(self, mock_ticker_cls):
        self.stock.add_entry(symbol="AAPL", open_price=100.0, quantity=1)

        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        empty_df = pd.DataFrame()
        mock_ticker.history.return_value = empty_df

        with self.assertRaises(ValueError):
            self.stock.market_value(date(2025, 1, 2))


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

    def test_total_value_cash_only(self):
        d = date(2025, 1, 2)
        self.assertEqual(self.p.total_value(d), 1050.0)

    @patch("botcoin.data.dataclasses.portfolio.yf.Ticker")
    def test_total_value_with_yfinance_mock(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        mock_ticker.history.return_value = pd.DataFrame({"Close": [10.0]})

        self.p.buy_stock("AAPL", quantity=10, open_price=5.0)

        total = self.p.total_value(date(2025, 1, 2))

        # cash left = 1000 - 50 = 950, stock value = 100
        self.assertEqual(total, 950.0 + 50.0 + 100.0)

    @patch("botcoin.data.dataclasses.portfolio.yf.Ticker")
    def test_total_value_full_chain_two_stocks(self, mock_ticker_cls):
        # --- Arrange: make yfinance return different Close prices per symbol ---
        def ticker_factory(symbol: str):
            ticker = MagicMock(name=f"Ticker({symbol})")

            def history(*, start, end):
                # Ensure Portfolio->Stock passes correct date window (d to d+1)
                self.assertEqual(end, start + timedelta(days=1))

                if symbol == "AAPL":
                    return pd.DataFrame({"Close": [10.0]})  # AAPL close
                if symbol == "MSFT":
                    return pd.DataFrame({"Close": [20.0]})  # MSFT close

                return pd.DataFrame()  # unknown symbol => empty => should raise if used

            ticker.history.side_effect = history
            return ticker

        mock_ticker_cls.side_effect = ticker_factory

        # Portfolio with cash + reserved cash
        p = Portfolio(cash=1000.0, reserved_cash=50.0)

        # Buy 2 symbols (this uses real Portfolio.buy_stock and real Stock.add_entry)
        p.buy_stock("AAPL", quantity=3, open_price=5.0)  # costs 15, cash -> 985
        p.buy_stock("MSFT", quantity=2, open_price=10.0)  # costs 20, cash -> 965

        d = date(2025, 1, 2)

        # --- Act ---
        total = p.total_value(d)

        # --- Assert ---
        # cash + reserved = 965 + 50 = 1015
        # AAPL value = 3 * 10 = 30
        # MSFT value = 2 * 20 = 40
        # total = 1015 + 30 + 40 = 1085
        self.assertEqual(total, 1085.0)

        # yfinance called once per symbol during valuation
        self.assertEqual(mock_ticker_cls.call_count, 2)
        mock_ticker_cls.assert_any_call("AAPL")
        mock_ticker_cls.assert_any_call("MSFT")

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
