"""
Scalping Strategies - 단타매매 전략
5분봉 기준 빠른 진입/청산
"""
import numpy as np
import pandas as pd


class MomentumScalpingStrategy:
    """모멘텀 스캘핑 - 강한 방향성 포착"""

    def __init__(self, momentum_period=5, strength_threshold=0.003):
        """
        Args:
            momentum_period: 모멘텀 계산 기간 (짧게)
            strength_threshold: 모멘텀 강도 임계값 (0.3%)
        """
        self.period = momentum_period
        self.strength_threshold = strength_threshold

    def calculate_momentum(self, prices):
        """최근 가격 모멘텀 계산"""
        if len(prices) < self.period + 1:
            return None

        current = prices[-1]
        past = prices[-self.period-1]
        momentum = (current - past) / past

        return momentum

    def calculate_volume_surge(self, candles):
        """거래량 급증 확인"""
        if len(candles) < 10:
            return False

        recent_volumes = [c['volume'] for c in candles[-10:]]
        current_vol = recent_volumes[-1]
        avg_vol = np.mean(recent_volumes[:-1])

        # 현재 거래량이 평균의 1.5배 이상
        return current_vol > avg_vol * 1.5

    def analyze(self, candles):
        """
        빠른 모멘텀 포착
        - 강한 상승 모멘텀 = 롱
        - 강한 하락 모멘텀 = 숏
        """
        if not candles or len(candles) < self.period + 1:
            return None

        closes = [c['close'] for c in candles]
        momentum = self.calculate_momentum(closes)

        if momentum is None:
            return None

        # 거래량 급증 시에만 진입 (신뢰도 높임)
        volume_surge = self.calculate_volume_surge(candles)

        print(f"Momentum: {momentum*100:.2f}%, Volume Surge: {volume_surge}")

        if volume_surge:
            if momentum > self.strength_threshold:
                return 'long'
            elif momentum < -self.strength_threshold:
                return 'short'

        return None


class EMAScalpingStrategy:
    """EMA 크로스 스캘핑 - 빠른 이동평균"""

    def __init__(self, fast_period=5, slow_period=13):
        """
        Args:
            fast_period: 빠른 EMA (매우 짧게)
            slow_period: 느린 EMA
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.period = slow_period

    def calculate_ema(self, prices, period):
        """지수 이동평균 계산"""
        if len(prices) < period:
            return None

        prices_array = np.array(prices)
        ema = pd.Series(prices_array).ewm(span=period, adjust=False).mean()
        return ema.iloc[-1]

    def analyze(self, candles):
        """
        빠른 EMA 크로스오버
        - 골든크로스 = 롱
        - 데드크로스 = 숏
        """
        if not candles or len(candles) < self.slow_period + 1:
            return None

        closes = [c['close'] for c in candles]

        fast_ema = self.calculate_ema(closes, self.fast_period)
        slow_ema = self.calculate_ema(closes, self.slow_period)

        if fast_ema is None or slow_ema is None:
            return None

        # 이전 값들도 계산
        prev_fast_ema = self.calculate_ema(closes[:-1], self.fast_period)
        prev_slow_ema = self.calculate_ema(closes[:-1], self.slow_period)

        if prev_fast_ema is None or prev_slow_ema is None:
            return None

        print(f"EMA Fast: {fast_ema:.2f}, Slow: {slow_ema:.2f}")

        # 크로스오버 감지
        if prev_fast_ema <= prev_slow_ema and fast_ema > slow_ema:
            return 'long'
        elif prev_fast_ema >= prev_slow_ema and fast_ema < slow_ema:
            return 'short'

        return None


class VolumeBreakoutStrategy:
    """거래량 돌파 전략 - 돌파 + 거래량"""

    def __init__(self, breakout_period=10, volume_multiplier=2.0):
        """
        Args:
            breakout_period: 돌파 확인 기간
            volume_multiplier: 거래량 배수
        """
        self.period = breakout_period
        self.volume_multiplier = volume_multiplier

    def analyze(self, candles):
        """
        가격 돌파 + 거래량 급증
        - 고점 돌파 + 거래량 = 롱
        - 저점 돌파 + 거래량 = 숏
        """
        if not candles or len(candles) < self.period + 1:
            return None

        recent = candles[-self.period-1:-1]
        current = candles[-1]

        highs = [c['high'] for c in recent]
        lows = [c['low'] for c in recent]
        volumes = [c['volume'] for c in recent]

        resistance = max(highs)
        support = min(lows)
        avg_volume = np.mean(volumes)

        current_price = current['close']
        current_volume = current['volume']

        print(f"Price: {current_price:.2f}, Resistance: {resistance:.2f}, Support: {support:.2f}")
        print(f"Volume: {current_volume:.0f}, Avg: {avg_volume:.0f} ({current_volume/avg_volume:.1f}x)")

        # 거래량 급증 확인
        if current_volume > avg_volume * self.volume_multiplier:
            # 저항선 돌파
            if current_price > resistance:
                return 'long'
            # 지지선 이탈
            elif current_price < support:
                return 'short'

        return None


class ScalpingRSIStrategy:
    """스캘핑용 RSI - 매우 짧은 기간"""

    def __init__(self, period=7, oversold=35, overbought=65):
        """
        Args:
            period: RSI 기간 (매우 짧게)
            oversold: 과매도 (덜 극단적)
            overbought: 과매수 (덜 극단적)
        """
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

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

    def check_trend(self, candles):
        """간단한 추세 확인 (20 EMA)"""
        if len(candles) < 20:
            return 'neutral'

        closes = [c['close'] for c in candles[-20:]]
        ema = pd.Series(closes).ewm(span=20, adjust=False).mean().iloc[-1]
        current = closes[-1]

        if current > ema * 1.001:  # 0.1% 이상
            return 'uptrend'
        elif current < ema * 0.999:
            return 'downtrend'
        return 'neutral'

    def analyze(self, candles):
        """
        RSI + 추세 필터
        - 상승 추세 + RSI 과매도 = 롱만
        - 하락 추세 + RSI 과매수 = 숏만
        """
        if not candles or len(candles) < self.period + 1:
            return None

        closes = [c['close'] for c in candles]
        rsi = self.calculate_rsi(closes)

        if rsi is None:
            return None

        trend = self.check_trend(candles)

        print(f"RSI: {rsi:.2f}, Trend: {trend}")

        # 추세 방향으로만 진입
        if trend == 'uptrend' and rsi < self.oversold:
            return 'long'
        elif trend == 'downtrend' and rsi > self.overbought:
            return 'short'

        return None


class MACDScalpingStrategy:
    """MACD 스캘핑 - 빠른 모멘텀 전환"""

    def __init__(self, fast=12, slow=26, signal=9):
        """
        Args:
            fast: 빠른 EMA
            slow: 느린 EMA
            signal: 시그널 라인
        """
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.period = slow + signal

    def calculate_macd(self, prices):
        """MACD 계산"""
        if len(prices) < self.slow + self.signal:
            return None, None, None

        prices_series = pd.Series(prices)

        ema_fast = prices_series.ewm(span=self.fast, adjust=False).mean()
        ema_slow = prices_series.ewm(span=self.slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]

    def analyze(self, candles):
        """
        MACD 크로스오버
        - MACD > Signal = 롱
        - MACD < Signal = 숏
        """
        if not candles or len(candles) < self.period:
            return None

        closes = [c['close'] for c in candles]

        macd, signal, histogram = self.calculate_macd(closes)

        if macd is None:
            return None

        # 이전 값 계산
        prev_macd, prev_signal, prev_hist = self.calculate_macd(closes[:-1])

        if prev_macd is None:
            return None

        print(f"MACD: {macd:.2f}, Signal: {signal:.2f}, Hist: {histogram:.2f}")

        # 크로스오버 (히스토그램 부호 변경)
        if prev_hist <= 0 and histogram > 0:
            return 'long'
        elif prev_hist >= 0 and histogram < 0:
            return 'short'

        return None


class SupertrendStrategy:
    """슈퍼트렌드 전략 - 트렌드 추종"""

    def __init__(self, period=10, multiplier=3):
        """
        Args:
            period: ATR 계산 기간
            multiplier: ATR 배수
        """
        self.period = period
        self.multiplier = multiplier

    def calculate_atr(self, candles):
        """ATR 계산"""
        if len(candles) < self.period + 1:
            return None

        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        closes = np.array([c['close'] for c in candles])

        high_low = highs[1:] - lows[1:]
        high_close = np.abs(highs[1:] - closes[:-1])
        low_close = np.abs(lows[1:] - closes[:-1])

        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = np.mean(tr[-self.period:])

        return atr

    def calculate_supertrend(self, candles):
        """슈퍼트렌드 계산"""
        if len(candles) < self.period + 1:
            return None, None

        atr = self.calculate_atr(candles)
        if atr is None:
            return None, None

        current = candles[-1]
        hl_avg = (current['high'] + current['low']) / 2

        upper_band = hl_avg + (self.multiplier * atr)
        lower_band = hl_avg - (self.multiplier * atr)

        return upper_band, lower_band

    def analyze(self, candles):
        """
        슈퍼트렌드 신호
        - 가격 > 하단밴드 = 롱
        - 가격 < 상단밴드 = 숏
        """
        if not candles or len(candles) < self.period + 2:
            return None

        upper, lower = self.calculate_supertrend(candles)
        prev_upper, prev_lower = self.calculate_supertrend(candles[:-1])

        if upper is None or prev_upper is None:
            return None

        current_price = candles[-1]['close']
        prev_price = candles[-2]['close']

        print(f"Price: {current_price:.2f}, Upper: {upper:.2f}, Lower: {lower:.2f}")

        # 트렌드 전환 감지
        if prev_price <= prev_lower and current_price > lower:
            return 'long'
        elif prev_price >= prev_upper and current_price < upper:
            return 'short'

        return None


class StochasticScalpingStrategy:
    """스토캐스틱 스캘핑"""

    def __init__(self, k_period=14, d_period=3, oversold=20, overbought=80):
        """
        Args:
            k_period: %K 기간
            d_period: %D 기간 (smoothing)
            oversold: 과매도
            overbought: 과매수
        """
        self.k_period = k_period
        self.d_period = d_period
        self.oversold = oversold
        self.overbought = overbought
        self.period = k_period + d_period

    def calculate_stochastic(self, candles):
        """스토캐스틱 계산"""
        if len(candles) < self.k_period:
            return None, None

        recent = candles[-self.k_period:]
        highs = [c['high'] for c in recent]
        lows = [c['low'] for c in recent]
        closes = [c['close'] for c in recent]

        highest_high = max(highs)
        lowest_low = min(lows)
        current_close = closes[-1]

        if highest_high == lowest_low:
            k = 50
        else:
            k = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100

        # %D는 %K의 이동평균
        if len(candles) >= self.k_period + self.d_period:
            k_values = []
            for i in range(self.d_period):
                idx = -(self.d_period - i)
                subset = candles[max(0, len(candles) + idx - self.k_period):len(candles) + idx]
                if len(subset) >= self.k_period:
                    h = max([c['high'] for c in subset[-self.k_period:]])
                    l = min([c['low'] for c in subset[-self.k_period:]])
                    cl = subset[-1]['close']
                    if h != l:
                        k_values.append(((cl - l) / (h - l)) * 100)
            d = np.mean(k_values) if k_values else k
        else:
            d = k

        return k, d

    def analyze(self, candles):
        """
        스토캐스틱 신호
        - %K가 과매도에서 %D 상향돌파 = 롱
        - %K가 과매수에서 %D 하향돌파 = 숏
        """
        if not candles or len(candles) < self.period:
            return None

        k, d = self.calculate_stochastic(candles)
        prev_k, prev_d = self.calculate_stochastic(candles[:-1])

        if k is None or prev_k is None:
            return None

        print(f"Stochastic K: {k:.2f}, D: {d:.2f}")

        # 과매도 구간에서 상향 돌파
        if k < self.oversold and prev_k < prev_d and k > d:
            return 'long'
        # 과매수 구간에서 하향 돌파
        elif k > self.overbought and prev_k > prev_d and k < d:
            return 'short'

        return None


class PriceActionStrategy:
    """가격 액션 전략 - 지지/저항 돌파"""

    def __init__(self, lookback=20, breakout_threshold=0.002):
        """
        Args:
            lookback: 지지/저항 확인 기간
            breakout_threshold: 돌파 임계값 (0.2%)
        """
        self.period = lookback
        self.breakout_threshold = breakout_threshold

    def find_support_resistance(self, candles):
        """지지선/저항선 찾기"""
        if len(candles) < self.period:
            return None, None

        recent = candles[-self.period:]
        highs = [c['high'] for c in recent]
        lows = [c['low'] for c in recent]

        resistance = max(highs)
        support = min(lows)

        return support, resistance

    def analyze(self, candles):
        """
        지지/저항 돌파
        - 저항 돌파 = 롱
        - 지지 이탈 = 숏
        """
        if not candles or len(candles) < self.period + 1:
            return None

        support, resistance = self.find_support_resistance(candles[:-1])

        if support is None:
            return None

        current = candles[-1]
        prev = candles[-2]

        current_price = current['close']
        prev_price = prev['close']

        print(f"Price: {current_price:.2f}, Support: {support:.2f}, Resistance: {resistance:.2f}")

        # 저항선 돌파 (확실하게)
        if prev_price <= resistance and current_price > resistance * (1 + self.breakout_threshold):
            return 'long'
        # 지지선 이탈
        elif prev_price >= support and current_price < support * (1 - self.breakout_threshold):
            return 'short'

        return None


class VWAPStrategy:
    """VWAP 전략 - 기관 진입가 기준"""

    def __init__(self, period=20):
        """
        Args:
            period: VWAP 계산 기간
        """
        self.period = period

    def calculate_vwap(self, candles):
        """VWAP 계산"""
        if len(candles) < self.period:
            return None

        recent = candles[-self.period:]

        typical_prices = [(c['high'] + c['low'] + c['close']) / 3 for c in recent]
        volumes = [c['volume'] for c in recent]

        vwap = sum([p * v for p, v in zip(typical_prices, volumes)]) / sum(volumes)

        return vwap

    def analyze(self, candles):
        """
        VWAP 기준 평균회귀
        - 가격 < VWAP = 롱 (싸다)
        - 가격 > VWAP = 숏 (비싸다)
        """
        if not candles or len(candles) < self.period:
            return None

        vwap = self.calculate_vwap(candles)

        if vwap is None:
            return None

        current_price = candles[-1]['close']
        prev_price = candles[-2]['close']

        deviation = (current_price - vwap) / vwap

        print(f"Price: {current_price:.2f}, VWAP: {vwap:.2f}, Deviation: {deviation*100:.2f}%")

        # 1% 이상 괴리 시에만 진입
        if prev_price >= vwap and current_price < vwap and deviation < -0.01:
            return 'long'
        elif prev_price <= vwap and current_price > vwap and deviation > 0.01:
            return 'short'

        return None


if __name__ == "__main__":
    print("Scalping strategies ready")
