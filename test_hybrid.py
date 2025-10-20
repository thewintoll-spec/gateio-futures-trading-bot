"""
하이브리드 전략 최종 비교 테스트
"""
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from hybrid_strategy import HybridStrategy
from ultimate_strategy import UltimateRSIStrategy
from trend_following_strategy import TrendFollowingStrategy


def run_final_comparison():
    """최종 비교: RSI vs 추세추종 vs 하이브리드"""

    print("=" * 80)
    print("최종 전략 비교: RSI vs 추세추종 vs 하이브리드")
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

    LEVERAGE = 3
    CAPITAL_PCT = 0.95

    results = []

    # ===== 1. RSI 전략 =====
    print(f"\n{'='*80}")
    print("1. RSI 평균회귀 전략")
    print(f"{'='*80}")

    rsi_strategy = UltimateRSIStrategy(period=14, oversold=30, overbought=70)
    engine1 = BacktestEngine(initial_capital=10000, leverage=LEVERAGE,
                             maker_fee=0.0002, taker_fee=0.0005)
    result1 = engine1.run(df, rsi_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

    print(f"\n[결과] 수익률: {result1['total_return']:.2f}%, "
          f"거래: {result1['total_trades']}개, "
          f"승률: {result1['win_rate']:.1f}%" if result1['total_trades'] > 0 else "")

    results.append(('RSI 평균회귀', result1))

    # ===== 2. 추세추종 전략 =====
    print(f"\n{'='*80}")
    print("2. 추세추종 전략")
    print(f"{'='*80}")

    trend_strategy = TrendFollowingStrategy(fast_period=12, slow_period=26,
                                           adx_period=14, adx_threshold=25)
    engine2 = BacktestEngine(initial_capital=10000, leverage=LEVERAGE,
                             maker_fee=0.0002, taker_fee=0.0005)
    result2 = engine2.run(df, trend_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

    print(f"\n[결과] 수익률: {result2['total_return']:.2f}%, "
          f"거래: {result2['total_trades']}개, "
          f"승률: {result2['win_rate']:.1f}%" if result2['total_trades'] > 0 else "")

    results.append(('추세추종', result2))

    # ===== 3. 하이브리드 전략 =====
    print(f"\n{'='*80}")
    print("3. 하이브리드 적응형 전략 (ADX 자동 전환)")
    print(f"{'='*80}")

    hybrid_strategy = HybridStrategy(adx_threshold=25, rsi_period=14,
                                     ema_fast=12, ema_slow=26)
    engine3 = BacktestEngine(initial_capital=10000, leverage=LEVERAGE,
                             maker_fee=0.0002, taker_fee=0.0005)
    result3 = engine3.run(df, hybrid_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

    print(f"\n[결과] 수익률: {result3['total_return']:.2f}%, "
          f"거래: {result3['total_trades']}개, "
          f"승률: {result3['win_rate']:.1f}%" if result3['total_trades'] > 0 else "")

    if result3['total_trades'] > 0:
        print(f"\n[전략 사용 통계]")
        print(f"  RSI 전략 사용: {hybrid_strategy.rsi_trades}회 "
              f"({hybrid_strategy.rsi_trades/(hybrid_strategy.rsi_trades + hybrid_strategy.trend_trades)*100:.1f}%)")
        print(f"  추세추종 사용: {hybrid_strategy.trend_trades}회 "
              f"({hybrid_strategy.trend_trades/(hybrid_strategy.rsi_trades + hybrid_strategy.trend_trades)*100:.1f}%)")

    results.append(('하이브리드', result3))

    # ===== 최종 비교표 =====
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

        print(f"{name:<20} {result['total_return']:>11.2f}% "
              f"{result['win_rate']:>9.1f}% " if result['total_trades'] > 0 else f"{'N/A':>9} "
              f"{result.get('max_drawdown', 0):>11.2f}% "
              f"{result['total_trades']:>10} "
              f"{pf:>10.2f}" if result['total_trades'] > 0 else f"{'N/A':>10}")

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

        trades_df = best_result['trades']
        tp_trades = len(trades_df[trades_df['reason'] == 'take_profit'])
        sl_trades = len(trades_df[trades_df['reason'] == 'stop_loss'])
        print(f"\n  TP 도달: {tp_trades}개 ({tp_trades/len(trades_df)*100:.1f}%)")
        print(f"  SL 손절: {sl_trades}개 ({sl_trades/len(trades_df)*100:.1f}%)")

    # 시장 분석
    print(f"\n{'='*80}")
    print("시장 분석")
    print(f"{'='*80}")
    print(f"시장 변동: {market_change:+.2f}%")

    if market_change < -5:
        print("→ 하락장: 추세추종이 유리했을 것 (숏으로 수익)")
    elif market_change > 5:
        print("→ 상승장: 추세추종이 유리했을 것 (롱으로 수익)")
    else:
        print("→ 횡보장: RSI 평균회귀가 유리했을 것")

    print(f"\n하이브리드 전략은 시장 상태를 자동 판단하여")
    print(f"최적의 전략을 선택합니다.")

    # 개선 여부
    print(f"\n{'='*80}")
    print("개선 효과")
    print(f"{'='*80}")

    rsi_return = result1['total_return']
    hybrid_return = result3['total_return']
    improvement = hybrid_return - rsi_return

    if improvement > 0:
        print(f"하이브리드가 RSI 대비 {improvement:+.2f}%p 더 나음!")
    else:
        print(f"하이브리드가 RSI 대비 {improvement:+.2f}%p 차이")

    print(f"\n시장 환경: {market_change:+.2f}% 변동")
    print(f"레버리지: {LEVERAGE}배")


if __name__ == "__main__":
    run_final_comparison()
