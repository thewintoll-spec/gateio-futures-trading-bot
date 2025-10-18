"""
개선된 RSI 전략 - 연속 손실 방지 및 포지션 관리
"""
import numpy as np
from datetime import datetime, timedelta


class ImprovedRSIStrategy:
    """
    실전 데이터 기반 개선된 RSI 전략

    개선사항:
    1. 연속 손실 방지 (2연속 손실 시 휴식)
    2. 손실 후 포지션 크기 축소
    3. 숏 진입 조건 강화
    """

    def __init__(self, period=9, oversold=25, overbought=65):
        """
        Args:
            period: RSI 계산 기간
            oversold: 과매도 기준 (롱 진입)
            overbought: 과매수 기준 (숏 진입)
        """
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

        # 손실 추적
        self.recent_trades = []  # [(시간, 'win'/'loss'), ...]
        self.consecutive_losses = 0
        self.last_trade_time = None
        self.cooldown_until = None

        # 포지션 크기 조정
        self.position_scale = 1.0  # 1.0 = 100%, 0.5 = 50%

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

    def calculate_trend(self, prices, period=20):
        """
        간단한 추세 판단

        Returns:
            'uptrend', 'downtrend', 'neutral'
        """
        if len(prices) < period:
            return 'neutral'

        # 최근 가격 vs 이전 가격
        recent_avg = np.mean(prices[-period//2:])
        past_avg = np.mean(prices[-period:-period//2])

        diff_pct = (recent_avg - past_avg) / past_avg

        if diff_pct > 0.01:  # 1% 이상 상승
            return 'uptrend'
        elif diff_pct < -0.01:  # 1% 이상 하락
            return 'downtrend'
        else:
            return 'neutral'

    def update_trade_result(self, result):
        """
        거래 결과 업데이트

        Args:
            result: 'win' or 'loss'
        """
        now = datetime.now()
        self.recent_trades.append((now, result))
        self.last_trade_time = now

        # 최근 10개만 유지
        if len(self.recent_trades) > 10:
            self.recent_trades.pop(0)

        # 연속 손실 카운트
        if result == 'loss':
            self.consecutive_losses += 1

            # 손실 후 포지션 크기 축소
            self.position_scale = max(0.5, self.position_scale - 0.2)
            print(f"  [손실] 포지션 크기 축소: {self.position_scale * 100:.0f}%")

            # 2연속 손실 시 휴식 모드
            if self.consecutive_losses >= 2:
                self.cooldown_until = now + timedelta(minutes=30)
                print(f"  [휴식 모드] 2연속 손실 - 30분간 거래 중지")
        else:
            self.consecutive_losses = 0
            # 승리 시 포지션 크기 복구
            self.position_scale = min(1.0, self.position_scale + 0.1)
            print(f"  [승리] 포지션 크기 복구: {self.position_scale * 100:.0f}%")

    def is_in_cooldown(self):
        """휴식 모드 확인"""
        if self.cooldown_until is None:
            return False

        now = datetime.now()
        if now < self.cooldown_until:
            remaining = (self.cooldown_until - now).total_seconds() / 60
            print(f"  [휴식 모드] 남은 시간: {remaining:.1f}분")
            return True
        else:
            # 휴식 종료
            self.cooldown_until = None
            print(f"  [휴식 종료] 거래 재개")
            return False

    def analyze(self, candles):
        """
        시장 분석 및 신호 생성

        Returns:
            Signal: 'long', 'short', None
        """
        if not candles or len(candles) < self.period + 1:
            return None

        # 휴식 모드 확인
        if self.is_in_cooldown():
            return None

        closes = [c['close'] for c in candles]
        rsi = self.calculate_rsi(closes)

        if rsi is None:
            return None

        # 추세 판단
        trend = self.calculate_trend(closes)

        print(f"RSI: {rsi:.2f}, Trend: {trend}, PosScale: {self.position_scale:.0%}, "
              f"ConsecLoss: {self.consecutive_losses}")

        # 롱 신호 (기존 조건 유지)
        if rsi < self.oversold:
            # 강한 하락 추세에서는 신중
            if trend == 'downtrend':
                if rsi < self.oversold - 5:  # 더 과매도일 때만
                    print(f"  [LONG] 극단적 과매도 (하락 추세)")
                    return 'long'
            else:
                print(f"  [LONG] RSI 과매도")
                return 'long'

        # 숏 신호 (조건 강화)
        elif rsi > self.overbought:
            # 상승 추세에서는 숏 금지
            if trend == 'uptrend':
                print(f"  [SKIP] 상승 추세 - 숏 진입 금지")
                return None

            # 하락 추세이거나 횡보일 때만 숏
            # RSI가 더 높을 때만 (확신도 증가)
            if rsi > self.overbought + 5:
                print(f"  [SHORT] 강한 과매수 신호")
                return 'short'
            elif trend == 'downtrend':
                print(f"  [SHORT] 하락 추세 + 과매수")
                return 'short'
            else:
                print(f"  [SKIP] 숏 신호 약함 (RSI: {rsi:.2f})")
                return None

        return None

    def get_position_scale(self):
        """현재 포지션 크기 비율 반환"""
        return self.position_scale


if __name__ == "__main__":
    print("개선된 RSI 전략 준비 완료!")
    print("\n주요 개선사항:")
    print("1. 연속 2회 손실 시 30분 휴식")
    print("2. 손실 후 포지션 크기 자동 축소 (50%까지)")
    print("3. 승리 시 포지션 크기 점진적 복구")
    print("4. 상승 추세에서 숏 진입 금지")
    print("5. 숏 진입 조건 강화 (RSI 70 이상)")
