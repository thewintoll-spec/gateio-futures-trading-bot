"""
Market Regime Detection Module
"""
import numpy as np
import pandas as pd


class RegimeDetector:
    """Detect market regime (trending vs ranging)"""

    def __init__(self, adx_period=14, adx_threshold=25, bb_period=20, bb_threshold=0.05):
        """
        Initialize regime detector

        Args:
            adx_period: Period for ADX calculation
            adx_threshold: ADX threshold (>25 = trending, <25 = ranging)
            bb_period: Period for Bollinger Bands
            bb_threshold: BB width threshold (relative to price)
        """
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.bb_period = bb_period
        self.bb_threshold = bb_threshold

    def calculate_adx(self, candles):
        """
        Calculate ADX (Average Directional Index)
        ADX measures trend strength (0-100)
        >25 = strong trend, <20 = weak/ranging
        """
        if len(candles) < self.adx_period + 1:
            return None

        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        closes = np.array([c['close'] for c in candles])

        # Calculate True Range (TR)
        high_low = highs[1:] - lows[1:]
        high_close = np.abs(highs[1:] - closes[:-1])
        low_close = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(high_low, np.maximum(high_close, low_close))

        # Calculate Directional Movement
        high_diff = highs[1:] - highs[:-1]
        low_diff = lows[:-1] - lows[1:]

        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)

        # Smooth with Wilder's method (EMA with alpha = 1/period)
        alpha = 1.0 / self.adx_period

        # Initialize
        atr = np.zeros(len(tr))
        plus_di = np.zeros(len(tr))
        minus_di = np.zeros(len(tr))

        atr[self.adx_period-1] = np.mean(tr[:self.adx_period])
        plus_di[self.adx_period-1] = np.mean(plus_dm[:self.adx_period])
        minus_di[self.adx_period-1] = np.mean(minus_dm[:self.adx_period])

        # Smooth
        for i in range(self.adx_period, len(tr)):
            atr[i] = atr[i-1] * (1 - alpha) + tr[i] * alpha
            plus_di[i] = plus_di[i-1] * (1 - alpha) + plus_dm[i] * alpha
            minus_di[i] = minus_di[i-1] * (1 - alpha) + minus_dm[i] * alpha

        # Calculate DI+, DI-
        plus_di_pct = 100 * plus_di / atr
        minus_di_pct = 100 * minus_di / atr

        # Calculate DX
        dx = 100 * np.abs(plus_di_pct - minus_di_pct) / (plus_di_pct + minus_di_pct + 1e-10)

        # Calculate ADX (smoothed DX)
        adx = np.zeros(len(dx))
        adx[self.adx_period-1] = np.mean(dx[:self.adx_period])

        for i in range(self.adx_period, len(dx)):
            adx[i] = adx[i-1] * (1 - alpha) + dx[i] * alpha

        return adx[-1]

    def calculate_bb_width(self, candles):
        """
        Calculate Bollinger Band width (relative to price)
        High width = high volatility
        Low width = low volatility (ranging)
        """
        if len(candles) < self.bb_period:
            return None

        closes = np.array([c['close'] for c in candles[-self.bb_period:]])

        sma = np.mean(closes)
        std = np.std(closes)

        # Width as percentage of price
        width = (2 * std) / sma

        return width

    def calculate_atr(self, candles, period=14):
        """
        Calculate ATR (Average True Range)
        Measures volatility
        """
        if len(candles) < period + 1:
            return None

        highs = np.array([c['high'] for c in candles[-period-1:]])
        lows = np.array([c['low'] for c in candles[-period-1:]])
        closes = np.array([c['close'] for c in candles[-period-1:]])

        high_low = highs[1:] - lows[1:]
        high_close = np.abs(highs[1:] - closes[:-1])
        low_close = np.abs(lows[1:] - closes[:-1])

        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = np.mean(tr)

        return atr

    def detect_regime(self, candles):
        """
        Detect market regime

        Returns:
            'trending': Strong directional movement
            'ranging': Sideways/choppy market
            None: Not enough data
        """
        if len(candles) < max(self.adx_period + 1, self.bb_period):
            return None

        adx = self.calculate_adx(candles)
        bb_width = self.calculate_bb_width(candles)

        if adx is None or bb_width is None:
            return None

        # Decision logic
        # High ADX = trending
        # Low ADX + Low BB width = ranging

        if adx > self.adx_threshold:
            regime = 'trending'
        else:
            regime = 'ranging'

        return regime, adx, bb_width

    def get_trend_direction(self, candles, ma_period=50):
        """
        Determine trend direction using moving average

        Returns:
            'bullish': Price above MA
            'bearish': Price below MA
            None: Not enough data
        """
        if len(candles) < ma_period:
            return None

        closes = np.array([c['close'] for c in candles])
        ma = np.mean(closes[-ma_period:])
        current_price = closes[-1]

        if current_price > ma:
            return 'bullish'
        else:
            return 'bearish'


if __name__ == "__main__":
    print("Market regime detector ready")
