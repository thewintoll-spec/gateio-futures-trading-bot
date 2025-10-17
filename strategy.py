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
        self.period = slow_period  # For backtest compatibility

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


class BollingerBandStrategy:
    """Bollinger Band Mean Reversion Strategy - Good for ranging markets"""

    def __init__(self, period=20, std_dev=2):
        """
        Initialize Bollinger Band strategy

        Args:
            period: BB calculation period
            std_dev: Number of standard deviations
        """
        self.period = period
        self.std_dev = std_dev

    def calculate_bb(self, prices):
        """Calculate Bollinger Bands"""
        if len(prices) < self.period:
            return None, None, None

        prices_array = np.array(prices[-self.period:])
        sma = np.mean(prices_array)
        std = np.std(prices_array)

        upper = sma + (self.std_dev * std)
        lower = sma - (self.std_dev * std)

        return upper, sma, lower

    def analyze(self, candles):
        """
        Analyze market data and generate signals
        Buy when price touches lower band (oversold)
        Sell when price touches upper band (overbought)

        Returns:
            Signal: 'long', 'short', or None
        """
        if not candles or len(candles) < self.period:
            return None

        closes = [c['close'] for c in candles]
        current_price = closes[-1]

        upper, middle, lower = self.calculate_bb(closes)

        if upper is None:
            return None

        print(f"BB: Upper={upper:.2f}, Middle={middle:.2f}, Lower={lower:.2f}, Price={current_price:.2f}")

        # Mean reversion signals
        if current_price <= lower:
            return 'long'  # Price at lower band - buy
        elif current_price >= upper:
            return 'short'  # Price at upper band - sell

        return None


class AdaptiveStrategy:
    """Adaptive strategy that switches based on market regime"""

    def __init__(self):
        """Initialize adaptive strategy with multiple sub-strategies"""
        from market_regime import RegimeDetector

        self.detector = RegimeDetector(adx_period=14, adx_threshold=25)

        # Strategies for different market conditions
        self.trending_strategy = MovingAverageCrossStrategy(fast_period=20, slow_period=50)
        self.ranging_strategy = BollingerBandStrategy(period=20, std_dev=2)

        # For backtest compatibility
        self.period = 50  # Use the longest period needed

        self.last_regime = None

    def analyze(self, candles):
        """
        Analyze market and generate signals based on detected regime

        Returns:
            Signal: 'long', 'short', or None
        """
        if not candles or len(candles) < self.period:
            return None

        # Detect market regime
        regime_result = self.detector.detect_regime(candles)

        if regime_result is None:
            return None

        regime, adx, bb_width = regime_result

        # Print regime change
        if regime != self.last_regime:
            print(f"\n[Regime Change] {self.last_regime or 'Unknown'} -> {regime.upper()}")
            print(f"  ADX: {adx:.2f}, BB Width: {bb_width:.4f}")
            self.last_regime = regime

        # Select strategy based on regime
        if regime == 'trending':
            # Use trend-following strategy (MA Cross)
            signal = self.trending_strategy.analyze(candles)
            if signal:
                print(f"[Adaptive] Using MA Cross (Trending market)")
            return signal
        else:  # ranging
            # Use mean-reversion strategy (Bollinger Bands)
            signal = self.ranging_strategy.analyze(candles)
            if signal:
                print(f"[Adaptive] Using Bollinger Bands (Ranging market)")
            return signal
