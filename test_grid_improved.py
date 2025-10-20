"""
개선된 그리드 전략 테스트

개선 사항:
1. 타이트한 손절 (3.5% → 1.0~2.0%)
2. 추세 필터 (강한 추세 시 진입 제한)
3. 동적 손절 (ATR 기반)
"""
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from grid_strategy import GridTradingStrategy


def test_improved_grid():
    """개선된 그리드 vs 기본 그리드 비교"""

    print("=" * 80)
    print("개선된 그리드 전략 테스트")
    print("=" * 80)

    # 데이터 로드
    loader = BinanceDataLoader(symbol='ETHUSDT')
    df = loader.fetch_historical_data(interval='5m', days=30)

    if df is None or len(df) == 0:
        print("데이터 로드 실패!")
        return

    print(f"\n데이터: {len(df)} 캔들")
    print(f"기간: {df['datetime'].min()} ~ {df['datetime'].max()}")
    market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
    print(f"시장 변동: {market_change:+.2f}%")

    LEVERAGE = 2
    CAPITAL_PCT = 0.90

    results = []

    # ===== 1. 기본 그리드 =====
    print(f"\n{'='*80}")
    print("1. 기본 그리드 (개선 전)")
    print(f"{'='*80}")
    print("설정: 타이트 SL OFF, 추세필터 OFF")

    basic_strategy = GridTradingStrategy(
        num_grids=30,
        range_pct=10.0,
        profit_per_grid=0.3,
        max_positions=10,
        rebalance_threshold=7.0,
        tight_sl=False,
        use_trend_filter=False,
        dynamic_sl=False
    )

    engine1 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result1 = engine1.run(df, basic_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

    print(f"\n[결과]")
    print(f"  수익률: {result1['total_return']:.2f}%")
    print(f"  거래수: {result1['total_trades']}")
    if result1['total_trades'] > 0:
        print(f"  승률: {result1['win_rate']:.1f}%")
        print(f"  MDD: {result1.get('max_drawdown', 0):.2f}%")

        trades_df = result1['trades']
        tp_trades = trades_df[trades_df['reason'] == 'take_profit']
        sl_trades = trades_df[trades_df['reason'] == 'stop_loss']

        print(f"\n  TP: {len(tp_trades)}개 ({len(tp_trades)/len(trades_df)*100:.1f}%)")
        print(f"  SL: {len(sl_trades)}개 ({len(sl_trades)/len(trades_df)*100:.1f}%)")

        if len(sl_trades) > 0:
            print(f"  평균 SL 손실: {sl_trades['pnl'].mean():.2f} USDT")

    results.append(('기본 그리드', result1))

    # ===== 2. 타이트 SL만 =====
    print(f"\n{'='*80}")
    print("2. 타이트 SL 적용")
    print(f"{'='*80}")
    print("설정: 타이트 SL ON (1.0~2.0%), 추세필터 OFF")

    tight_sl_strategy = GridTradingStrategy(
        num_grids=30,
        range_pct=10.0,
        profit_per_grid=0.3,
        max_positions=10,
        rebalance_threshold=7.0,
        tight_sl=True,
        use_trend_filter=False,
        dynamic_sl=True
    )

    engine2 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result2 = engine2.run(df, tight_sl_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

    print(f"\n[결과]")
    print(f"  수익률: {result2['total_return']:.2f}%")
    print(f"  거래수: {result2['total_trades']}")
    if result2['total_trades'] > 0:
        print(f"  승률: {result2['win_rate']:.1f}%")
        print(f"  MDD: {result2.get('max_drawdown', 0):.2f}%")

        trades_df = result2['trades']
        tp_trades = trades_df[trades_df['reason'] == 'take_profit']
        sl_trades = trades_df[trades_df['reason'] == 'stop_loss']

        print(f"\n  TP: {len(tp_trades)}개")
        print(f"  SL: {len(sl_trades)}개")

        if len(sl_trades) > 0:
            print(f"  평균 SL 손실: {sl_trades['pnl'].mean():.2f} USDT")

    results.append(('타이트 SL', result2))

    # ===== 3. 추세필터만 =====
    print(f"\n{'='*80}")
    print("3. 추세 필터 적용")
    print(f"{'='*80}")
    print("설정: 타이트 SL OFF, 추세필터 ON")

    trend_filter_strategy = GridTradingStrategy(
        num_grids=30,
        range_pct=10.0,
        profit_per_grid=0.3,
        max_positions=10,
        rebalance_threshold=7.0,
        tight_sl=False,
        use_trend_filter=True,
        dynamic_sl=False
    )

    engine3 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result3 = engine3.run(df, trend_filter_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

    print(f"\n[결과]")
    print(f"  수익률: {result3['total_return']:.2f}%")
    print(f"  거래수: {result3['total_trades']}")
    if result3['total_trades'] > 0:
        print(f"  승률: {result3['win_rate']:.1f}%")
        print(f"  MDD: {result3.get('max_drawdown', 0):.2f}%")

    results.append(('추세필터', result3))

    # ===== 4. 모든 개선 적용 =====
    print(f"\n{'='*80}")
    print("4. 모든 개선 사항 적용 (최종)")
    print(f"{'='*80}")
    print("설정: 타이트 SL ON, 추세필터 ON, 동적 SL ON")

    improved_strategy = GridTradingStrategy(
        num_grids=30,
        range_pct=10.0,
        profit_per_grid=0.3,
        max_positions=10,
        rebalance_threshold=7.0,
        tight_sl=True,
        use_trend_filter=True,
        dynamic_sl=True
    )

    engine4 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result4 = engine4.run(df, improved_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

    print(f"\n[결과]")
    print(f"  수익률: {result4['total_return']:.2f}%")
    print(f"  거래수: {result4['total_trades']}")
    if result4['total_trades'] > 0:
        print(f"  승률: {result4['win_rate']:.1f}%")
        print(f"  MDD: {result4.get('max_drawdown', 0):.2f}%")

        trades_df = result4['trades']
        tp_trades = trades_df[trades_df['reason'] == 'take_profit']
        sl_trades = trades_df[trades_df['reason'] == 'stop_loss']

        print(f"\n  TP: {len(tp_trades)}개")
        print(f"  SL: {len(sl_trades)}개")

        if len(sl_trades) > 0:
            print(f"  평균 SL 손실: {sl_trades['pnl'].mean():.2f} USDT")

        # Profit Factor
        winning = trades_df[trades_df['pnl'] > 0]
        losing = trades_df[trades_df['pnl'] <= 0]
        if len(winning) > 0 and len(losing) > 0:
            pf = winning['pnl'].sum() / abs(losing['pnl'].sum())
            print(f"\n  Profit Factor: {pf:.2f}")

    results.append(('개선 적용', result4))

    # ===== 비교표 =====
    print(f"\n{'='*80}")
    print("비교 결과")
    print(f"{'='*80}")
    print(f"{'전략':<20} {'수익률':>12} {'승률':>10} {'MDD':>12} {'거래수':>10}")
    print("-" * 80)

    for name, result in results:
        win_rate_str = f"{result['win_rate']:.1f}%" if result['total_trades'] > 0 else "N/A"

        print(f"{name:<20} {result['total_return']:>11.2f}% "
              f"{win_rate_str:>9} "
              f"{result.get('max_drawdown', 0):>11.2f}% "
              f"{result['total_trades']:>10}")

    print("=" * 80)

    # 최고 성과
    best = max(results, key=lambda x: x[1]['total_return'])
    print(f"\n최고 성과: {best[0]} ({best[1]['total_return']:+.2f}%)")

    # 개선도
    baseline = result1['total_return']
    improved = result4['total_return']
    improvement = improved - baseline

    print(f"\n기본 → 개선: {improvement:+.2f}%p")

    if improved > 0:
        print(f"\n[대성공] 플러스 수익 달성! ({improved:+.2f}%)")
    elif improvement > 0:
        print(f"\n[개선] 손실 {abs(improvement):.2f}%p 감소!")
    else:
        print(f"\n[실패] 개선 효과 없음")


if __name__ == "__main__":
    test_improved_grid()
