"""
종합 개선 전략 (Ultimate RSI Strategy)

개선 사항:
1. 반전 청산 제거 - TP/SL만 사용
2. 레버리지 낮춤 (5x → 3x)
3. TP/SL 비율 최적화 (Risk:Reward = 1:1.5)
4. 추세 필터 추가 (강한 추세장에서는 거래 안 함)
5. 거래 빈도 제어 강화
"""
import numpy as np
from datetime import datetime, timedelta


class UltimateRSIStrategy:
    """
    종합 개선 RSI 전략

    핵심 개선:
    - 반전 청산 없음 (TP/SL만)
    - 추세 필터 (강한 추세장 회피)
    - 최적화된 TP/SL
    - 엄격한 진입 조건
    """

    def __init__(self, period=14, oversold=30, overbought=70):
        """
        Args:
            period: RSI 기간 (14로 늘림 - 더 안정적)
            oversold: 과매도 기준 (30으로 올림 - 더 보수적)
            overbought: 과매수 기준 (70으로 올림 - 더 보수적)
        """
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

        # 거래 제어
        self.last_trade_time = None
        self.min_trade_interval = 1800  # 30분 간격 (더 길게)

        # 손실 관리
        self.recent_trades = []
        self.consecutive_losses = 0
        self.cooldown_until = None

    def calculate_rsi(self, prices):
        """RSI 계산"""
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

    def calculate_trend_filter(self, prices, period=50):
        """
        추세 필터 - 강한 추세장 감지

        Returns:
            'strong_uptrend', 'strong_downtrend', 'neutral'
        """
        if len(prices) < period:
            return 'neutral'

        # 이동평균
        ma_short = np.mean(prices[-20:])
        ma_long = np.mean(prices[-period:])

        current_price = prices[-1]

        # 추세 강도 계산
        trend_pct = (ma_short - ma_long) / ma_long * 100

        # 가격이 이동평균 위에 있는지
        price_above_ma = current_price > ma_short

        # 강한 상승 추세 (위험 - RSI 롱 신호 무시)
        if trend_pct > 3 and price_above_ma:
            return 'strong_uptrend'

        # 강한 하락 추세 (위험 - RSI 숏 신호 무시)
        elif trend_pct < -3 and not price_above_ma:
            return 'strong_downtrend'

        return 'neutral'

    def calculate_volatility(self, prices, period=20):
        """변동성 계산"""
        if len(prices) < period:
            return 0.0

        returns = np.diff(prices[-period:]) / prices[-period:-1]
        volatility = np.std(returns) * 100
        return volatility

    def get_tp_sl(self):
        """
        고정 TP/SL (최적화된 비율)

        Risk:Reward = 1:1.5
        - SL: 2.0% (더 타이트)
        - TP: 3.0% (더 현실적)
        """
        stop_loss = 2.0
        take_profit = 3.0

        return take_profit, stop_loss

    def update_trade_result(self, result):
        """거래 결과 업데이트"""
        now = datetime.now()
        self.recent_trades.append((now, result))

        # 최근 10개만 유지
        if len(self.recent_trades) > 10:
            self.recent_trades.pop(0)

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
        신호 생성 (엄격한 조건)

        Returns:
            dict: {'signal': 'long'/'short', 'take_profit': float, 'stop_loss': float}
            또는 None
        """
        if not candles or len(candles) < max(self.period + 1, 50):
            return None

        # 휴식 모드 체크
        if self.is_in_cooldown():
            return None

        closes = [c['close'] for c in candles]

        # RSI 계산
        rsi = self.calculate_rsi(closes)
        if rsi is None:
            return None

        # 추세 필터
        trend = self.calculate_trend_filter(closes)

        # 변동성
        volatility = self.calculate_volatility(closes)

        # 거래 빈도 제어 (30분 간격)
        current_time = candles[-1].get('timestamp', candles[-1].get('datetime'))
        if self.last_trade_time:
            if isinstance(current_time, (int, float)):
                time_diff = current_time - self.last_trade_time
            else:
                time_diff = (current_time - self.last_trade_time).total_seconds()

            if time_diff < self.min_trade_interval:
                return None

        tp, sl = self.get_tp_sl()

        print(f"RSI: {rsi:.1f}, Trend: {trend}, Vol: {volatility:.3f}%")

        # ===== 롱 진입 조건 =====
        if rsi < self.oversold:
            # 강한 하락 추세에서는 롱 진입 안 함 (계속 떨어질 수 있음)
            if trend == 'strong_downtrend':
                print(f"  [SKIP] 강한 하락장 - 롱 진입 위험")
                return None

            # 변동성이 너무 높으면 진입 안 함
            if volatility > 1.0:
                print(f"  [SKIP] 변동성 너무 높음: {volatility:.3f}%")
                return None

            print(f"  [LONG] RSI 과매도, TP: {tp}%, SL: {sl}%")
            self.last_trade_time = current_time
            return {'signal': 'long', 'take_profit': tp, 'stop_loss': sl}

        # ===== 숏 진입 조건 =====
        elif rsi > self.overbought:
            # 강한 상승 추세에서는 숏 진입 안 함 (계속 오를 수 있음)
            if trend == 'strong_uptrend':
                print(f"  [SKIP] 강한 상승장 - 숏 진입 위험")
                return None

            # 변동성이 너무 높으면 진입 안 함
            if volatility > 1.0:
                print(f"  [SKIP] 변동성 너무 높음: {volatility:.3f}%")
                return None

            print(f"  [SHORT] RSI 과매수, TP: {tp}%, SL: {sl}%")
            self.last_trade_time = current_time
            return {'signal': 'short', 'take_profit': tp, 'stop_loss': sl}

        return None


if __name__ == "__main__":
    print("종합 개선 전략 (Ultimate RSI Strategy)")
    print("\n개선 사항:")
    print("1. 반전 청산 제거 - TP/SL만 사용")
    print("2. 레버리지 권장: 3배 (기존 5배에서 낮춤)")
    print("3. TP/SL 최적화: TP 3%, SL 2% (Risk:Reward = 1:1.5)")
    print("4. 추세 필터: 강한 추세장에서 거래 안 함")
    print("5. RSI 기준 보수적: 30/70 (기존 25/65)")
    print("6. 거래 간격: 30분 (기존 15분)")
    print("7. 3연속 손실 시 1시간 휴식")
