"""
역발상 RSI 전략 - 시장 반대로 베팅
"""
import numpy as np
from datetime import datetime, timedelta


class InverseRSIStrategy:
    """
    역발상 RSI 전략

    핵심 아이디어:
    - RSI 과매도(< 25) → 더 떨어질 것 → 숏 진입
    - RSI 과매수(> 65) → 더 오를 것 → 롱 진입
    - 기존 SL이 새로운 TP
    - 기존 TP가 새로운 SL
    """

    def __init__(self, period=9, oversold=25, overbought=65):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

        # 손실 추적
        self.recent_trades = []
        self.consecutive_losses = 0
        self.last_candle_time = None
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
        """추세 강도 계산"""
        if len(prices) < period:
            return 'neutral', 0.0

        recent_avg = np.mean(prices[-period//2:])
        past_avg = np.mean(prices[-period:-period//2])
        diff_pct = (recent_avg - past_avg) / past_avg

        volatility = np.std(prices[-period:]) / np.mean(prices[-period:])

        if volatility > 0:
            strength = abs(diff_pct) / volatility
            strength = min(1.0, strength)
        else:
            strength = 0.0

        if diff_pct > 0.02:
            if strength > 0.6:
                return 'strong_up', strength
            else:
                return 'weak_up', strength
        elif diff_pct < -0.02:
            if strength > 0.6:
                return 'strong_down', strength
            else:
                return 'weak_down', strength
        else:
            return 'neutral', strength

    def calculate_dynamic_levels(self, side, trend, strength):
        """
        동적 TP/SL 계산 (역발상) - 최적화된 비율

        승률 58%를 활용한 Risk/Reward 조정
        """
        # 적당한 익절 (2.5%)
        take_profit = 2.5

        # 적당한 손절 (3.0%)
        base_sl = 3.0

        # 추세에 따라 손절 미세 조정
        if side == 'short':  # 역발상 숏 (원래 롱 신호)
            if trend in ['strong_down', 'weak_down']:
                # 하락 추세면 숏이 유리 → 손절 조금 크게
                stop_loss = base_sl + (strength * 1.0)  # 3~4%
            else:
                stop_loss = base_sl  # 3%

        else:  # 역발상 롱 (원래 숏 신호)
            if trend in ['strong_up', 'weak_up']:
                # 상승 추세면 롱이 유리 → 손절 조금 크게
                stop_loss = base_sl + (strength * 1.0)  # 3~4%
            else:
                stop_loss = base_sl  # 3%

        return round(take_profit, 1), round(stop_loss, 1)

    def update_trade_result(self, result):
        """거래 결과 업데이트"""
        now = datetime.now()
        self.recent_trades.append((now, result))

        if len(self.recent_trades) > 10:
            self.recent_trades.pop(0)

        if result == 'loss':
            self.consecutive_losses += 1
            self.position_scale = max(0.5, self.position_scale - 0.2)
            print(f"  [손실] 포지션 크기 축소: {self.position_scale * 100:.0f}%")

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
        역발상 신호 생성

        Returns:
            dict: {'signal': 'long'/'short', 'take_profit': float, 'stop_loss': float}
        """
        if not candles or len(candles) < self.period + 20:
            return None

        if self.is_in_cooldown():
            return None

        closes = [c['close'] for c in candles]
        rsi = self.calculate_rsi(closes)

        if rsi is None:
            return None

        trend, strength = self.calculate_trend_strength(closes)

        print(f"RSI: {rsi:.2f}, Trend: {trend}, Strength: {strength:.2f}, "
              f"PosScale: {self.position_scale:.0%}, ConsecLoss: {self.consecutive_losses}")

        # 거래 빈도 제어: 15분 간격
        current_candle_time = candles[-1].get('timestamp', candles[-1].get('datetime'))
        if self.last_candle_time:
            if isinstance(current_candle_time, (int, float)):
                time_diff = current_candle_time - self.last_candle_time
                if time_diff < 900:
                    return None
            else:
                time_diff = (current_candle_time - self.last_candle_time).total_seconds()
                if time_diff < 900:
                    return None

        # 역발상 신호!

        # RSI 과매도 → 원래는 롱인데, 역발상으로 숏!
        if rsi < self.oversold:
            tp, sl = self.calculate_dynamic_levels('short', trend, strength)
            print(f"  [INVERSE SHORT] RSI 과매도 → 더 떨어질 것, TP: {tp}%, SL: {sl}%")
            self.last_candle_time = current_candle_time
            return {'signal': 'short', 'take_profit': tp, 'stop_loss': sl}

        # RSI 과매수 → 원래는 숏인데, 역발상으로 롱!
        elif rsi > self.overbought:
            tp, sl = self.calculate_dynamic_levels('long', trend, strength)
            print(f"  [INVERSE LONG] RSI 과매수 → 더 오를 것, TP: {tp}%, SL: {sl}%")
            self.last_candle_time = current_candle_time
            return {'signal': 'long', 'take_profit': tp, 'stop_loss': sl}

        return None

    def get_position_scale(self):
        """현재 포지션 크기 비율 반환"""
        return self.position_scale


if __name__ == "__main__":
    print("역발상 RSI 전략 준비 완료!")
    print("\n핵심 로직:")
    print("- RSI < 25 (과매도) → SHORT (더 떨어질 것)")
    print("- RSI > 65 (과매수) → LONG (더 오를 것)")
    print("- TP: 2.5% (적당한 익절)")
    print("- SL: 3~4% (적당한 손절)")
    print("- Risk/Reward: 1:1.2")
