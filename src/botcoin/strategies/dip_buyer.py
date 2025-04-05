import pandas as pd
from botcoin.cost.simple import SimpleTradeCost


class DipBuyerStrategy:
    """
    A class to implement a dip buying strategy for stock trading.
    """

    def __init__(self, threshold: int = 3, trade_amount: float = 0.1, stop_gain: float = 0.01):
        """
        Initialize the DipBuyer with a threshold for dip buying.

        :param threshold: Number of consecutive days the stock price must be lower than the previous close to consider it a dip.
        :type threshold: int
        :param trade_amount: The amount to trade when a dip is detected.
        :type trade_amount: float
        """
        self.threshold = threshold
        self.trade_amount = trade_amount
        self.stop_gain = stop_gain
        self.convertion_cost = SimpleTradeCost(cost_percentage=0.007)

    def trade(self, balance: float, open: float, high: float, close: float) -> dict:
        """
        This simulates a trade. Assuming we buy at the open price and sell at close price or stop gain.
        """
        amount = balance * self.trade_amount
        stop_gain = open * self.stop_gain
        if high > stop_gain:
            # Calculate profit/loss
            delta = (high - open) / open
        else:
            # If stop gain is not reached, we sell at close price
            delta = (close - open) / open

        # Update balance with the profit/loss from the trade
        balance += amount * delta

        # Calculate the cost of the trade
        cost: float = 0
        cost += self.convertion_cost.calculate_cost(amount)
        balance -= cost


        is_winning = str((delta - self.convertion_cost.cost_percentage) > 0)
        record = {
            "trade_amount": amount,
            "is_winning": is_winning,
            "balance": balance,
        }

        return record
    
    def get_history_tradeable_records(self, ticker_data: pd.DataFrame) -> list[dict]:
        """
        Get the historical tradeable records for a given ticker.
        This function identifies the dips in the historical data based on the open and close prices.
        """
        records = []

        # Initialize variables for tracking dips
        curr: int = 0
        count: int = 0
        is_bought: bool = False

        # Iterate through the historical data to identify dips
        for _, row in ticker_data.iterrows():
            if is_bought:
                # If we have already bought, skip to the next iteration
                is_bought = False
                continue
            if row["Open"] < row["Close"]:
                count += 1
            else:
                if count == self.threshold:
                    # buy logic here
                    is_bought = True

                    # Execute trade and record the result
                    next_row = ticker_data.iloc[curr + 1]
                    rec = next_row.to_dict()
                    rec.update({'date': next_row.name})
                    records.append(rec)

                # Reset the count and start index
                count = 0

            curr += 1
           
        return records

    def history_replay(self, trades: list[dict]) -> tuple[float, list[dict], float]:
        """
        Replay the historical data for a given ticker between start and end dates.

        :param trades: A list of dictionaries containing the historical data for the ticker.
        :type trades: list[dict]
        each dictionary should contain the keys "Open", "High", "Low", and "Close".
        """

        # Initialize starting balance and trade record
        balance: float = 1
        records: list = []

        # Iterate through the historical data to identify dips
        for rec in trades:
            record = self.trade(balance, rec["Open"], rec["High"], rec["Close"])
            balance = record["balance"]
            records.append(record)

        win_rate = len([x for x in records if x["is_winning"] == "True"]) / len(records) if records else 0
        return balance, records, win_rate
