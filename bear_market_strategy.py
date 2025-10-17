"""
하락장 대응 전략
Bear Market Adaptive Strategies
"""
import numpy as np
import pandas as pd


class MarketRegimeDetector:
    """시장 상태 감지기 - 상승/하락/횡보"""

    def __init__(self, short_period=20, long_period=50):
        """
        Args:
            short_period: 단기 추세 기간
            long_period: 장기 추세 기간
        """
        self.short_period = short_period
        self.long_period = long_period

    def detect_market_trend(self, candles):
        """
        시장 추세 감지

        Returns:
            'strong_bull': 강한 상승
            'bull': 상승
            'ranging': 횡보
            'bear': 하락
            'strong_bear': 강한 하락
        """
        if len(candles) < self.long_period:
            return 'ranging'

        closes = np.array([c['close'] for c in candles])

        # 단기/장기 이동평균
        short_ma = np.mean(closes[-self.short_period:])
        long_ma = np.mean(closes[-self.long_period:])
        current_price = closes[-1]

        # 최근 변화율
        recent_change = (current_price - closes[-self.short_period]) / closes[-self.short_period]

        # 추세 강도
        ma_diff = (short_ma - long_ma) / long_ma

        # 판단
        if ma_diff > 0.02 and recent_change > 0.03:
            return 'strong_bull'  # 강한 상승 (2% 이상 + 최근 3% 상승)
        elif ma_diff > 0.01:
            return 'bull'  # 상승
        elif ma_diff < -0.02 and recent_change < -0.03:
            return 'strong_bear'  # 강한 하락 (2% 이상 + 최근 3% 하락)
        elif ma_diff < -0.01:
            return 'bear'  # 하락
        else:
            return 'ranging'  # 횡보

    def calculate_volatility(self, candles, period=20):
        """변동성 계산 (ATR 기반)"""
        if len(candles) < period + 1:
            return 0

        highs = np.array([c['high'] for c in candles[-period-1:]])
        lows = np.array([c['low'] for c in candles[-period-1:]])
        closes = np.array([c['close'] for c in candles[-period-1:]])

        high_low = highs[1:] - lows[1:]
        high_close = np.abs(highs[1:] - closes[:-1])
        low_close = np.abs(lows[1:] - closes[:-1])

        tr = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = np.mean(tr)

        # 가격 대비 변동성 %
        volatility_pct = (atr / closes[-1]) * 100
        return volatility_pct


class BearMarketRSIStrategy:
    """하락장 특화 RSI 전략 - 숏 위주"""

    def __init__(self, period=9, oversold=20, overbought=70):
        """
        Args:
            period: RSI 기간
            oversold: 과매도 (하락장에서는 덜 공격적)
            overbought: 과매수 (숏 진입용)
        """
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.regime_detector = MarketRegimeDetector()

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

    def analyze(self, candles):
        """
        하락장 대응 분석
        - 강한 하락: 숏만 (RSI 과매수)
        - 약한 하락: 숏 위주, 롱 신중
        - 횡보/상승: 양방향
        """
        if not candles or len(candles) < self.period + 1:
            return None

        closes = [c['close'] for c in candles]
        rsi = self.calculate_rsi(closes)

        if rsi is None:
            return None

        # 시장 상태 감지
        trend = self.regime_detector.detect_market_trend(candles)
        volatility = self.regime_detector.calculate_volatility(candles)

        print(f"RSI: {rsi:.2f}, Trend: {trend}, Volatility: {volatility:.2f}%")

        # 변동성 너무 높으면 거래 안 함 (리스크 회피)
        if volatility > 5.0:
            print(f"  [SKIP] 변동성 너무 높음 ({volatility:.2f}%)")
            return None

        # 강한 하락장: 숏만
        if trend == 'strong_bear':
            if rsi > self.overbought:
                print(f"  [SHORT] 강한 하락장 + RSI 과매수")
                return 'short'
            # 롱 진입 금지
            return None

        # 약한 하락장: 숏 위주
        elif trend == 'bear':
            if rsi > self.overbought:
                print(f"  [SHORT] 하락장 + RSI 과매수")
                return 'short'
            elif rsi < self.oversold:
                # 매우 과매도일 때만 롱 (반등 노리기)
                if rsi < 15:
                    print(f"  [LONG] 극단적 과매도 반등")
                    return 'long'
            return None

        # 횡보장: 양방향 거래
        elif trend == 'ranging':
            if rsi < self.oversold:
                print(f"  [LONG] 횡보장 + RSI 과매도")
                return 'long'
            elif rsi > self.overbought:
                print(f"  [SHORT] 횡보장 + RSI 과매수")
                return 'short'

        # 상승장: 롱 위주
        else:  # bull or strong_bull
            if rsi < self.oversold:
                print(f"  [LONG] 상승장 + RSI 과매도")
                return 'long'
            # 상승장에서 숏은 위험
            return None

        return None


class BearMarketMomentumStrategy:
    """하락장 모멘텀 전략 - 하락 가속 포착"""

    def __init__(self, momentum_period=5, threshold=0.005):
        """
        Args:
            momentum_period: 모멘텀 계산 기간
            threshold: 하락 임계값 (0.5%)
        """
        self.period = momentum_period
        self.threshold = threshold
        self.regime_detector = MarketRegimeDetector()

    def calculate_momentum(self, prices):
        """모멘텀 계산"""
        if len(prices) < self.period + 1:
            return None

        current = prices[-1]
        past = prices[-self.period-1]
        momentum = (current - past) / past

        return momentum

    def volume_confirmation(self, candles):
        """거래량 확인"""
        if len(candles) < 10:
            return False

        volumes = [c['volume'] for c in candles[-10:]]
        current_vol = volumes[-1]
        avg_vol = np.mean(volumes[:-1])

        return current_vol > avg_vol * 1.5

    def analyze(self, candles):
        """
        하락 모멘텀 포착
        - 급락 + 거래량 = 숏
        - 급등 + 상승장 = 롱
        """
        if not candles or len(candles) < self.period + 1:
            return None

        closes = [c['close'] for c in candles]
        momentum = self.calculate_momentum(closes)

        if momentum is None:
            return None

        trend = self.regime_detector.detect_market_trend(candles)
        volume_surge = self.volume_confirmation(candles)

        print(f"Momentum: {momentum*100:.2f}%, Trend: {trend}, Volume: {volume_surge}")

        # 거래량 확인 필수
        if not volume_surge:
            return None

        # 강한 하락 모멘텀
        if momentum < -self.threshold:
            # 하락장이나 횡보장에서만 숏
            if trend in ['bear', 'strong_bear', 'ranging']:
                print(f"  [SHORT] 하락 모멘텀 확인")
                return 'short'

        # 강한 상승 모멘텀
        elif momentum > self.threshold:
            # 상승장이나 횡보장에서만 롱
            if trend in ['bull', 'strong_bull', 'ranging']:
                print(f"  [LONG] 상승 모멘텀 확인")
                return 'long'

        return None


class AdaptiveBearMarketStrategy:
    """적응형 하락장 전략 - 시장 상황별 전략 전환"""

    def __init__(self):
        """여러 전략 조합"""
        self.regime_detector = MarketRegimeDetector()
        self.rsi_strategy = BearMarketRSIStrategy(period=9, oversold=20, overbought=70)
        self.momentum_strategy = BearMarketMomentumStrategy(momentum_period=5, threshold=0.005)
        self.period = 50  # 백테스트 호환용

    def analyze(self, candles):
        """
        시장 상황에 따라 전략 전환
        - 강한 하락: 숏 전략만
        - 횡보: RSI 양방향
        - 상승: 롱 위주
        """
        if not candles or len(candles) < self.period:
            return None

        trend = self.regime_detector.detect_market_trend(candles)

        print(f"\n[Market] {trend}")

        # 강한 하락장: 모멘텀 숏 전략
        if trend == 'strong_bear':
            signal = self.momentum_strategy.analyze(candles)
            if signal == 'short':
                return signal
            # 숏 아니면 RSI도 체크
            return self.rsi_strategy.analyze(candles)

        # 일반 하락장: RSI 위주
        elif trend == 'bear':
            return self.rsi_strategy.analyze(candles)

        # 횡보장: RSI
        elif trend == 'ranging':
            return self.rsi_strategy.analyze(candles)

        # 상승장: 롱만
        else:  # bull, strong_bull
            signal = self.rsi_strategy.analyze(candles)
            # 상승장에서 숏 신호는 무시
            if signal == 'short':
                return None
            return signal


if __name__ == "__main__":
    print("Bear market strategies ready")
