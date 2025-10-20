"""
추세추종 전략 (Trend Following Strategy)

핵심 아이디어:
- RSI 평균회귀 대신 → 추세를 따라가기
- 상승 추세 → 롱
- 하락 추세 → 숏
- 추세가 꺾이면 청산

지표:
- EMA (지수이동평균) 크로스오버
- ADX (추세 강도)
- 가격 모멘텀
"""
import numpy as np
from datetime import datetime, timedelta


class TrendFollowingStrategy:
    """
    추세추종 전략

    핵심:
    - 빠른 EMA(12) > 느린 EMA(26) → 상승 추세 → 롱
    - 빠른 EMA(12) < 느린 EMA(26) → 하락 추세 → 숏
    - ADX로 추세 강도 확인 (약한 추세는 거래 안 함)
    """

    def __init__(self, fast_period=12, slow_period=26, adx_period=14, adx_threshold=25):
        """
        Args:
            fast_period: 빠른 EMA 기간
            slow_period: 느린 EMA 기간
            adx_period: ADX 기간
            adx_threshold: ADX 임계값 (이보다 높으면 추세 강함)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.period = max(fast_period, slow_period, adx_period) + 1

        # 거래 제어
        self.last_trade_time = None
        self.min_trade_interval = 900  # 15분 간격

        # 손실 관리
        self.consecutive_losses = 0
        self.cooldown_until = None

    def calculate_ema(self, prices, period):
        """EMA 계산 (지수이동평균)"""
        if len(prices) < period:
            return None

        prices = np.array(prices)
        ema = np.zeros(len(prices))

        # 첫 EMA는 SMA로 시작
        ema[period-1] = np.mean(prices[:period])

        # 지수 가중치
        multiplier = 2 / (period + 1)

        # 나머지 EMA 계산
        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]

        return ema[-1]

    def calculate_adx(self, candles, period=14):
        """
        ADX 계산 (Average Directional Index)

        추세 강도를 측정:
        - ADX < 20: 약한 추세 (횡보)
        - ADX 20-40: 중간 추세
        - ADX > 40: 강한 추세
        """
        if len(candles) < period + 1:
            return None

        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        closes = np.array([c['close'] for c in candles])

        # +DM, -DM 계산
        high_diff = np.diff(highs)
        low_diff = -np.diff(lows)

        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)

        # True Range 계산
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        # ATR (Average True Range)
        atr = np.mean(tr[-period:])

        if atr == 0:
            return None

        # +DI, -DI 계산
        plus_di = 100 * np.mean(plus_dm[-period:]) / atr
        minus_di = 100 * np.mean(minus_dm[-period:]) / atr

        # DX 계산
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0

        # ADX는 DX의 이동평균 (간단히 현재값 반환)
        return dx

    def calculate_momentum(self, prices, period=10):
        """가격 모멘텀 계산"""
        if len(prices) < period + 1:
            return 0

        current = prices[-1]
        past = prices[-period-1]
        momentum = (current - past) / past * 100
        return momentum

    def get_tp_sl(self, side, atr_pct):
        """
        동적 TP/SL (ATR 기반)

        추세추종은 큰 수익을 노림:
        - TP: ATR의 3배 (추세를 오래 타기)
        - SL: ATR의 1.5배 (빠른 손절)
        """
        # ATR 기반 배수
        tp_multiplier = 3.0
        sl_multiplier = 1.5

        # 최소/최대 제한
        take_profit = max(3.0, min(10.0, atr_pct * tp_multiplier))
        stop_loss = max(1.5, min(4.0, atr_pct * sl_multiplier))

        return round(take_profit, 1), round(stop_loss, 1)

    def calculate_atr_percent(self, candles, period=14):
        """ATR을 가격 대비 퍼센트로 계산"""
        if len(candles) < period + 1:
            return 2.0  # 기본값

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

    def update_trade_result(self, result):
        """거래 결과 업데이트"""
        now = datetime.now()

        if result == 'loss':
            self.consecutive_losses += 1
            print(f"  [손실] 연속 손실: {self.consecutive_losses}")

            # 3연속 손실 시 1시간 휴식
            if self.consecutive_losses >= 3:
                self.cooldown_until = now + timedelta(hours=1)
                print(f"  [휴식 모드] 3연속 손실 - 1시간 거래 중지")
        else:
            self.consecutive_losses = 0
            print(f"  [승리] 연속 손실 리셋")

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
            print(f"  [휴식 종료] 거래 재개")
            return False

    def analyze(self, candles):
        """
        추세추종 신호 생성

        Returns:
            dict: {'signal': 'long'/'short', 'take_profit': float, 'stop_loss': float}
            또는 None
        """
        if not candles or len(candles) < self.period:
            return None

        # 휴식 모드 체크
        if self.is_in_cooldown():
            return None

        closes = [c['close'] for c in candles]

        # EMA 계산
        fast_ema = self.calculate_ema(closes, self.fast_period)
        slow_ema = self.calculate_ema(closes, self.slow_period)

        if fast_ema is None or slow_ema is None:
            return None

        # ADX 계산 (추세 강도)
        adx = self.calculate_adx(candles, self.adx_period)
        if adx is None:
            return None

        # 모멘텀 계산
        momentum = self.calculate_momentum(closes, 10)

        # ATR 계산 (동적 TP/SL용)
        atr_pct = self.calculate_atr_percent(candles, 14)

        # 거래 빈도 제어
        current_time = candles[-1].get('timestamp', candles[-1].get('datetime'))
        if self.last_trade_time:
            if isinstance(current_time, (int, float)):
                time_diff = current_time - self.last_trade_time
            else:
                time_diff = (current_time - self.last_trade_time).total_seconds()

            if time_diff < self.min_trade_interval:
                return None

        # EMA 차이 (퍼센트)
        ema_diff_pct = (fast_ema - slow_ema) / slow_ema * 100

        print(f"EMA12: {fast_ema:.2f}, EMA26: {slow_ema:.2f}, Diff: {ema_diff_pct:+.2f}%, "
              f"ADX: {adx:.1f}, Mom: {momentum:+.2f}%")

        # ===== 롱 진입 조건 =====
        # 1. 빠른 EMA > 느린 EMA (상승 추세)
        # 2. ADX > 임계값 (추세가 충분히 강함)
        # 3. 모멘텀 > 0 (상승 모멘텀)
        if fast_ema > slow_ema and adx > self.adx_threshold and momentum > 0.5:
            tp, sl = self.get_tp_sl('long', atr_pct)
            print(f"  [LONG] 상승 추세, ADX: {adx:.1f}, TP: {tp}%, SL: {sl}%")
            self.last_trade_time = current_time
            return {'signal': 'long', 'take_profit': tp, 'stop_loss': sl}

        # ===== 숏 진입 조건 =====
        # 1. 빠른 EMA < 느린 EMA (하락 추세)
        # 2. ADX > 임계값 (추세가 충분히 강함)
        # 3. 모멘텀 < 0 (하락 모멘텀)
        elif fast_ema < slow_ema and adx > self.adx_threshold and momentum < -0.5:
            tp, sl = self.get_tp_sl('short', atr_pct)
            print(f"  [SHORT] 하락 추세, ADX: {adx:.1f}, TP: {tp}%, SL: {sl}%")
            self.last_trade_time = current_time
            return {'signal': 'short', 'take_profit': tp, 'stop_loss': sl}

        # 추세가 약하면 거래 안 함
        if adx < self.adx_threshold:
            print(f"  [SKIP] 약한 추세 (ADX: {adx:.1f} < {self.adx_threshold})")

        return None


if __name__ == "__main__":
    print("추세추종 전략 (Trend Following Strategy)")
    print("\n핵심 로직:")
    print("- EMA12 > EMA26 + 강한 ADX → LONG (상승 추세)")
    print("- EMA12 < EMA26 + 강한 ADX → SHORT (하락 추세)")
    print("- ADX < 25 → 거래 안 함 (약한 추세)")
    print("\nTP/SL:")
    print("- TP: ATR의 3배 (큰 수익 노림)")
    print("- SL: ATR의 1.5배 (빠른 손절)")
    print("\n레버리지 권장: 3배")
