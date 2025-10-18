"""
개선된 전략 v2 백테스트 (동적 테이크프로핏)
"""
from backtest.data_loader import DataLoader
from backtest.backtest import BacktestEngine
from improved_strategy_v2 import ImprovedRSIStrategyV2
from scalping_strategy import ScalpingRSIStrategy
import config


def run_v2_test():
    """v2 전략 테스트"""

    print("=" * 80)
    print("개선된 전략 v2 백테스트 (동적 테이크프로핏)")
    print("=" * 80)

    # 데이터 로드
    loader = DataLoader(config.SYMBOL, testnet=config.TESTNET)
    df = loader.fetch_historical_data(interval='5m', days=30)

    if df is None or len(df) == 0:
        print("데이터 로드 실패!")
        return

    print(f"\n데이터: {len(df)} 캔들")
    print(f"기간: {df['datetime'].min()} ~ {df['datetime'].max()}")
    market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
    print(f"시장 변동: {market_change:+.2f}%")

    # 파라미터
    LEVERAGE = 5
    CAPITAL_PCT = 0.95

    # 1. 기존 전략 (고정 TP 5%)
    print(f"\n{'='*80}")
    print("1. 기존 RSI 전략 (고정 TP 5%)")
    print(f"{'='*80}")

    original_strategy = ScalpingRSIStrategy(period=9, oversold=25, overbought=65)

    engine1 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result1 = engine1.run(df, original_strategy, capital_pct=CAPITAL_PCT)

    print(f"\n[결과]")
    print(f"  수익률: {result1['total_return']:.2f}%")
    print(f"  거래수: {result1['total_trades']}")
    if result1['total_trades'] > 0:
        print(f"  승률: {result1['win_rate']:.1f}%")
        print(f"  MDD: {result1.get('max_drawdown', 0):.2f}%")

        trades_df = result1['trades']
        long_trades = trades_df[trades_df['side'] == 'long']
        short_trades = trades_df[trades_df['side'] == 'short']

        print(f"\n  롱: {len(long_trades)}개, PnL: {long_trades['pnl'].sum():+.2f}")
        print(f"  숏: {len(short_trades)}개, PnL: {short_trades['pnl'].sum():+.2f}")

    # 2. 개선 전략 v2 (동적 TP)
    print(f"\n{'='*80}")
    print("2. 개선 전략 v2 (동적 TP: 5~15%)")
    print(f"{'='*80}")

    improved_v2_strategy = ImprovedRSIStrategyV2(period=9, oversold=25, overbought=65)

    engine2 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result2 = engine2.run(df, improved_v2_strategy, capital_pct=CAPITAL_PCT)

    print(f"\n[결과]")
    print(f"  수익률: {result2['total_return']:.2f}%")
    print(f"  거래수: {result2['total_trades']}")
    if result2['total_trades'] > 0:
        print(f"  승률: {result2['win_rate']:.1f}%")
        print(f"  MDD: {result2.get('max_drawdown', 0):.2f}%")

        trades_df = result2['trades']
        long_trades = trades_df[trades_df['side'] == 'long']
        short_trades = trades_df[trades_df['side'] == 'short']

        print(f"\n  롱: {len(long_trades)}개, PnL: {long_trades['pnl'].sum():+.2f}")
        print(f"  숏: {len(short_trades)}개, PnL: {short_trades['pnl'].sum():+.2f}")

        # TP 분포 분석
        print(f"\n  [동적 TP 분석]")
        tp_reasons = trades_df[trades_df['reason'] == 'take_profit']
        sl_reasons = trades_df[trades_df['reason'] == 'stop_loss']
        print(f"  TP 도달: {len(tp_reasons)}개 ({len(tp_reasons)/len(trades_df)*100:.1f}%)")
        print(f"  SL 손절: {len(sl_reasons)}개 ({len(sl_reasons)/len(trades_df)*100:.1f}%)")

    # 비교
    print(f"\n{'='*80}")
    print("비교 결과")
    print(f"{'='*80}")
    print(f"{'항목':<20} {'기존 전략':>15} {'개선 v2':>15} {'개선도':>15}")
    print("-" * 80)

    print(f"{'수익률':<20} {result1['total_return']:>14.2f}% {result2['total_return']:>14.2f}% "
          f"{result2['total_return'] - result1['total_return']:>+14.2f}%p")

    if result1['total_trades'] > 0 and result2['total_trades'] > 0:
        print(f"{'승률':<20} {result1['win_rate']:>14.1f}% {result2['win_rate']:>14.1f}% "
              f"{result2['win_rate'] - result1['win_rate']:>+14.1f}%p")

        print(f"{'MDD':<20} {result1.get('max_drawdown', 0):>14.2f}% "
              f"{result2.get('max_drawdown', 0):>14.2f}% "
              f"{result2.get('max_drawdown', 0) - result1.get('max_drawdown', 0):>+14.2f}%p")

    print(f"{'거래수':<20} {result1['total_trades']:>15} {result2['total_trades']:>15} "
          f"{result2['total_trades'] - result1['total_trades']:>+15}")

    print("=" * 80)

    # 결론
    if result2['total_return'] > result1['total_return']:
        print("\n결론: 개선 v2 전략이 더 나은 성과!")
        print(f"  수익률 개선: {result2['total_return'] - result1['total_return']:+.2f}%p")
        if result2['total_trades'] > 0:
            print(f"  승률: {result2['win_rate']:.1f}%")
            print(f"  거래수: {result2['total_trades']}개 (기존: {result1['total_trades']}개)")
    else:
        print("\n결론: 추가 개선 필요")
        print(f"  수익률 차이: {result2['total_return'] - result1['total_return']:+.2f}%p")


if __name__ == "__main__":
    run_v2_test()
