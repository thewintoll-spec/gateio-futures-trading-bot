"""
하이브리드 전략 (Hybrid Adaptive Strategy)

핵심 아이디어:
- ADX로 시장 상태 판단
- 약한 추세/횡보장 (ADX < 25) → RSI 평균회귀 전략
- 강한 추세장 (ADX >= 25) → 추세추종 전략
- 자동으로 최적 전략 선택

장점:
- 모든 시장 환경에 대응 가능
- 각 전략의 장점만 활용
"""
import numpy as np
from datetime import datetime, timedelta


class HybridStrategy:
    """
    하이브리드 적응형 전략

    시장 환경에 따라 자동 전략 전환:
    - 횡보장: RSI 평균회귀
    - 추세장: 추세추종
    """

    def __init__(self, adx_threshold=25, rsi_period=14, ema_fast=12, ema_slow=26):
        """
        Args:
            adx_threshold: ADX 임계값 (이상이면 추세장)
            rsi_period: RSI 기간
            ema_fast: 빠른 EMA
            ema_slow: 느린 EMA
        """
        self.adx_threshold = adx_threshold
        self.rsi_period = rsi_period
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.period = max(rsi_period, ema_slow, 14) + 1

        # 거래 제어
        self.last_trade_time = None
        self.min_trade_interval = 900  # 15분

        # 손실 관리
        self.consecutive_losses = 0
        self.cooldown_until = None

        # 전략 사용 통계
        self.rsi_trades = 0
        self.trend_trades = 0

    def calculate_rsi(self, prices):
        """RSI 계산"""
        if len(prices) < self.rsi_period + 1:
            return None

        prices = np.array(prices)
        deltas = np.diff(prices)

        gains = deltas.copy()
        losses = deltas.copy()

        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)

        avg_gain = np.mean(gains[-self.rsi_period:])
        avg_loss = np.mean(losses[-self.rsi_period:])

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_ema(self, prices, period):
        """EMA 계산"""
        if len(prices) < period:
            return None

        prices = np.array(prices)
        ema = np.zeros(len(prices))
        ema[period-1] = np.mean(prices[:period])

        multiplier = 2 / (period + 1)

        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]

        return ema[-1]

    def calculate_adx(self, candles, period=14):
        """ADX 계산"""
        if len(candles) < period + 1:
            return None

        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        closes = np.array([c['close'] for c in candles])

        high_diff = np.diff(highs)
        low_diff = -np.diff(lows)

        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)

        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        atr = np.mean(tr[-period:])

        if atr == 0:
            return None

        plus_di = 100 * np.mean(plus_dm[-period:]) / atr
        minus_di = 100 * np.mean(minus_dm[-period:]) / atr

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0

        return dx

    def calculate_atr_percent(self, candles, period=14):
        """ATR 퍼센트 계산"""
        if len(candles) < period + 1:
            return 2.0

        highs = np.array([c['high'] for c in candles[-period-1:]])
        lows = np.array([c['low'] for c in candles[-period-1:]])
        closes = np.array([c['close'] for c in candles[-period-1:]])

        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        atr = np.mean(tr)
        current_price = closes[-1]

        atr_pct = (atr / current_price) * 100
        return atr_pct

    def get_tp_sl_rsi(self):
        """RSI 전략 TP/SL (보수적)"""
        return 3.0, 2.0

    def get_tp_sl_trend(self, atr_pct):
        """추세추종 TP/SL (공격적)"""
        take_profit = max(4.0, min(12.0, atr_pct * 3.0))
        stop_loss = max(2.0, min(4.0, atr_pct * 1.5))
        return round(take_profit, 1), round(stop_loss, 1)

    def update_trade_result(self, result):
        """거래 결과 업데이트"""
        now = datetime.now()

        if result == 'loss':
            self.consecutive_losses += 1
            if self.consecutive_losses >= 3:
                self.cooldown_until = now + timedelta(hours=1)
                print(f"  [휴식 모드] 3연속 손실 - 1시간 거래 중지")
        else:
            self.consecutive_losses = 0

    def is_in_cooldown(self):
        """휴식 모드 확인"""
        if self.cooldown_until is None:
            return False

        now = datetime.now()
        if now < self.cooldown_until:
            remaining = (self.cooldown_until - now).total_seconds() / 60
            print(f"  [휴식 모드] 남은 시간: {remaining:.0f}분")
            return True
        else:
            self.cooldown_until = None
            return False

    def analyze(self, candles):
        """
        하이브리드 신호 생성

        Returns:
            dict: {'signal': 'long'/'short', 'take_profit': float, 'stop_loss': float}
        """
        if not candles or len(candles) < self.period:
            return None

        if self.is_in_cooldown():
            return None

        closes = [c['close'] for c in candles]

        # ADX 계산 (시장 상태 판단)
        adx = self.calculate_adx(candles, 14)
        if adx is None:
            return None

        # 거래 빈도 제어
        current_time = candles[-1].get('timestamp', candles[-1].get('datetime'))
        if self.last_trade_time:
            if isinstance(current_time, (int, float)):
                time_diff = current_time - self.last_trade_time
            else:
                time_diff = (current_time - self.last_trade_time).total_seconds()

            if time_diff < self.min_trade_interval:
                return None

        # ===== 시장 상태 판단 =====
        is_trending = adx >= self.adx_threshold

        if is_trending:
            # 추세장 → 추세추종 전략
            signal = self._trend_following_signal(closes, candles, adx)
            if signal:
                self.trend_trades += 1
                strategy_name = "추세추종"
        else:
            # 횡보장 → RSI 평균회귀 전략
            signal = self._rsi_mean_reversion_signal(closes, adx)
            if signal:
                self.rsi_trades += 1
                strategy_name = "RSI평균회귀"

        if signal:
            self.last_trade_time = current_time
            total_trades = self.rsi_trades + self.trend_trades
            rsi_pct = (self.rsi_trades / total_trades * 100) if total_trades > 0 else 0
            trend_pct = (self.trend_trades / total_trades * 100) if total_trades > 0 else 0
            print(f"  [전략 통계] RSI: {self.rsi_trades}회({rsi_pct:.0f}%), "
                  f"추세: {self.trend_trades}회({trend_pct:.0f}%)")

        return signal

    def _rsi_mean_reversion_signal(self, closes, adx):
        """RSI 평균회귀 신호 (횡보장용)"""
        rsi = self.calculate_rsi(closes)
        if rsi is None:
            return None

        tp, sl = self.get_tp_sl_rsi()

        print(f"ADX: {adx:.1f} (횡보장), RSI: {rsi:.1f}")

        # 과매도 → 롱
        if rsi < 30:
            print(f"  [RSI LONG] 과매도 반등 노림, TP: {tp}%, SL: {sl}%")
            return {'signal': 'long', 'take_profit': tp, 'stop_loss': sl}

        # 과매수 → 숏
        elif rsi > 70:
            print(f"  [RSI SHORT] 과매수 조정 노림, TP: {tp}%, SL: {sl}%")
            return {'signal': 'short', 'take_profit': tp, 'stop_loss': sl}

        return None

    def _trend_following_signal(self, closes, candles, adx):
        """추세추종 신호 (추세장용)"""
        fast_ema = self.calculate_ema(closes, self.ema_fast)
        slow_ema = self.calculate_ema(closes, self.ema_slow)

        if fast_ema is None or slow_ema is None:
            return None

        atr_pct = self.calculate_atr_percent(candles, 14)
        tp, sl = self.get_tp_sl_trend(atr_pct)

        ema_diff_pct = (fast_ema - slow_ema) / slow_ema * 100

        print(f"ADX: {adx:.1f} (추세장), EMA12: {fast_ema:.2f}, EMA26: {slow_ema:.2f}, "
              f"Diff: {ema_diff_pct:+.2f}%")

        # 상승 추세 → 롱
        if fast_ema > slow_ema and ema_diff_pct > 0.1:
            print(f"  [TREND LONG] 상승 추세 추종, TP: {tp}%, SL: {sl}%")
            return {'signal': 'long', 'take_profit': tp, 'stop_loss': sl}

        # 하락 추세 → 숏
        elif fast_ema < slow_ema and ema_diff_pct < -0.1:
            print(f"  [TREND SHORT] 하락 추세 추종, TP: {tp}%, SL: {sl}%")
            return {'signal': 'short', 'take_profit': tp, 'stop_loss': sl}

        return None


if __name__ == "__main__":
    print("하이브리드 적응형 전략 (Hybrid Adaptive Strategy)")
    print("\n핵심 로직:")
    print("- ADX >= 25 (추세장) → 추세추종 전략")
    print("  - EMA 크로스오버")
    print("  - TP: ATR의 3배 (4-12%)")
    print("  - SL: ATR의 1.5배 (2-4%)")
    print("")
    print("- ADX < 25 (횡보장) → RSI 평균회귀 전략")
    print("  - RSI < 30 → 롱")
    print("  - RSI > 70 → 숏")
    print("  - TP: 3%, SL: 2%")
    print("")
    print("레버리지 권장: 3배")
