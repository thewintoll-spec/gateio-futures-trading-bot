"""
개선된 RSI 전략 v2 - 동적 테이크프로핏
"""
import numpy as np
from datetime import datetime, timedelta


class ImprovedRSIStrategyV2:
    """
    실전 데이터 기반 개선된 RSI 전략 v2

    핵심 개선사항:
    1. 동적 테이크프로핏 (추세 강도에 따라 5% ~ 15%)
    2. 고정 스탑로스 (1.5%)
    3. 거래 빈도 제어 (과도한 거래 방지)
    4. 추세 확인 강화
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
        self.recent_trades = []
        self.consecutive_losses = 0
        self.last_trade_time = None
        self.last_candle_time = None  # 백테스트용
        self.cooldown_until = None

        # 포지션 크기 조정
        self.position_scale = 1.0

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

    def calculate_trend_strength(self, prices, period=20):
        """
        추세 강도 계산

        Returns:
            trend: 'strong_up', 'weak_up', 'neutral', 'weak_down', 'strong_down'
            strength: 추세 강도 (0.0 ~ 1.0)
        """
        if len(prices) < period:
            return 'neutral', 0.0

        # 최근 vs 과거 가격
        recent_avg = np.mean(prices[-period//2:])
        past_avg = np.mean(prices[-period:-period//2])

        diff_pct = (recent_avg - past_avg) / past_avg

        # 변동성 계산 (표준편차)
        volatility = np.std(prices[-period:]) / np.mean(prices[-period:])

        # 추세 강도 (변동성 대비 방향성)
        if volatility > 0:
            strength = abs(diff_pct) / volatility
            strength = min(1.0, strength)  # 0~1로 정규화
        else:
            strength = 0.0

        # 추세 분류
        if diff_pct > 0.02:  # 2% 이상 상승
            if strength > 0.6:
                return 'strong_up', strength
            else:
                return 'weak_up', strength
        elif diff_pct < -0.02:  # 2% 이상 하락
            if strength > 0.6:
                return 'strong_down', strength
            else:
                return 'weak_down', strength
        else:
            return 'neutral', strength

    def calculate_dynamic_take_profit(self, side, trend, strength):
        """
        동적 테이크프로핏 계산

        Args:
            side: 'long' or 'short'
            trend: 추세 방향
            strength: 추세 강도 (0.0 ~ 1.0)

        Returns:
            take_profit_pct: 테이크프로핏 % (5.0 ~ 15.0)
        """
        base_tp = 5.0  # 기본 5%

        # 롱 포지션
        if side == 'long':
            if trend == 'strong_up':
                # 강한 상승 추세: 높은 목표 (10~15%)
                tp = base_tp + (strength * 10.0)
            elif trend == 'weak_up':
                # 약한 상승 추세: 중간 목표 (7~10%)
                tp = base_tp + (strength * 5.0)
            elif trend == 'neutral':
                # 횡보: 기본 목표 (5~7%)
                tp = base_tp + (strength * 2.0)
            else:  # weak_down, strong_down
                # 하락 추세: 낮은 목표, 빨리 익절 (3~5%)
                tp = base_tp - (strength * 2.0)
                tp = max(3.0, tp)

        # 숏 포지션
        else:
            if trend == 'strong_down':
                # 강한 하락 추세: 높은 목표 (10~15%)
                tp = base_tp + (strength * 10.0)
            elif trend == 'weak_down':
                # 약한 하락 추세: 중간 목표 (7~10%)
                tp = base_tp + (strength * 5.0)
            elif trend == 'neutral':
                # 횡보: 기본 목표 (5~7%)
                tp = base_tp + (strength * 2.0)
            else:  # weak_up, strong_up
                # 상승 추세: 낮은 목표, 빨리 익절 (3~5%)
                tp = base_tp - (strength * 2.0)
                tp = max(3.0, tp)

        return round(tp, 1)

    def update_trade_result(self, result):
        """거래 결과 업데이트"""
        now = datetime.now()
        self.recent_trades.append((now, result))
        self.last_trade_time = now

        # 최근 10개만 유지
        if len(self.recent_trades) > 10:
            self.recent_trades.pop(0)

        # 연속 손실 카운트
        if result == 'loss':
            self.consecutive_losses += 1
            self.position_scale = max(0.5, self.position_scale - 0.2)
            print(f"  [손실] 포지션 크기 축소: {self.position_scale * 100:.0f}%")

            # 2연속 손실 시 휴식 모드
            if self.consecutive_losses >= 2:
                self.cooldown_until = now + timedelta(minutes=30)
                print(f"  [휴식 모드] 2연속 손실 - 30분간 거래 중지")
        else:
            self.consecutive_losses = 0
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
            self.cooldown_until = None
            print(f"  [휴식 종료] 거래 재개")
            return False

    def analyze(self, candles):
        """
        시장 분석 및 신호 생성

        Returns:
            dict: {'signal': 'long'/'short'/None, 'take_profit': float, 'stop_loss': 1.5}
        """
        if not candles or len(candles) < self.period + 20:
            return None

        # 휴식 모드 확인
        if self.is_in_cooldown():
            return None

        closes = [c['close'] for c in candles]
        rsi = self.calculate_rsi(closes)

        if rsi is None:
            return None

        # 추세 강도 분석
        trend, strength = self.calculate_trend_strength(closes)

        print(f"RSI: {rsi:.2f}, Trend: {trend}, Strength: {strength:.2f}, "
              f"PosScale: {self.position_scale:.0%}, ConsecLoss: {self.consecutive_losses}")

        # 거래 빈도 제어: 최소 3개 캔들 간격 (5분 x 3 = 15분)
        current_candle_time = candles[-1].get('timestamp', candles[-1].get('datetime'))
        if self.last_candle_time:
            # 백테스트용: 캔들 타임스탬프 비교
            if isinstance(current_candle_time, (int, float)):
                # Unix timestamp
                time_diff = current_candle_time - self.last_candle_time
                if time_diff < 900:  # 15분 (초 단위)
                    return None
            else:
                # datetime object
                time_diff = (current_candle_time - self.last_candle_time).total_seconds()
                if time_diff < 900:
                    return None

        # 롱 신호
        if rsi < self.oversold:
            # 강한 하락 추세에서는 더 극단적인 과매도만
            if trend == 'strong_down':
                if rsi < self.oversold - 10:  # RSI < 15
                    tp = self.calculate_dynamic_take_profit('long', trend, strength)
                    print(f"  [LONG] 극단적 과매도 (강한 하락), TP: {tp}%")
                    self.last_candle_time = current_candle_time
                    return {'signal': 'long', 'take_profit': tp, 'stop_loss': 1.5}
                else:
                    print(f"  [SKIP] 강한 하락 추세 - 과매도 부족 (RSI: {rsi:.2f})")
                    return None

            # 약한 하락 추세에서는 좀 더 신중
            elif trend == 'weak_down':
                if rsi < self.oversold - 3:  # RSI < 22
                    tp = self.calculate_dynamic_take_profit('long', trend, strength)
                    print(f"  [LONG] 과매도 (약한 하락), TP: {tp}%")
                    self.last_candle_time = current_candle_time
                    return {'signal': 'long', 'take_profit': tp, 'stop_loss': 1.5}
                else:
                    print(f"  [SKIP] 약한 하락 추세 - 좀 더 기다림")
                    return None

            # 횡보/상승 추세에서는 적극 진입
            else:
                tp = self.calculate_dynamic_take_profit('long', trend, strength)
                print(f"  [LONG] RSI 과매도, TP: {tp}%")
                self.last_candle_time = current_candle_time
                return {'signal': 'long', 'take_profit': tp, 'stop_loss': 1.5}

        # 숏 신호
        elif rsi > self.overbought:
            # 상승 추세에서는 숏 금지
            if trend in ['strong_up', 'weak_up']:
                print(f"  [SKIP] 상승 추세 - 숏 진입 금지")
                return None

            # 하락 추세에서만 숏 진입
            if trend == 'strong_down':
                # 강한 하락 추세 + 과매수 = 좋은 숏 기회
                if rsi > self.overbought + 5:  # RSI > 70
                    tp = self.calculate_dynamic_take_profit('short', trend, strength)
                    print(f"  [SHORT] 강한 과매수 + 하락 추세, TP: {tp}%")
                    self.last_candle_time = current_candle_time
                    return {'signal': 'short', 'take_profit': tp, 'stop_loss': 1.5}

            elif trend == 'weak_down':
                # 약한 하락 + 강한 과매수
                if rsi > self.overbought + 8:  # RSI > 73
                    tp = self.calculate_dynamic_take_profit('short', trend, strength)
                    print(f"  [SHORT] 매우 강한 과매수 + 약한 하락, TP: {tp}%")
                    self.last_candle_time = current_candle_time
                    return {'signal': 'short', 'take_profit': tp, 'stop_loss': 1.5}

            # 횡보에서는 더 엄격
            elif trend == 'neutral':
                if rsi > self.overbought + 10:  # RSI > 75
                    tp = self.calculate_dynamic_take_profit('short', trend, strength)
                    print(f"  [SHORT] 극단적 과매수 (횡보), TP: {tp}%")
                    self.last_candle_time = current_candle_time
                    return {'signal': 'short', 'take_profit': tp, 'stop_loss': 1.5}

            print(f"  [SKIP] 숏 조건 미달 (RSI: {rsi:.2f}, Trend: {trend})")
            return None

        return None

    def get_position_scale(self):
        """현재 포지션 크기 비율 반환"""
        return self.position_scale


if __name__ == "__main__":
    print("개선된 RSI 전략 v2 준비 완료!")
    print("\n주요 개선사항:")
    print("1. 동적 테이크프로핏 (5% ~ 15%)")
    print("   - 강한 추세: 10~15% (큰 수익 노림)")
    print("   - 약한 추세: 7~10% (중간 수익)")
    print("   - 횡보: 5~7% (안전한 수익)")
    print("   - 역추세: 3~5% (빠른 익절)")
    print("2. 고정 스탑로스 1.5%")
    print("3. 거래 빈도 제어 (15분 간격)")
    print("4. 추세 강도 기반 필터링")
    print("5. 하락장에서 롱 진입 매우 신중")
    print("6. 상승장에서 숏 진입 완전 차단")
