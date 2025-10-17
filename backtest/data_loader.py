"""
Historical Data Loader for Backtesting
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchange import GateioFutures
import pandas as pd
from datetime import datetime, timedelta
import time


class DataLoader:
    """Load historical candlestick data from Gate.io"""

    def __init__(self, symbol, testnet=True):
        """
        Initialize data loader

        Args:
            symbol: Trading pair (e.g., 'ETH_USDT')
            testnet: Use testnet or mainnet
        """
        self.symbol = symbol
        self.exchange = GateioFutures(testnet=testnet)

    def fetch_historical_data(self, interval='5m', days=30):
        """
        Fetch historical candlestick data

        Args:
            interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            days: Number of days to fetch

        Returns:
            pandas DataFrame with OHLCV data
        """
        print(f"Fetching {days} days of {interval} data for {self.symbol}...")

        all_candles = []

        # Gate.io API limit is usually 1000 candles per request
        limit = 1000

        # Calculate how many requests we need
        interval_minutes = self._interval_to_minutes(interval)
        candles_per_day = (24 * 60) / interval_minutes
        total_candles = int(candles_per_day * days)
        num_requests = (total_candles // limit) + 1

        print(f"Estimated {total_candles} candles, {num_requests} requests needed")

        for i in range(num_requests):
            try:
                candles = self.exchange.get_candlesticks(
                    self.symbol,
                    interval=interval,
                    limit=limit
                )

                if not candles:
                    print(f"No more data available after {i} requests")
                    break

                all_candles.extend(candles)
                print(f"Request {i+1}/{num_requests}: Fetched {len(candles)} candles")

                # Respect rate limits
                if i < num_requests - 1:
                    time.sleep(0.2)

            except Exception as e:
                print(f"Error fetching data: {e}")
                break

        if not all_candles:
            return None

        # Convert to DataFrame
        df = pd.DataFrame(all_candles)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.sort_values('datetime')
        df = df.drop_duplicates(subset=['datetime'])
        df = df.reset_index(drop=True)

        # Limit to requested days
        cutoff_date = df['datetime'].max() - timedelta(days=days)
        df = df[df['datetime'] >= cutoff_date]

        print(f"Total candles loaded: {len(df)}")
        print(f"Date range: {df['datetime'].min()} to {df['datetime'].max()}")

        return df

    def _interval_to_minutes(self, interval):
        """Convert interval string to minutes"""
        unit = interval[-1]
        value = int(interval[:-1])

        if unit == 'm':
            return value
        elif unit == 'h':
            return value * 60
        elif unit == 'd':
            return value * 60 * 24
        else:
            return 5  # default

    def save_to_csv(self, df, filename=None):
        """Save DataFrame to CSV file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/{self.symbol}_{timestamp}.csv"

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
        return filename

    def load_from_csv(self, filename):
        """Load DataFrame from CSV file"""
        df = pd.read_csv(filename)
        df['datetime'] = pd.to_datetime(df['datetime'])
        print(f"Data loaded from {filename}: {len(df)} candles")
        return df


if __name__ == "__main__":
    # Test data loader
    loader = DataLoader('ETH_USDT', testnet=True)
    df = loader.fetch_historical_data(interval='5m', days=7)

    if df is not None:
        print("\nFirst few rows:")
        print(df.head())
        print("\nLast few rows:")
        print(df.tail())

        # Save to CSV
        loader.save_to_csv(df)
