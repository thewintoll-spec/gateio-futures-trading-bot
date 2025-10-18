"""
역발상 전략 백테스트 (Binance 30일 데이터)
"""
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from inverse_strategy import InverseRSIStrategy
from improved_strategy_v2 import ImprovedRSIStrategyV2


def run_inverse_test_binance():
    """역발상 전략 vs 정방향 전략 (Binance 30일 데이터)"""

    print("=" * 80)
    print("역발상 전략 백테스트 - Binance 30일 데이터")
    print("=" * 80)

    # Binance 데이터 로드 (30일)
    loader = BinanceDataLoader(symbol='ETHUSDT')
    df = loader.fetch_historical_data(interval='5m', days=30)

    if df is None or len(df) == 0:
        print("데이터 로드 실패!")
        return

    print(f"\n데이터: {len(df)} 캔들")
    print(f"기간: {df['datetime'].min()} ~ {df['datetime'].max()}")
    market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
    print(f"시장 변동: {market_change:+.2f}%")

    LEVERAGE = 5
    CAPITAL_PCT = 0.95

    # 1. 정방향 전략 (개선 v2)
    print(f"\n{'='*80}")
    print("1. 정방향 전략 (개선 v2)")
    print(f"{'='*80}")

    normal_strategy = ImprovedRSIStrategyV2(period=9, oversold=25, overbought=65)

    engine1 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result1 = engine1.run(df, normal_strategy, capital_pct=CAPITAL_PCT)

    print(f"\n[결과]")
    print(f"  수익률: {result1['total_return']:.2f}%")
    print(f"  거래수: {result1['total_trades']}")
    if result1['total_trades'] > 0:
        print(f"  승률: {result1['win_rate']:.1f}%")
        print(f"  MDD: {result1.get('max_drawdown', 0):.2f}%")

        trades_df = result1['trades']
        tp_trades = trades_df[trades_df['reason'] == 'take_profit']
        sl_trades = trades_df[trades_df['reason'] == 'stop_loss']
        print(f"  TP 도달: {len(tp_trades)}개 ({len(tp_trades)/len(trades_df)*100:.1f}%)")
        print(f"  SL 손절: {len(sl_trades)}개 ({len(sl_trades)/len(trades_df)*100:.1f}%)")

        long_trades = trades_df[trades_df['side'] == 'long']
        short_trades = trades_df[trades_df['side'] == 'short']
        print(f"\n  롱: {len(long_trades)}개, PnL: {long_trades['pnl'].sum():+.2f}")
        print(f"  숏: {len(short_trades)}개, PnL: {short_trades['pnl'].sum():+.2f}")

    # 2. 역발상 전략
    print(f"\n{'='*80}")
    print("2. 역발상 전략 (Inverse)")
    print(f"{'='*80}")

    inverse_strategy = InverseRSIStrategy(period=9, oversold=25, overbought=65)

    engine2 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result2 = engine2.run(df, inverse_strategy, capital_pct=CAPITAL_PCT)

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

        tp_trades = trades_df[trades_df['reason'] == 'take_profit']
        sl_trades = trades_df[trades_df['reason'] == 'stop_loss']
        print(f"\n  TP 도달: {len(tp_trades)}개 ({len(tp_trades)/len(trades_df)*100:.1f}%)")
        print(f"  SL 손절: {len(sl_trades)}개 ({len(sl_trades)/len(trades_df)*100:.1f}%)")

    # 비교
    print(f"\n{'='*80}")
    print("비교 결과 (30일 데이터)")
    print(f"{'='*80}")
    print(f"{'항목':<20} {'정방향':>15} {'역발상':>15} {'차이':>15}")
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
        print(f"\n[OK] 결론: 역발상 전략 승리!")
        print(f"  수익률 개선: {result2['total_return'] - result1['total_return']:+.2f}%p")
        if result2['total_trades'] > 0:
            print(f"  승률: {result2['win_rate']:.1f}%")
            print(f"  거래수: {result2['total_trades']}개")
    else:
        print(f"\n[X] 결론: 정방향 전략 승리")
        print(f"  수익률 차이: {result1['total_return'] - result2['total_return']:+.2f}%p")

    # 시장 상황 분석
    print(f"\n시장 상황:")
    print(f"  전체 변동: {market_change:+.2f}%")
    if market_change > 5:
        print(f"  → 강한 상승장 (역발상 불리)")
    elif market_change < -5:
        print(f"  → 강한 하락장 (역발상 불리)")
    else:
        print(f"  → 박스권/횡보장 (역발상 유리)")


if __name__ == "__main__":
    run_inverse_test_binance()
