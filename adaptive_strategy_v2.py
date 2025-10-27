# -*- coding: utf-8 -*-
"""
Adaptive Multi-Regime Strategy V2 - Anti-Whipsaw Edition

Improvements:
1. ADX strength classification (weak/strong trend)
2. Trend confirmation with EMA + price position
3. False breakout detection
4. Consecutive loss protection
5. Volatility filter (ATR-based)
"""
import numpy as np
from grid_strategy import GridTradingStrategy
from trend_following_strategy import TrendFollowingStrategy


class AdaptiveStrategyV2:
    """
    Adaptive Multi-Regime Strategy V2

    Anti-Whipsaw Features:
    - Strong ADX requirement for trend (35+ instead of 25+)
    - EMA confirmation required
    - Price must be above/below EMA
    - Recent candle direction check
    - ATR volatility filter
    """

    def __init__(
        self,
        adx_threshold=35,  # Increased from 25 to 35
        adx_strong=45,     # Strong trend threshold
        allow_short_in_downtrend=True,
        ema_period=20,
        atr_multiplier=2.5
    ):
        """
        Args:
            adx_threshold: Minimum ADX for trend (default 35)
            adx_strong: Strong trend threshold (default 45)
            allow_short_in_downtrend: Allow short in downtrend (default True)
            ema_period: EMA period for trend confirmation (default 20)
            atr_multiplier: ATR multiplier for volatility filter (default 2.5)
        """
        self.adx_threshold = adx_threshold
        self.adx_strong = adx_strong
        self.allow_short_in_downtrend = allow_short_in_downtrend
        self.ema_period = ema_period
        self.atr_multiplier = atr_multiplier

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
            use_regime_filter=False
        )

        self.trend_strategy = TrendFollowingStrategy(
            fast_ema=12,
            slow_ema=26,
            adx_threshold=35,  # Increased
            trailing_stop_atr=2.0,
            min_profit_before_trail=1.0
        )

        # Current state
        self.current_regime = None
        self.current_strategy = None

        # Loss tracking
        self.recent_losses = []
        self.max_consecutive_losses = 3

        # Required period
        self.period = max(
            self.grid_strategy.period,
            self.trend_strategy.period,
            self.ema_period + 14  # EMA + ADX
        )

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

    def calculate_ema(self, candles, period):
        """Calculate EMA"""
        if len(candles) < period:
            return None

        closes = np.array([c['close'] for c in candles[-period:]])
        ema = closes[0]
        multiplier = 2 / (period + 1)

        for close in closes[1:]:
            ema = (close - ema) * multiplier + ema

        return ema

    def calculate_atr(self, candles, period=14):
        """Calculate ATR"""
        if len(candles) < period + 1:
            return 0

        highs = np.array([c['high'] for c in candles[-(period+1):]])
        lows = np.array([c['low'] for c in candles[-(period+1):]])
        closes = np.array([c['close'] for c in candles[-(period+1):]])

        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        return np.mean(tr)

    def check_trend_confirmation(self, candles, direction):
        """
        Check trend confirmation

        Requirements:
        1. Price above/below EMA
        2. Recent candles align with direction
        3. EMA slope in correct direction

        Returns:
            bool: True if trend confirmed
        """
        if len(candles) < self.ema_period + 5:
            return False

        current_price = candles[-1]['close']
        ema = self.calculate_ema(candles, self.ema_period)

        if ema is None:
            return False

        # Check 1: Price position
        if direction == 'long':
            if current_price <= ema:
                return False
        else:  # short
            if current_price >= ema:
                return False

        # Check 2: Recent 3 candles direction
        recent_closes = [c['close'] for c in candles[-4:]]

        if direction == 'long':
            # Expecting upward movement
            up_count = sum(1 for i in range(1, 4) if recent_closes[i] > recent_closes[i-1])
            if up_count < 2:  # At least 2 out of 3 up
                return False
        else:  # short
            # Expecting downward movement
            down_count = sum(1 for i in range(1, 4) if recent_closes[i] < recent_closes[i-1])
            if down_count < 2:  # At least 2 out of 3 down
                return False

        # Check 3: EMA slope
        prev_ema = self.calculate_ema(candles[:-5], self.ema_period)
        if prev_ema is None:
            return True  # Can't check, assume OK

        ema_slope = (ema - prev_ema) / prev_ema * 100

        if direction == 'long':
            if ema_slope < 0:  # EMA going down
                return False
        else:  # short
            if ema_slope > 0:  # EMA going up
                return False

        return True

    def check_volatility_filter(self, candles):
        """
        Check if volatility is too high

        Returns:
            bool: True if OK to trade, False if too volatile
        """
        atr = self.calculate_atr(candles, 14)
        current_price = candles[-1]['close']

        # ATR as percentage of price
        atr_pct = (atr / current_price * 100) if current_price > 0 else 0

        # If ATR > 3%, too volatile
        if atr_pct > 3.0:
            return False

        return True

    def check_consecutive_losses(self):
        """
        Check if too many recent losses

        Returns:
            bool: True if OK to trade, False if too many losses
        """
        if len(self.recent_losses) < self.max_consecutive_losses:
            return True

        # Check last N trades
        last_n = self.recent_losses[-self.max_consecutive_losses:]

        # If all losses, stop trading
        if all(loss for loss in last_n):
            return False

        return True

    def record_trade_result(self, is_loss):
        """Record trade result for loss tracking"""
        self.recent_losses.append(is_loss)

        # Keep only last 10
        if len(self.recent_losses) > 10:
            self.recent_losses = self.recent_losses[-10:]

    def detect_market_regime(self, candles):
        """
        Detect market regime with improved logic

        Returns:
            tuple: (regime, adx, plus_di, minus_di, strength)
            regime: 'ranging' / 'trending_up' / 'trending_down'
            strength: 'weak' / 'strong'
        """
        adx, plus_di, minus_di = self.calculate_adx(candles, 14)

        # ADX < threshold: Ranging
        if adx < self.adx_threshold:
            return 'ranging', adx, plus_di, minus_di, 'none'

        # ADX >= threshold: Trending
        # Classify strength
        strength = 'strong' if adx >= self.adx_strong else 'weak'

        # Check direction
        if plus_di > minus_di:
            return 'trending_up', adx, plus_di, minus_di, strength
        else:
            return 'trending_down', adx, plus_di, minus_di, strength

    def analyze(self, candles):
        """
        Adaptive strategy analysis with anti-whipsaw filters

        Returns:
            dict: {'signal': 'long'/'short'/'close', 'take_profit': float, 'stop_loss': float, 'regime': str}
            or None
        """
        if not candles or len(candles) < self.period:
            return None

        # Check consecutive losses
        if not self.check_consecutive_losses():
            print(f"[ADAPTIVE V2] Too many consecutive losses, waiting...")
            return None

        # Detect market regime
        regime, adx, plus_di, minus_di, strength = self.detect_market_regime(candles)

        # Log regime changes
        if regime != self.current_regime:
            print(f"\n{'='*60}")
            print(f"[REGIME CHANGE] {self.current_regime} -> {regime}")
            print(f"  ADX: {adx:.1f} ({strength}), +DI: {plus_di:.1f}, -DI: {minus_di:.1f}")
            print(f"{'='*60}")
            self.current_regime = regime

        # ===== Ranging: Grid Trading =====
        if regime == 'ranging':
            print(f"[ADAPTIVE V2] Ranging (ADX: {adx:.1f}) - Grid Trading")
            self.current_strategy = 'grid'
            signal = self.grid_strategy.analyze(candles)
            if signal:
                signal['regime'] = 'ranging'
            return signal

        # ===== Trending: Check filters =====

        # Filter 1: Volatility too high?
        if not self.check_volatility_filter(candles):
            print(f"[ADAPTIVE V2] High volatility detected, waiting...")
            return None

        # ===== Uptrend =====
        if regime == 'trending_up':
            # For weak trends, require confirmation
            if strength == 'weak':
                if not self.check_trend_confirmation(candles, 'long'):
                    print(f"[ADAPTIVE V2] Weak uptrend (ADX: {adx:.1f}), no confirmation - SKIP")
                    return None

            print(f"[ADAPTIVE V2] Uptrend (ADX: {adx:.1f}, {strength}) - Trend Following (Long)")
            self.current_strategy = 'trend_long'
            signal = self.trend_strategy.analyze(candles, direction='long')
            if signal:
                signal['regime'] = f'trending_up_{strength}'
            return signal

        # ===== Downtrend =====
        elif regime == 'trending_down':
            if not self.allow_short_in_downtrend:
                print(f"[ADAPTIVE V2] Downtrend (ADX: {adx:.1f}) - Waiting (No Short)")
                self.current_strategy = 'wait'
                return None

            # For weak trends, require confirmation
            if strength == 'weak':
                if not self.check_trend_confirmation(candles, 'short'):
                    print(f"[ADAPTIVE V2] Weak downtrend (ADX: {adx:.1f}), no confirmation - SKIP")
                    return None

            print(f"[ADAPTIVE V2] Downtrend (ADX: {adx:.1f}, {strength}) - Trend Following (Short)")
            self.current_strategy = 'trend_short'
            signal = self.trend_strategy.analyze(candles, direction='short')
            if signal:
                signal['regime'] = f'trending_down_{strength}'
            return signal

        return None

    def get_current_strategy(self):
        """Get current active strategy"""
        return self.current_strategy

    def get_current_regime(self):
        """Get current market regime"""
        return self.current_regime


if __name__ == "__main__":
    print("Adaptive Multi-Regime Strategy V2 - Anti-Whipsaw Edition")
    print("\nImprovements:")
    print("1. ADX threshold increased: 25 -> 35")
    print("2. Strong trend requirement: ADX 45+")
    print("3. Trend confirmation required for weak trends:")
    print("   - Price above/below EMA")
    print("   - Recent candles align with direction")
    print("   - EMA slope in correct direction")
    print("4. Volatility filter: ATR < 3%")
    print("5. Consecutive loss protection: Max 3 losses")
    print("\nExpected Results:")
    print("- Fewer false signals")
    print("- Higher win rate")
    print("- Better Sharpe ratio")
    print("- Less whipsaw in choppy markets")
