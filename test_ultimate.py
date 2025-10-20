"""
종합 개선 전략 백테스트

개선 사항:
1. 반전 청산 제거 (allow_reversal=False)
2. 레버리지 낮춤 (5x → 3x)
3. TP/SL 최적화 (TP 3%, SL 2%)
4. 추세 필터 추가
5. 엄격한 진입 조건
"""
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from ultimate_strategy import UltimateRSIStrategy
from improved_strategy_v2 import ImprovedRSIStrategyV2


def run_ultimate_test():
    """종합 개선 전략 vs 기존 전략"""

    print("=" * 80)
    print("종합 개선 전략 백테스트")
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

    # ===== 기존 전략 (반전 청산 있음, 5배 레버리지) =====
    print(f"\n{'='*80}")
    print("1. 기존 전략 (반전 청산 ON, 5배 레버리지)")
    print(f"{'='*80}")

    old_strategy = ImprovedRSIStrategyV2(period=9, oversold=25, overbought=65)

    engine1 = BacktestEngine(
        initial_capital=10000,
        leverage=5,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result1 = engine1.run(df, old_strategy, capital_pct=0.95, allow_reversal=True)

    print(f"\n[결과]")
    print(f"  수익률: {result1['total_return']:.2f}%")
    print(f"  거래수: {result1['total_trades']}")
    if result1['total_trades'] > 0:
        print(f"  승률: {result1['win_rate']:.1f}%")
        print(f"  MDD: {result1.get('max_drawdown', 0):.2f}%")

        trades_df = result1['trades']
        tp_trades = trades_df[trades_df['reason'] == 'take_profit']
        sl_trades = trades_df[trades_df['reason'] == 'stop_loss']
        reverse_trades = trades_df[trades_df['reason'] == 'reverse']

        print(f"\n  TP: {len(tp_trades)}개 ({len(tp_trades)/len(trades_df)*100:.1f}%)")
        print(f"  SL: {len(sl_trades)}개 ({len(sl_trades)/len(trades_df)*100:.1f}%)")
        print(f"  반전: {len(reverse_trades)}개 ({len(reverse_trades)/len(trades_df)*100:.1f}%)")

    # ===== 종합 개선 전략 (반전 청산 없음, 3배 레버리지) =====
    print(f"\n{'='*80}")
    print("2. 종합 개선 전략 (반전 청산 OFF, 3배 레버리지)")
    print(f"{'='*80}")
    print("개선 사항:")
    print("  - 반전 청산 제거 (TP/SL만)")
    print("  - 레버리지 5x → 3x")
    print("  - TP/SL: 3% / 2% (Risk:Reward 1:1.5)")
    print("  - 추세 필터 (강한 추세장 회피)")
    print("  - RSI 30/70 (더 보수적)")
    print("  - 거래 간격 30분")
    print("")

    ultimate_strategy = UltimateRSIStrategy(period=14, oversold=30, overbought=70)

    engine2 = BacktestEngine(
        initial_capital=10000,
        leverage=3,  # 레버리지 낮춤
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result2 = engine2.run(df, ultimate_strategy, capital_pct=0.95, allow_reversal=False)

    print(f"\n[결과]")
    print(f"  수익률: {result2['total_return']:.2f}%")
    print(f"  거래수: {result2['total_trades']}")
    if result2['total_trades'] > 0:
        print(f"  승률: {result2['win_rate']:.1f}%")
        print(f"  MDD: {result2.get('max_drawdown', 0):.2f}%")

        trades_df = result2['trades']
        tp_trades = trades_df[trades_df['reason'] == 'take_profit']
        sl_trades = trades_df[trades_df['reason'] == 'stop_loss']
        reverse_trades = trades_df[trades_df['reason'] == 'reverse']

        print(f"\n  TP: {len(tp_trades)}개 ({len(tp_trades)/len(trades_df)*100:.1f}%)")
        print(f"  SL: {len(sl_trades)}개 ({len(sl_trades)/len(trades_df)*100:.1f}%)")
        print(f"  반전: {len(reverse_trades)}개 ({len(reverse_trades)/len(trades_df)*100:.1f}%)")

        long_trades = trades_df[trades_df['side'] == 'long']
        short_trades = trades_df[trades_df['side'] == 'short']
        print(f"\n  롱: {len(long_trades)}개, PnL: {long_trades['pnl'].sum():+.2f}")
        print(f"  숏: {len(short_trades)}개, PnL: {short_trades['pnl'].sum():+.2f}")

        # Profit Factor
        winning = trades_df[trades_df['pnl'] > 0]
        losing = trades_df[trades_df['pnl'] <= 0]
        if len(winning) > 0 and len(losing) > 0:
            pf = winning['pnl'].sum() / abs(losing['pnl'].sum())
            print(f"\n  Profit Factor: {pf:.2f}")

    # ===== 비교 =====
    print(f"\n{'='*80}")
    print("비교 결과")
    print(f"{'='*80}")
    print(f"{'항목':<20} {'기존 (5x)':>15} {'개선 (3x)':>15} {'차이':>15}")
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

    # 반전 청산 비교
    if result1['total_trades'] > 0:
        old_reverse = len(result1['trades'][result1['trades']['reason'] == 'reverse'])
        old_reverse_pct = old_reverse / result1['total_trades'] * 100
    else:
        old_reverse_pct = 0

    if result2['total_trades'] > 0:
        new_reverse = len(result2['trades'][result2['trades']['reason'] == 'reverse'])
        new_reverse_pct = new_reverse / result2['total_trades'] * 100
    else:
        new_reverse_pct = 0

    print(f"{'반전 청산 비율':<20} {old_reverse_pct:>14.1f}% {new_reverse_pct:>14.1f}% "
          f"{new_reverse_pct - old_reverse_pct:>+14.1f}%p")

    print("=" * 80)

    # 결론
    if result2['total_return'] > result1['total_return']:
        improvement = result2['total_return'] - result1['total_return']
        print(f"\n[OK] 종합 개선 전략 승리!")
        print(f"  수익률 개선: {improvement:+.2f}%p")
        if result2['total_trades'] > 0:
            print(f"  승률: {result2['win_rate']:.1f}%")
            print(f"  MDD 개선: {result1.get('max_drawdown', 0) - result2.get('max_drawdown', 0):+.2f}%p")
    else:
        loss = result1['total_return'] - result2['total_return']
        print(f"\n[X] 종합 개선 실패")
        print(f"  수익률 악화: {-loss:+.2f}%p")
        print(f"  하지만 MDD는 개선: {result1.get('max_drawdown', 0) - result2.get('max_drawdown', 0):+.2f}%p")


if __name__ == "__main__":
    run_ultimate_test()
