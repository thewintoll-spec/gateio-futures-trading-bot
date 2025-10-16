"""
Trading Strategy Module
"""
import numpy as np
import pandas as pd


class RSIStrategy:
    """Simple RSI-based trading strategy"""

    def __init__(self, period=14, oversold=30, overbought=70):
        """
        Initialize RSI strategy

        Args:
            period: RSI calculation period
            oversold: RSI oversold threshold
            overbought: RSI overbought threshold
        """
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def calculate_rsi(self, prices):
        """
        Calculate RSI indicator

        Args:
            prices: List of closing prices

        Returns:
            RSI value (0-100)
        """
        if len(prices) < self.period + 1:
            return None

        prices = np.array(prices)
        deltas = np.diff(prices)

        gains = deltas.copy()
        losses = deltas.copy()

        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)

        avg_gain = np.mean(gains[-self.period:])
        avg_loss = np.mean(losses[-self.period:])

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def analyze(self, candles):
        """
        Analyze market data and generate signals

        Args:
            candles: List of candlestick data

        Returns:
            Signal: 'long', 'short', or None
        """
        if not candles or len(candles) < self.period + 1:
            return None

        # Extract closing prices
        closes = [c['close'] for c in candles]

        # Calculate RSI
        rsi = self.calculate_rsi(closes)

        if rsi is None:
            return None

        print(f"Current RSI: {rsi:.2f}")

        # Generate signals
        if rsi < self.oversold:
            return 'long'  # Oversold - Buy signal
        elif rsi > self.overbought:
            return 'short'  # Overbought - Sell signal

        return None


class MovingAverageCrossStrategy:
    """Moving Average Crossover Strategy"""

    def __init__(self, fast_period=10, slow_period=30):
        """
        Initialize MA Cross strategy

        Args:
            fast_period: Fast MA period
            slow_period: Slow MA period
        """
        self.fast_period = fast_period
        self.slow_period = slow_period

    def calculate_ma(self, prices, period):
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return None
        return np.mean(prices[-period:])

    def analyze(self, candles):
        """
        Analyze market data and generate signals

        Returns:
            Signal: 'long', 'short', or None
        """
        if not candles or len(candles) < self.slow_period:
            return None

        closes = [c['close'] for c in candles]

        fast_ma = self.calculate_ma(closes, self.fast_period)
        slow_ma = self.calculate_ma(closes, self.slow_period)

        if fast_ma is None or slow_ma is None:
            return None

        # Calculate previous MAs to detect crossover
        if len(closes) > self.slow_period:
            prev_fast_ma = self.calculate_ma(closes[:-1], self.fast_period)
            prev_slow_ma = self.calculate_ma(closes[:-1], self.slow_period)

            print(f"Fast MA: {fast_ma:.2f}, Slow MA: {slow_ma:.2f}")

            # Golden cross - bullish
            if prev_fast_ma <= prev_slow_ma and fast_ma > slow_ma:
                return 'long'

            # Death cross - bearish
            if prev_fast_ma >= prev_slow_ma and fast_ma < slow_ma:
                return 'short'

        return None
