# -*- coding: utf-8 -*-
"""
Trend Following Strategy

Strategy Logic:
- Follow trends using EMA crossover
- Long in uptrends, Short in downtrends
- Use trailing stop to protect profits

Indicators:
- EMA (Exponential Moving Average)
- ADX (Average Directional Index)
- ATR (Average True Range)

Entry:
- Golden Cross + ADX > 25 -> Long
- Death Cross + ADX > 25 -> Short

Exit:
- EMA reversal crossover
- ATR-based trailing stop
"""
import numpy as np


class TrendFollowingStrategy:
    """
    Trend Following Strategy

    Logic:
    1. Detect EMA crossover for trend direction
    2. Confirm with ADX for trend strength
    3. Enter in direction of strong trend
    4. Use trailing stop to protect profits
    """

    def __init__(self, fast_ema=12, slow_ema=26, adx_threshold=25,
                 trailing_stop_atr=2.0, min_profit_before_trail=1.0):
        """
        Args:
            fast_ema: Fast EMA period (default 12)
            slow_ema: Slow EMA period (default 26)
            adx_threshold: ADX threshold (default 25)
            trailing_stop_atr: Trailing stop ATR multiplier (default 2.0)
            min_profit_before_trail: Min profit % before trailing (default 1.0%)
        """
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.adx_threshold = adx_threshold
        self.trailing_stop_atr = trailing_stop_atr
        self.min_profit_before_trail = min_profit_before_trail

        # Position tracking
        self.position = None  # {'side': 'long/short', 'entry_price': float, 'highest': float, 'lowest': float}

        # Required period
        self.period = max(slow_ema, 26)

    def calculate_ema(self, data, period):
        """Calculate EMA"""
        if len(data) < period:
            return None

        # Simple EMA calculation (exponential weights)
        weights = np.exp(np.linspace(-1., 0., period))
        weights /= weights.sum()

        ema = np.convolve(data, weights, mode='valid')
        return ema[-1] if len(ema) > 0 else None

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

        atr = np.mean(tr)
        return atr

    def analyze(self, candles, direction='both'):
        """
        Trend following analysis

        Args:
            candles: candle data
            direction: 'both', 'long', 'short'

        Returns:
            dict: {'signal': 'long'/'short'/'close', 'take_profit': float, 'stop_loss': float}
            or None
        """
        if not candles or len(candles) < self.slow_ema + 1:
            return None

        # Current price
        current_price = candles[-1]['close']

        # Calculate EMAs
        closes = np.array([c['close'] for c in candles])
        fast_ema = self.calculate_ema(closes, self.fast_ema)
        slow_ema = self.calculate_ema(closes, self.slow_ema)

        if fast_ema is None or slow_ema is None:
            return None

        # Previous EMAs
        if len(candles) < self.slow_ema + 2:
            return None

        closes_prev = np.array([c['close'] for c in candles[:-1]])
        fast_ema_prev = self.calculate_ema(closes_prev, self.fast_ema)
        slow_ema_prev = self.calculate_ema(closes_prev, self.slow_ema)

        # Calculate ADX
        adx, plus_di, minus_di = self.calculate_adx(candles, 14)

        # Calculate ATR
        atr = self.calculate_atr(candles, 14)
        atr_pct = (atr / current_price * 100)

        # Golden Cross (fast EMA crosses above slow EMA)
        golden_cross = (fast_ema_prev <= slow_ema_prev) and (fast_ema > slow_ema)

        # Death Cross (fast EMA crosses below slow EMA)
        death_cross = (fast_ema_prev >= slow_ema_prev) and (fast_ema < slow_ema)

        # ===== Entry Signals =====

        # Long Entry
        if golden_cross and adx >= self.adx_threshold and direction in ['both', 'long']:
            print(f"\n[TREND LONG] Golden Cross + Strong Trend")
            print(f"  Fast EMA: {fast_ema:.2f}, Slow EMA: {slow_ema:.2f}")
            print(f"  ADX: {adx:.1f}, +DI: {plus_di:.1f}, -DI: {minus_di:.1f}")

            # Stop Loss: ATR multiplier
            sl_pct = atr_pct * 2.0

            # Take Profit: 2x stop loss
            tp_pct = sl_pct * 2.0

            self.position = {
                'side': 'long',
                'entry_price': current_price,
                'highest': current_price,
                'lowest': current_price
            }

            return {
                'signal': 'long',
                'take_profit': tp_pct,
                'stop_loss': sl_pct,
                'reason': 'golden_cross'
            }

        # Short Entry
        elif death_cross and adx >= self.adx_threshold and direction in ['both', 'short']:
            print(f"\n[TREND SHORT] Death Cross + Strong Trend")
            print(f"  Fast EMA: {fast_ema:.2f}, Slow EMA: {slow_ema:.2f}")
            print(f"  ADX: {adx:.1f}, +DI: {plus_di:.1f}, -DI: {minus_di:.1f}")

            # Stop Loss: ATR multiplier
            sl_pct = atr_pct * 2.0

            # Take Profit: 2x stop loss
            tp_pct = sl_pct * 2.0

            self.position = {
                'side': 'short',
                'entry_price': current_price,
                'highest': current_price,
                'lowest': current_price
            }

            return {
                'signal': 'short',
                'take_profit': tp_pct,
                'stop_loss': sl_pct,
                'reason': 'death_cross'
            }

        # ===== Position Management (Trailing Stop) =====

        if self.position:
            side = self.position['side']
            entry_price = self.position['entry_price']

            # Update highest/lowest prices
            self.position['highest'] = max(self.position['highest'], current_price)
            self.position['lowest'] = min(self.position['lowest'], current_price)

            # Current PnL
            if side == 'long':
                pnl_pct = (current_price - entry_price) / entry_price * 100

                # Exit on reversal crossover
                if death_cross:
                    print(f"\n[TREND EXIT] Death Cross - Close Long")
                    self.position = None
                    return {
                        'signal': 'close',
                        'reason': 'trend_reversal'
                    }

                # Trailing stop (after min profit)
                if pnl_pct >= self.min_profit_before_trail:
                    trail_stop_price = self.position['highest'] - (atr * self.trailing_stop_atr)
                    if current_price <= trail_stop_price:
                        print(f"\n[TREND EXIT] Trailing Stop - Close Long (PnL: {pnl_pct:.2f}%)")
                        self.position = None
                        return {
                            'signal': 'close',
                            'reason': 'trailing_stop'
                        }

            elif side == 'short':
                pnl_pct = (entry_price - current_price) / entry_price * 100

                # Exit on reversal crossover
                if golden_cross:
                    print(f"\n[TREND EXIT] Golden Cross - Close Short")
                    self.position = None
                    return {
                        'signal': 'close',
                        'reason': 'trend_reversal'
                    }

                # Trailing stop
                if pnl_pct >= self.min_profit_before_trail:
                    trail_stop_price = self.position['lowest'] + (atr * self.trailing_stop_atr)
                    if current_price >= trail_stop_price:
                        print(f"\n[TREND EXIT] Trailing Stop - Close Short (PnL: {pnl_pct:.2f}%)")
                        self.position = None
                        return {
                            'signal': 'close',
                            'reason': 'trailing_stop'
                        }

        return None


if __name__ == "__main__":
    print("Trend Following Strategy")
    print("\nStrategy Logic:")
    print("- Golden Cross: fast EMA > slow EMA -> Long")
    print("- Death Cross: fast EMA < slow EMA -> Short")
    print("- ADX > 25: Strong trend confirmation")
    print("- Trailing Stop: Protect profits")
    print("\nFeatures:")
    print("- Works best in trending markets")
    print("- Clear entry/exit signals")
    print("- Dynamic profit protection")
    print("\nRecommended Period: 20+ (for EMA stability)")
