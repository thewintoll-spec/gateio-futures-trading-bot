# -*- coding: utf-8 -*-
"""
Adaptive Multi-Regime Strategy

Strategy Logic:
- Detect market regime and switch strategies
- Ranging: Grid Trading
- Uptrend: Trend Following (Long Only)
- Downtrend: Trend Following (Short Only) or Wait

Features:
- Auto regime detection based on ADX
- Dynamic strategy switching
- Optimized for each market condition
"""
import numpy as np
from grid_strategy import GridTradingStrategy
from trend_following_strategy import TrendFollowingStrategy


class AdaptiveStrategy:
    """
    Adaptive Multi-Regime Strategy

    Logic:
    1. Detect market regime with ADX (ranging/trending)
    2. Ranging -> Grid Trading
    3. Uptrend -> Trend Following (Long)
    4. Downtrend -> Trend Following (Short) or Wait
    """

    def __init__(self, adx_threshold=25, allow_short_in_downtrend=True):
        """
        Args:
            adx_threshold: ADX threshold (default 25)
            allow_short_in_downtrend: Allow short in downtrend (default True)
        """
        self.adx_threshold = adx_threshold
        self.allow_short_in_downtrend = allow_short_in_downtrend

        # Initialize sub-strategies
        self.grid_strategy = GridTradingStrategy(
            num_grids=30,
            range_pct=10.0,
            profit_per_grid=0.3,
            max_positions=10,
            rebalance_threshold=7.0,
            tight_sl=True,
            use_trend_filter=True,
            dynamic_sl=True,
            use_regime_filter=False  # Adaptive handles regime detection
        )

        self.trend_strategy = TrendFollowingStrategy(
            fast_ema=12,
            slow_ema=26,
            adx_threshold=25,
            trailing_stop_atr=2.0,
            min_profit_before_trail=1.0
        )

        # Current state
        self.current_regime = None
        self.current_strategy = None

        # Required period
        self.period = max(self.grid_strategy.period, self.trend_strategy.period)

    def calculate_adx(self, candles, period=14):
        """Calculate ADX"""
        if len(candles) < period + 1:
            return 0, 0, 0

        highs = np.array([c['high'] for c in candles[-(period+1):]])
        lows = np.array([c['low'] for c in candles[-(period+1):]])
        closes = np.array([c['close'] for c in candles[-(period+1):]])

        # True Range
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        # Directional Movement
        up_move = highs[1:] - highs[:-1]
        down_move = lows[:-1] - lows[1:]

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        # Smoothed
        atr = np.mean(tr)
        plus_dm_smooth = np.mean(plus_dm)
        minus_dm_smooth = np.mean(minus_dm)

        # DI
        plus_di = (plus_dm_smooth / atr * 100) if atr > 0 else 0
        minus_di = (minus_dm_smooth / atr * 100) if atr > 0 else 0

        # ADX
        di_sum = plus_di + minus_di
        di_diff = abs(plus_di - minus_di)
        dx = (di_diff / di_sum * 100) if di_sum > 0 else 0
        adx = dx

        return adx, plus_di, minus_di

    def detect_market_regime(self, candles):
        """
        Detect market regime

        Returns:
            'ranging': Ranging market
            'trending_up': Uptrend
            'trending_down': Downtrend
        """
        adx, plus_di, minus_di = self.calculate_adx(candles, 14)

        # ADX < threshold: Ranging
        if adx < self.adx_threshold:
            return 'ranging', adx, plus_di, minus_di

        # ADX >= threshold: Trending
        # Check +DI vs -DI for direction
        if plus_di > minus_di:
            return 'trending_up', adx, plus_di, minus_di
        else:
            return 'trending_down', adx, plus_di, minus_di

    def analyze(self, candles):
        """
        Adaptive strategy analysis

        Detect market regime and delegate to appropriate strategy

        Returns:
            dict: {'signal': 'long'/'short'/'close', 'take_profit': float, 'stop_loss': float}
            or None
        """
        if not candles or len(candles) < self.period:
            return None

        # Detect market regime
        regime, adx, plus_di, minus_di = self.detect_market_regime(candles)

        # Log regime changes
        if regime != self.current_regime:
            print(f"\n{'='*60}")
            print(f"[REGIME CHANGE] {self.current_regime} -> {regime}")
            print(f"  ADX: {adx:.1f}, +DI: {plus_di:.1f}, -DI: {minus_di:.1f}")
            print(f"{'='*60}")
            self.current_regime = regime

        # ===== Ranging: Grid Trading =====
        if regime == 'ranging':
            print(f"[ADAPTIVE] Ranging Market (ADX: {adx:.1f}) - Grid Trading")
            self.current_strategy = 'grid'
            return self.grid_strategy.analyze(candles)

        # ===== Uptrend: Trend Following (Long Only) =====
        elif regime == 'trending_up':
            print(f"[ADAPTIVE] Uptrend (ADX: {adx:.1f}) - Trend Following (Long)")
            self.current_strategy = 'trend_long'
            return self.trend_strategy.analyze(candles, direction='long')

        # ===== Downtrend: Short or Wait =====
        elif regime == 'trending_down':
            if self.allow_short_in_downtrend:
                print(f"[ADAPTIVE] Downtrend (ADX: {adx:.1f}) - Trend Following (Short)")
                self.current_strategy = 'trend_short'
                return self.trend_strategy.analyze(candles, direction='short')
            else:
                print(f"[ADAPTIVE] Downtrend (ADX: {adx:.1f}) - Waiting (No Short)")
                self.current_strategy = 'wait'
                return None

        return None

    def get_current_strategy(self):
        """Get current active strategy"""
        return self.current_strategy

    def get_current_regime(self):
        """Get current market regime"""
        return self.current_regime


if __name__ == "__main__":
    print("Adaptive Multi-Regime Strategy")
    print("\nStrategy Logic:")
    print("- ADX < 25: Ranging -> Grid Trading")
    print("- ADX >= 25 & +DI > -DI: Uptrend -> Trend Following (Long)")
    print("- ADX >= 25 & +DI < -DI: Downtrend -> Trend Following (Short)")
    print("\nFeatures:")
    print("- Auto regime detection")
    print("- Dynamic strategy switching")
    print("- Optimized for each market condition")
    print("- Best of both worlds")
    print("\nRecommended Period: 20+ (for indicator stability)")
