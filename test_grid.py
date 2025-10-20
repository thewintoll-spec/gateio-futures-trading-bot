"""
그리드 트레이딩 전략 백테스트

기존 전략들과 비교:
- RSI 평균회귀
- 추세추종
- 하이브리드
- 그리드 트레이딩 (NEW)
"""
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from grid_strategy import GridTradingStrategy
from hybrid_strategy import HybridStrategy
from ultimate_strategy import UltimateRSIStrategy


def run_grid_test():
    """그리드 vs 기존 전략들 비교"""

    print("=" * 80)
    print("그리드 트레이딩 전략 백테스트")
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

    LEVERAGE = 2  # 그리드는 2배로 안정적으로
    CAPITAL_PCT = 0.90

    results = []

    # ===== 1. 그리드 트레이딩 전략 (NEW) =====
    print(f"\n{'='*80}")
    print("1. 그리드 트레이딩 전략 (Grid Trading)")
    print(f"{'='*80}")
    print("전략:")
    print("  - 현재가 기준 ±5% 범위, 10개 그리드")
    print("  - 하락 시 매수, 상승 시 매도")
    print("  - 각 그리드당 1% 수익 목표")
    print("  - 최대 5개 동시 포지션")
    print("")

    grid_strategy = GridTradingStrategy(
        num_grids=10,
        range_pct=5.0,
        profit_per_grid=1.0,
        rebalance_threshold=7.0,
        max_positions=5
    )

    engine1 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result1 = engine1.run(df, grid_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

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

        # Profit Factor
        winning = trades_df[trades_df['pnl'] > 0]
        losing = trades_df[trades_df['pnl'] <= 0]
        if len(winning) > 0 and len(losing) > 0:
            pf = winning['pnl'].sum() / abs(losing['pnl'].sum())
            print(f"\n  Profit Factor: {pf:.2f}")

        # 그리드 통계
        stats = grid_strategy.get_statistics()
        if stats['most_hit_grid'][0] is not None:
            print(f"\n  가장 활성 그리드: Level {stats['most_hit_grid'][0]} ({stats['most_hit_grid'][1]}회)")

    results.append(('그리드 트레이딩', result1))

    # ===== 2. RSI 평균회귀 (기존) =====
    print(f"\n{'='*80}")
    print("2. RSI 평균회귀 전략 (비교용)")
    print(f"{'='*80}")

    rsi_strategy = UltimateRSIStrategy(period=14, oversold=30, overbought=70)

    engine2 = BacktestEngine(
        initial_capital=10000,
        leverage=3,  # RSI는 3배
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result2 = engine2.run(df, rsi_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

    print(f"\n[결과]")
    print(f"  수익률: {result2['total_return']:.2f}%")
    print(f"  거래수: {result2['total_trades']}")
    if result2['total_trades'] > 0:
        print(f"  승률: {result2['win_rate']:.1f}%")
        print(f"  MDD: {result2.get('max_drawdown', 0):.2f}%")

    results.append(('RSI 평균회귀', result2))

    # ===== 3. 하이브리드 (기존) =====
    print(f"\n{'='*80}")
    print("3. 하이브리드 적응형 전략 (비교용)")
    print(f"{'='*80}")

    hybrid_strategy = HybridStrategy(adx_threshold=25, rsi_period=14,
                                     ema_fast=12, ema_slow=26)

    engine3 = BacktestEngine(
        initial_capital=10000,
        leverage=3,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result3 = engine3.run(df, hybrid_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

    print(f"\n[결과]")
    print(f"  수익률: {result3['total_return']:.2f}%")
    print(f"  거래수: {result3['total_trades']}")
    if result3['total_trades'] > 0:
        print(f"  승률: {result3['win_rate']:.1f}%")
        print(f"  MDD: {result3.get('max_drawdown', 0):.2f}%")

    results.append(('하이브리드', result3))

    # ===== 비교표 =====
    print(f"\n{'='*80}")
    print("최종 비교 결과")
    print(f"{'='*80}")
    print(f"{'전략':<20} {'수익률':>12} {'승률':>10} {'MDD':>12} {'거래수':>10} {'PF':>10}")
    print("-" * 80)

    for name, result in results:
        pf = 0
        if result['total_trades'] > 0:
            trades_df = result['trades']
            winning = trades_df[trades_df['pnl'] > 0]
            losing = trades_df[trades_df['pnl'] <= 0]
            if len(winning) > 0 and len(losing) > 0:
                pf = winning['pnl'].sum() / abs(losing['pnl'].sum())

        win_rate_str = f"{result['win_rate']:.1f}%" if result['total_trades'] > 0 else "N/A"
        pf_str = f"{pf:.2f}" if result['total_trades'] > 0 and pf > 0 else "N/A"

        print(f"{name:<20} {result['total_return']:>11.2f}% "
              f"{win_rate_str:>9} "
              f"{result.get('max_drawdown', 0):>11.2f}% "
              f"{result['total_trades']:>10} "
              f"{pf_str:>10}")

    print("=" * 80)

    # ===== 승자 선정 =====
    best_strategy = max(results, key=lambda x: x[1]['total_return'])
    best_name, best_result = best_strategy

    print(f"\n{'='*80}")
    print("결론")
    print(f"{'='*80}")

    print(f"\n최고 성과 전략: {best_name}")
    print(f"  수익률: {best_result['total_return']:.2f}%")
    if best_result['total_trades'] > 0:
        print(f"  승률: {best_result['win_rate']:.1f}%")
        print(f"  MDD: {best_result.get('max_drawdown', 0):.2f}%")
        print(f"  거래수: {best_result['total_trades']}개")

    # 그리드와 기존 전략 비교
    grid_return = result1['total_return']
    rsi_return = result2['total_return']
    hybrid_return = result3['total_return']

    print(f"\n{'='*80}")
    print("그리드 트레이딩 vs 기존 전략")
    print(f"{'='*80}")

    print(f"\n그리드 vs RSI: {grid_return - rsi_return:+.2f}%p")
    print(f"그리드 vs 하이브리드: {grid_return - hybrid_return:+.2f}%p")

    if grid_return > rsi_return and grid_return > hybrid_return:
        print(f"\n[성공] 그리드 트레이딩이 모든 전략을 능가!")
        improvement = min(grid_return - rsi_return, grid_return - hybrid_return)
        print(f"  최소 개선: {improvement:+.2f}%p")
    elif grid_return > 0:
        print(f"\n[부분 성공] 그리드 트레이딩이 플러스 수익!")
        print(f"  수익률: {grid_return:+.2f}%")
    else:
        print(f"\n[개선 필요] 그리드도 마이너스")
        print(f"  하지만 손실 최소화: {grid_return:.2f}%")

    # 시장 분석
    print(f"\n{'='*80}")
    print("시장 환경 분석")
    print(f"{'='*80}")
    print(f"시장 변동: {market_change:+.2f}%")

    if abs(market_change) < 3:
        print("→ 횡보장: 그리드 트레이딩에 최적!")
    elif market_change < -5:
        print("→ 하락장: 그리드도 불리, 하지만 손실 최소화")
    elif market_change > 5:
        print("→ 상승장: 그리드도 불리, 하지만 손실 최소화")


if __name__ == "__main__":
    run_grid_test()
