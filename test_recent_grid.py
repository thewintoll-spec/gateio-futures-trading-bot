"""
최근 4일간 Grid 전략 백테스트 (10월 23일 02:42:25 이후)
실제로 횡보장이 아니어서 진입을 안 한 건지 확인
"""
import sys
sys.path.append('backtest')
from datetime import datetime
from binance_data_loader import BinanceDataLoader
from grid_strategy import GridTradingStrategy


def analyze_market_regime(candles):
    """시장 상태 분석"""
    strategy = GridTradingStrategy(
        num_grids=30,
        range_pct=10.0,
        profit_per_grid=0.3,
        max_positions=10,
        rebalance_threshold=7.0,
        tight_sl=True,
        use_trend_filter=True,
        dynamic_sl=True
    )

    # ADX 계산
    adx, plus_di, minus_di = strategy.calculate_adx(candles, 14)
    regime = strategy.detect_market_regime(candles)

    return {
        'adx': adx,
        'plus_di': plus_di,
        'minus_di': minus_di,
        'regime': regime
    }


def simple_backtest(candles, symbol):
    """간단한 백테스트"""
    strategy = GridTradingStrategy(
        num_grids=30,
        range_pct=10.0,
        profit_per_grid=0.3,
        max_positions=10,
        rebalance_threshold=7.0,
        tight_sl=True,
        use_trend_filter=True,  # ADX 필터 ON
        dynamic_sl=True
    )

    signals = []
    for i in range(100, len(candles)):
        window = candles[i-100:i+1]
        signal = strategy.analyze(window)

        if signal:
            signals.append({
                'time': window[-1]['timestamp'],
                'price': window[-1]['close'],
                'signal': signal
            })

    return signals


def main():
    # 백테스트 기간
    start_date = datetime(2025, 10, 23, 2, 42, 25)
    end_date = datetime.now()
    days = (end_date - start_date).days + 1

    print("=" * 80)
    print("최근 4일간 Grid 전략 백테스트")
    print("=" * 80)
    print(f"기간: {start_date} ~ {end_date}")
    print(f"총 기간: {(end_date - start_date).total_seconds() / 3600:.1f}시간")
    print("=" * 80)

    for symbol in ['BTC/USDT', 'ETH/USDT']:
        print(f"\n{'='*80}")
        print(f"{symbol} 분석")
        print(f"{'='*80}")

        # 심볼 변환 (BTC/USDT -> BTCUSDT)
        binance_symbol = symbol.replace('/', '')

        # 데이터 로더 생성
        loader = BinanceDataLoader(symbol=binance_symbol)

        # 데이터 로드
        print(f"데이터 로딩 중...")
        df = loader.fetch_historical_data(interval='5m', days=days)

        if df is None:
            print(f"❌ 데이터 로드 실패")
            continue

        # DataFrame을 candles 리스트로 변환
        candles = df.to_dict('records')

        if not candles:
            print(f"[X] 데이터 로드 실패")
            continue

        print(f"[OK] 총 {len(candles)}개 캔들 로드 완료")

        # 현재 시장 상태
        print(f"\n[현재 시장 상태]")
        regime_info = analyze_market_regime(candles)
        print(f"  ADX: {regime_info['adx']:.2f}")
        print(f"  +DI: {regime_info['plus_di']:.2f}")
        print(f"  -DI: {regime_info['minus_di']:.2f}")
        print(f"  시장 상태: {regime_info['regime']}")

        if regime_info['regime'] == 'ranging':
            print(f"  -> 횡보장 (Grid 전략 활성)")
        elif regime_info['regime'] == 'trending_up':
            print(f"  -> 상승 추세 (Grid 전략 필터링)")
        else:
            print(f"  -> 하락 추세 (Grid 전략 필터링)")

        # 신호 분석
        print(f"\n[신호 분석]")
        signals = simple_backtest(candles, symbol)

        print(f"  총 신호 수: {len(signals)}건")

        if len(signals) > 0:
            print(f"\n  최근 신호 5건:")
            for sig in signals[-5:]:
                print(f"    {sig['time']} | ${sig['price']:.2f} | {sig['signal']['signal'].upper()}")
        else:
            print(f"  [경고] 신호 없음")
            print(f"  -> ADX 필터가 모든 신호를 걸러냈을 가능성")

        # 시간대별 ADX 분석 (1시간 간격으로 샘플링)
        print(f"\n[시간대별 시장 상태 (6시간 간격 샘플링)]")
        interval = 72  # 6시간 = 72 * 5분

        for i in range(100, len(candles), interval):
            window = candles[max(0, i-100):i+1]
            if len(window) < 100:
                continue

            regime_info = analyze_market_regime(window)
            timestamp = window[-1]['timestamp']

            regime_symbol = {
                'ranging': '[RANGE]',
                'trending_up': '[UP   ]',
                'trending_down': '[DOWN ]'
            }.get(regime_info['regime'], '[?????]')

            print(f"  {timestamp} | ADX: {regime_info['adx']:5.1f} | {regime_symbol} {regime_info['regime']}")

        print(f"\n{'='*80}")


if __name__ == "__main__":
    main()
