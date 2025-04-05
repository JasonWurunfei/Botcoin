import pandas as pd
from botcoin.cost.simple import SimpleTradeCost


class DipBuyerStrategy:
    """
    A class to implement a dip buying strategy for stock trading.
    """

    def __init__(self, threshold: int = 3, trade_amount: float = 0.1):
        """
        Initialize the DipBuyer with a threshold for dip buying.

        :param threshold: Number of consecutive days the stock price must be lower than the previous close to consider it a dip.
        :type threshold: int
        :param trade_amount: The amount to trade when a dip is detected.
        :type trade_amount: float
        """
        self.threshold = threshold
        self.trade_amount = trade_amount
        self.convertion_cost = SimpleTradeCost(cost_percentage=0.007)  # 0.5% trade cost

    def history_replay(self, ticker_data: pd.DataFrame):
        """
        Replay the historical data for a given ticker between start and end dates.

        :param ticker_data: The historical data for the ticker.
        :type ticker_data: pd.DataFrame
        """

        # Initialize variables for tracking dips
        curr: int = 0
        count: int = 0
        is_bought: bool = False

        # Initialize starting balance and trade record
        balance: float = 1
        record: list = []

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
                    next_row = ticker_data.iloc[curr + 1]
                    delta = (next_row["High"] - next_row["Open"]) / next_row["Open"]
                    amount = balance * self.trade_amount
                    balance -= amount # Deduct the trade amount from balance
                    balance += amount * (1 + delta) # Update balance with the profit/loss from the trade

                    # Calculate the cost of the trade
                    cost: float = 0
                    cost += self.convertion_cost.calculate_cost(amount) # Calculate the trade cost
                    balance -= cost # Deduct the trade cost from balance

                    # Record the trade details
                    record.append(
                        {
                            "date": str(next_row.name.to_pydatetime()),
                            "trade_amount": amount,
                            "winning": str(delta > 0),
                            "profit": delta,
                            "balance": balance,
                            "cost": cost,
                        }
                    )

                # Reset the count and start index
                count = 0

            curr += 1

        return balance, record

