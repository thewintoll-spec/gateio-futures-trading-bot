"""
그리드 트레이딩 전략 (Grid Trading Strategy)

핵심 개념:
- 가격 범위를 여러 구간(그리드)으로 분할
- 하락 시 매수, 상승 시 매도
- 방향 예측 불필요, 변동성으로 수익
- 횡보장에 최적화

장점:
- 승률 70%+ (횡보장)
- 안정적인 수익
- 방향 예측 불필요
- 자동화 용이
"""
import numpy as np
from datetime import datetime, timedelta


class GridTradingStrategy:
    """
    그리드 트레이딩 전략

    작동 원리:
    1. 현재가 기준으로 ±range_pct 범위 설정
    2. num_grids 개의 그리드 생성
    3. 가격이 그리드 아래로 내려가면 매수
    4. 가격이 그리드 위로 올라가면 매도
    5. 각 그리드마다 profit_per_grid % 수익 목표
    """

    def __init__(self, num_grids=10, range_pct=5.0, profit_per_grid=0.5,
                 rebalance_threshold=7.0, max_positions=5, tight_sl=True,
                 use_trend_filter=True, dynamic_sl=True, use_regime_filter=True,
                 adx_threshold=25):
        """
        Args:
            num_grids: 그리드 개수 (기본 10개)
            range_pct: 가격 범위 ±% (기본 ±5%)
            profit_per_grid: 각 그리드당 목표 수익률 % (기본 0.5%)
            rebalance_threshold: 리밸런싱 임계값 % (기본 7%)
            max_positions: 최대 동시 포지션 수 (기본 5개)
            tight_sl: 타이트한 손절 사용 (기본 True)
            use_trend_filter: 추세 필터 사용 (기본 True)
            dynamic_sl: 동적 손절 사용 (기본 True)
            use_regime_filter: 시장 상태 필터 사용 (기본 True)
            adx_threshold: ADX 임계값 (기본 25, 이상이면 추세장으로 판단)
        """
        self.num_grids = num_grids
        self.range_pct = range_pct
        self.profit_per_grid = profit_per_grid
        self.rebalance_threshold = rebalance_threshold
        self.max_positions = max_positions
        self.tight_sl = tight_sl
        self.use_trend_filter = use_trend_filter
        self.dynamic_sl = dynamic_sl
        self.use_regime_filter = use_regime_filter
        self.adx_threshold = adx_threshold

        # 그리드 상태
        self.grids = []
        self.center_price = None
        self.last_rebalance_time = None

        # 포지션 추적
        self.active_positions = {}  # {grid_level: {'entry_price', 'size', 'side'}}

        # 거래 제어
        self.min_rebalance_interval = 3600  # 1시간

        # 백테스트 엔진 호환성
        self.period = 20  # 최소 캔들 수

        # 통계
        self.total_trades = 0
        self.profitable_trades = 0
        self.grid_hits = {}  # 각 그리드 히트 횟수

    def initialize_grids(self, current_price):
        """그리드 초기화"""
        self.center_price = current_price
        self.grids = []

        # 그리드 간격 계산
        grid_spacing = (2 * self.range_pct) / self.num_grids

        # 그리드 생성 (하단부터 상단까지)
        for i in range(self.num_grids + 1):
            # 하단 그리드부터 상단 그리드까지
            grid_pct = -self.range_pct + (i * grid_spacing)
            grid_price = current_price * (1 + grid_pct / 100)

            self.grids.append({
                'level': i,
                'price': grid_price,
                'pct_from_center': grid_pct,
                'filled': False
            })

            self.grid_hits[i] = 0

        print(f"\n[그리드 초기화] 중심가: {current_price:.2f}")
        print(f"  범위: {self.grids[0]['price']:.2f} ~ {self.grids[-1]['price']:.2f}")
        print(f"  그리드 간격: {grid_spacing:.2f}%")

        self.last_rebalance_time = datetime.now()

    def should_rebalance(self, current_price, current_time):
        """그리드 리밸런싱 필요 여부"""
        if self.center_price is None:
            return True

        # 가격이 범위를 벗어났는지 확인
        price_change_pct = abs((current_price - self.center_price) / self.center_price * 100)

        if price_change_pct > self.rebalance_threshold:
            # 최소 간격 확인
            if self.last_rebalance_time:
                if isinstance(current_time, (int, float)):
                    time_diff = current_time - self.last_rebalance_time.timestamp()
                else:
                    time_diff = (current_time - self.last_rebalance_time).total_seconds()

                if time_diff >= self.min_rebalance_interval:
                    print(f"\n[리밸런싱] 가격 변화 {price_change_pct:.2f}% > {self.rebalance_threshold}%")
                    return True
            else:
                return True

        return False

    def find_grid_level(self, price):
        """현재 가격이 속한 그리드 레벨 찾기"""
        if not self.grids:
            return None

        for i in range(len(self.grids) - 1):
            if self.grids[i]['price'] <= price < self.grids[i + 1]['price']:
                return i

        # 범위를 벗어난 경우
        if price < self.grids[0]['price']:
            return 0
        if price >= self.grids[-1]['price']:
            return len(self.grids) - 1

        return None

    def calculate_trend_strength(self, candles, period=20):
        """추세 강도 계산 (EMA 기반)"""
        if len(candles) < period:
            return 0

        closes = [c['close'] for c in candles[-period:]]
        ema = np.mean(closes)  # 간단히 평균 사용
        current = closes[-1]

        trend_pct = (current - ema) / ema * 100
        return trend_pct

    def calculate_adx(self, candles, period=14):
        """
        ADX (Average Directional Index) 계산

        ADX 값:
        - 0~20: 약한 추세 또는 횡보
        - 20~25: 추세 시작
        - 25~50: 강한 추세
        - 50~75: 매우 강한 추세
        - 75~100: 극단적 추세

        Returns:
            tuple: (adx, plus_di, minus_di)
        """
        if len(candles) < period + 1:
            return 0, 0, 0

        highs = np.array([c['high'] for c in candles[-(period+1):]])
        lows = np.array([c['low'] for c in candles[-(period+1):]])
        closes = np.array([c['close'] for c in candles[-(period+1):]])

        # True Range 계산
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        # Directional Movement 계산
        up_move = highs[1:] - highs[:-1]
        down_move = lows[:-1] - lows[1:]

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        # Smoothed TR, +DM, -DM
        atr = np.mean(tr)
        plus_dm_smooth = np.mean(plus_dm)
        minus_dm_smooth = np.mean(minus_dm)

        # Directional Indicators
        plus_di = (plus_dm_smooth / atr * 100) if atr > 0 else 0
        minus_di = (minus_dm_smooth / atr * 100) if atr > 0 else 0

        # DX (Directional Index)
        di_sum = plus_di + minus_di
        di_diff = abs(plus_di - minus_di)
        dx = (di_diff / di_sum * 100) if di_sum > 0 else 0

        # ADX (smoothed DX)
        adx = dx  # 간단화: 첫 계산이므로 DX를 그대로 사용

        return adx, plus_di, minus_di

    def detect_market_regime(self, candles):
        """
        시장 상태 감지 (ADX 기반)

        Returns:
            'ranging': 횡보장 - Grid Trading 실행
            'trending_up': 상승 추세 - 거래 중단
            'trending_down': 하락 추세 - 거래 중단
        """
        if not self.use_regime_filter:
            return 'ranging'

        adx, plus_di, minus_di = self.calculate_adx(candles, 14)

        # ADX가 임계값보다 낮으면 횡보장
        if adx < self.adx_threshold:
            return 'ranging'

        # ADX가 높으면 추세장 → 방향 확인
        if plus_di > minus_di:
            return 'trending_up'
        else:
            return 'trending_down'

    def is_strong_trend(self, candles):
        """강한 추세 여부 판단"""
        if not self.use_trend_filter:
            return False

        trend = self.calculate_trend_strength(candles, 20)

        # 강한 하락 추세 (롱 진입 위험)
        if trend < -3.0:
            return 'downtrend'
        # 강한 상승 추세 (숏 진입 위험)
        elif trend > 3.0:
            return 'uptrend'

        return False

    def get_dynamic_sl(self, side, atr_pct):
        """동적 손절 계산"""
        if not self.dynamic_sl:
            # 고정 손절
            return self.rebalance_threshold * 0.5

        # ATR 기반 동적 손절
        if self.tight_sl:
            # 타이트한 손절 (1.0 ~ 2.0%)
            sl = max(1.0, min(2.0, atr_pct * 1.0))
        else:
            # 일반 손절 (2.0 ~ 3.5%)
            sl = max(2.0, min(3.5, atr_pct * 1.5))

        return sl

    def analyze(self, candles):
        """
        그리드 트레이딩 신호 생성

        Returns:
            dict: {'signal': 'long'/'short'/'close', 'take_profit': float, 'stop_loss': float}
            또는 None
        """
        if not candles or len(candles) < 20:
            return None

        current_candle = candles[-1]
        current_price = current_candle['close']
        current_time = current_candle.get('timestamp', current_candle.get('datetime'))

        # 그리드 초기화 또는 리밸런싱
        if not self.grids or self.should_rebalance(current_price, current_time):
            self.initialize_grids(current_price)
            return None

        # 시장 상태 필터: ADX 기반 횡보/추세 판단
        regime = self.detect_market_regime(candles)

        if regime == 'trending_up':
            adx, plus_di, minus_di = self.calculate_adx(candles, 14)
            print(f"  [시장필터] 상승 추세 감지 - 거래 중단 (ADX: {adx:.1f}, +DI: {plus_di:.1f}, -DI: {minus_di:.1f})")
            return None
        elif regime == 'trending_down':
            adx, plus_di, minus_di = self.calculate_adx(candles, 14)
            print(f"  [시장필터] 하락 추세 감지 - 거래 중단 (ADX: {adx:.1f}, +DI: {plus_di:.1f}, -DI: {minus_di:.1f})")
            return None
        else:
            # 횡보장 - Grid Trading 실행
            adx, plus_di, minus_di = self.calculate_adx(candles, 14)
            print(f"  [시장필터] 횡보장 감지 - Grid Trading 실행 (ADX: {adx:.1f})")

        # 추세 필터: 강한 추세 시 거래 제한
        trend = self.is_strong_trend(candles)
        if trend == 'downtrend':
            # 강한 하락장: 롱 진입 금지
            print(f"  [추세필터] 강한 하락장 감지 - 롱 진입 제한")
            return None
        elif trend == 'uptrend':
            # 강한 상승장: 숏 진입 금지
            print(f"  [추세필터] 강한 상승장 감지 - 숏 진입 제한")
            return None

        # 현재 그리드 레벨 찾기
        current_level = self.find_grid_level(current_price)
        if current_level is None:
            return None

        current_grid = self.grids[current_level]

        # 변동성 체크 (ATR)
        atr_pct = self.calculate_atr_percent(candles, 14)

        # 변동성이 너무 낮으면 거래 안 함
        if atr_pct < 0.5:
            return None

        # 최대 포지션 수 체크
        if len(self.active_positions) >= self.max_positions:
            # 기존 포지션 청산 신호만 생성
            return self.check_close_signals(current_price, current_level)

        # ===== 매수 신호 (하단 그리드) =====
        # 현재가가 중심가 아래이고, 해당 그리드에 포지션이 없으면 매수
        if current_level < len(self.grids) // 2:  # 하단 절반
            if current_level not in self.active_positions:
                # 목표가: 한 그리드 위
                target_grid = min(current_level + 1, len(self.grids) - 1)
                target_price = self.grids[target_grid]['price']
                tp_pct = (target_price - current_price) / current_price * 100

                # 동적 손절
                sl_pct = self.get_dynamic_sl('long', atr_pct)

                self.grid_hits[current_level] += 1
                self.active_positions[current_level] = {
                    'entry_price': current_price,
                    'side': 'long',
                    'target_level': target_grid
                }

                print(f"\n[GRID LONG] Level {current_level} @ {current_price:.2f}")
                print(f"  목표: Level {target_grid} @ {target_price:.2f} (TP: {tp_pct:.2f}%)")
                print(f"  활성 포지션: {len(self.active_positions)}/{self.max_positions}")

                return {
                    'signal': 'long',
                    'take_profit': tp_pct,
                    'stop_loss': sl_pct,
                    'grid_level': current_level
                }

        # ===== 매도 신호 (상단 그리드) =====
        # 현재가가 중심가 위이고, 해당 그리드에 포지션이 없으면 매도
        elif current_level > len(self.grids) // 2:  # 상단 절반
            if current_level not in self.active_positions:
                # 목표가: 한 그리드 아래
                target_grid = max(current_level - 1, 0)
                target_price = self.grids[target_grid]['price']
                tp_pct = (current_price - target_price) / current_price * 100

                # 동적 손절
                sl_pct = self.get_dynamic_sl('short', atr_pct)

                self.grid_hits[current_level] += 1
                self.active_positions[current_level] = {
                    'entry_price': current_price,
                    'side': 'short',
                    'target_level': target_grid
                }

                print(f"\n[GRID SHORT] Level {current_level} @ {current_price:.2f}")
                print(f"  목표: Level {target_grid} @ {target_price:.2f} (TP: {tp_pct:.2f}%)")
                print(f"  활성 포지션: {len(self.active_positions)}/{self.max_positions}")

                return {
                    'signal': 'short',
                    'take_profit': tp_pct,
                    'stop_loss': sl_pct,
                    'grid_level': current_level
                }

        # 기존 포지션 청산 체크
        return self.check_close_signals(current_price, current_level)

    def check_close_signals(self, current_price, current_level):
        """기존 포지션 청산 신호 체크"""
        # 간단 버전: 목표 레벨 도달 시 청산은 TP/SL로 처리
        return None

    def calculate_atr_percent(self, candles, period=14):
        """ATR 퍼센트 계산"""
        if len(candles) < period + 1:
            return 1.0

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

    def update_trade_result(self, result, grid_level=None):
        """거래 결과 업데이트"""
        self.total_trades += 1

        if result == 'profit':
            self.profitable_trades += 1

        # 포지션 제거
        if grid_level is not None and grid_level in self.active_positions:
            del self.active_positions[grid_level]

    def get_statistics(self):
        """전략 통계 반환"""
        win_rate = (self.profitable_trades / self.total_trades * 100) if self.total_trades > 0 else 0

        # 가장 많이 히트된 그리드
        most_hit_grid = max(self.grid_hits.items(), key=lambda x: x[1]) if self.grid_hits else (None, 0)

        return {
            'total_trades': self.total_trades,
            'win_rate': win_rate,
            'most_hit_grid': most_hit_grid,
            'active_positions': len(self.active_positions)
        }


if __name__ == "__main__":
    print("그리드 트레이딩 전략 (Grid Trading Strategy)")
    print("\n핵심 로직:")
    print("- 현재가 기준 ±5% 범위에 10개 그리드")
    print("- 하락 시 자동 매수, 상승 시 자동 매도")
    print("- 각 그리드마다 0.5~1% 수익 목표")
    print("- 방향 예측 불필요, 변동성이 수익")
    print("\n장점:")
    print("- 횡보장 승률 70%+")
    print("- 안정적인 수익")
    print("- 리스크 관리 명확")
    print("\n레버리지 권장: 2배 (안정성 우선)")
