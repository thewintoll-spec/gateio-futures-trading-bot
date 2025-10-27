# -*- coding: utf-8 -*-
"""
적응형 멀티 시장 전략 (Adaptive Multi-Regime Strategy)

전략 로직:
- 시장 상태를 감지하여 자동으로 전략 전환
- 횡보장: 그리드 트레이딩
- 상승 추세: 추세 추종 (롱만)
- 하락 추세: 추세 추종 (숏만) 또는 대기

특징:
- ADX 기반 자동 시장 감지
- 동적 전략 전환
- 각 시장 상황에 최적화
"""
import numpy as np
from grid_strategy import GridTradingStrategy
from trend_following_strategy import TrendFollowingStrategy


class AdaptiveStrategy:
    """
    적응형 멀티 시장 전략

    로직:
    1. ADX로 시장 상태 감지 (횡보/추세)
    2. 횡보장 -> 그리드 트레이딩
    3. 상승 추세 -> 추세 추종 (롱)
    4. 하락 추세 -> 추세 추종 (숏) 또는 대기
    """

    def __init__(self, adx_threshold=25, allow_short_in_downtrend=True):
        """
        Args:
            adx_threshold: ADX 임계값 (기본 25)
            allow_short_in_downtrend: 하락장에서 숏 허용 (기본 True)
        """
        self.adx_threshold = adx_threshold
        self.allow_short_in_downtrend = allow_short_in_downtrend

        # 하위 전략 초기화
        self.grid_strategy = GridTradingStrategy(
            num_grids=30,
            range_pct=10.0,
            profit_per_grid=0.3,
            max_positions=10,
            rebalance_threshold=7.0,
            tight_sl=True,
            use_trend_filter=True,
            dynamic_sl=True,
            use_regime_filter=False  # Adaptive가 시장 감지 담당
        )

        self.trend_strategy = TrendFollowingStrategy(
            fast_ema=12,
            slow_ema=26,
            adx_threshold=25,
            trailing_stop_atr=2.0,
            min_profit_before_trail=1.0
        )

        # 현재 상태
        self.current_regime = None
        self.current_strategy = None

        # 필요한 캔들 수
        self.period = max(self.grid_strategy.period, self.trend_strategy.period)

    def calculate_adx(self, candles, period=14):
        """ADX 계산"""
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
        시장 상태 감지

        Returns:
            'ranging': 횡보장
            'trending_up': 상승 추세
            'trending_down': 하락 추세
        """
        adx, plus_di, minus_di = self.calculate_adx(candles, 14)

        # ADX < 임계값: 횡보장
        if adx < self.adx_threshold:
            return 'ranging', adx, plus_di, minus_di

        # ADX >= 임계값: 추세장
        # +DI vs -DI로 방향 판단
        if plus_di > minus_di:
            return 'trending_up', adx, plus_di, minus_di
        else:
            return 'trending_down', adx, plus_di, minus_di

    def analyze(self, candles):
        """
        적응형 전략 분석

        시장 상태를 감지하여 적절한 전략에 위임

        Returns:
            dict: {'signal': 'long'/'short'/'close', 'take_profit': float, 'stop_loss': float}
            또는 None
        """
        if not candles or len(candles) < self.period:
            return None

        # 시장 상태 감지
        regime, adx, plus_di, minus_di = self.detect_market_regime(candles)

        # 시장 상태 변경 로그
        if regime != self.current_regime:
            print(f"\n{'='*60}")
            print(f"[시장 변화] {self.current_regime} -> {regime}")
            print(f"  ADX: {adx:.1f}, +DI: {plus_di:.1f}, -DI: {minus_di:.1f}")
            print(f"{'='*60}")
            self.current_regime = regime

        # ===== 횡보장: 그리드 트레이딩 =====
        if regime == 'ranging':
            print(f"[적응형] 횡보장 (ADX: {adx:.1f}) - 그리드 트레이딩")
            self.current_strategy = 'grid'
            return self.grid_strategy.analyze(candles)

        # ===== 상승 추세: 추세 추종 (롱만) =====
        elif regime == 'trending_up':
            print(f"[적응형] 상승 추세 (ADX: {adx:.1f}) - 추세 추종 (롱)")
            self.current_strategy = 'trend_long'
            return self.trend_strategy.analyze(candles, direction='long')

        # ===== 하락 추세: 숏 또는 대기 =====
        elif regime == 'trending_down':
            if self.allow_short_in_downtrend:
                print(f"[적응형] 하락 추세 (ADX: {adx:.1f}) - 추세 추종 (숏)")
                self.current_strategy = 'trend_short'
                return self.trend_strategy.analyze(candles, direction='short')
            else:
                print(f"[적응형] 하락 추세 (ADX: {adx:.1f}) - 대기 (숏 금지)")
                self.current_strategy = 'wait'
                return None

        return None

    def get_current_strategy(self):
        """현재 활성 전략 반환"""
        return self.current_strategy

    def get_current_regime(self):
        """현재 시장 상태 반환"""
        return self.current_regime


if __name__ == "__main__":
    print("적응형 멀티 시장 전략")
    print("\n전략 로직:")
    print("- ADX < 25: 횡보장 -> 그리드 트레이딩")
    print("- ADX >= 25 & +DI > -DI: 상승 추세 -> 추세 추종 (롱)")
    print("- ADX >= 25 & +DI < -DI: 하락 추세 -> 추세 추종 (숏)")
    print("\n특징:")
    print("- 자동 시장 감지")
    print("- 동적 전략 전환")
    print("- 각 시장 상황에 최적화")
    print("- 두 전략의 장점 결합")
    print("\n권장 캔들 수: 20+ (지표 안정성)")
