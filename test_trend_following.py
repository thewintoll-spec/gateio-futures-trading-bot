"""
추세추종 전략 vs RSI 전략 비교
"""
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from trend_following_strategy import TrendFollowingStrategy
from ultimate_strategy import UltimateRSIStrategy


def run_trend_test():
    """추세추종 vs RSI 비교"""

    print("=" * 80)
    print("추세추종 전략 vs RSI 전략")
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

    # ===== RSI 전략 (Ultimate) =====
    print(f"\n{'='*80}")
    print("1. RSI 평균회귀 전략 (Ultimate)")
    print(f"{'='*80}")

    rsi_strategy = UltimateRSIStrategy(period=14, oversold=30, overbought=70)

    engine1 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result1 = engine1.run(df, rsi_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

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

        long_trades = trades_df[trades_df['side'] == 'long']
        short_trades = trades_df[trades_df['side'] == 'short']
        print(f"\n  롱: {len(long_trades)}개, PnL: {long_trades['pnl'].sum():+.2f}")
        print(f"  숏: {len(short_trades)}개, PnL: {short_trades['pnl'].sum():+.2f}")

    # ===== 추세추종 전략 =====
    print(f"\n{'='*80}")
    print("2. 추세추종 전략 (Trend Following)")
    print(f"{'='*80}")
    print("전략:")
    print("  - EMA12 > EMA26 + 강한 ADX → LONG")
    print("  - EMA12 < EMA26 + 강한 ADX → SHORT")
    print("  - TP: ATR의 3배, SL: ATR의 1.5배")
    print("")

    trend_strategy = TrendFollowingStrategy(
        fast_period=12,
        slow_period=26,
        adx_period=14,
        adx_threshold=25
    )

    engine2 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    result2 = engine2.run(df, trend_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

    print(f"\n[결과]")
    print(f"  수익률: {result2['total_return']:.2f}%")
    print(f"  거래수: {result2['total_trades']}")
    if result2['total_trades'] > 0:
        print(f"  승률: {result2['win_rate']:.1f}%")
        print(f"  MDD: {result2.get('max_drawdown', 0):.2f}%")

        trades_df = result2['trades']
        tp_trades = trades_df[trades_df['reason'] == 'take_profit']
        sl_trades = trades_df[trades_df['reason'] == 'stop_loss']

        print(f"\n  TP: {len(tp_trades)}개 ({len(tp_trades)/len(trades_df)*100:.1f}%)")
        print(f"  SL: {len(sl_trades)}개 ({len(sl_trades)/len(trades_df)*100:.1f}%)")

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
    print(f"{'항목':<20} {'RSI':>15} {'추세추종':>15} {'차이':>15}")
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
    print(f"\n시장 상황: {market_change:+.2f}% 변동")

    if result2['total_return'] > result1['total_return']:
        improvement = result2['total_return'] - result1['total_return']
        print(f"\n[OK] 추세추종 전략 승리!")
        print(f"  수익률 개선: {improvement:+.2f}%p")
        if result2['total_trades'] > 0:
            print(f"  승률: {result2['win_rate']:.1f}%")

        # 하락장에서 수익냈는지 체크
        if market_change < 0 and result2['total_return'] > 0:
            print(f"\n  [대박] 하락장({market_change:+.2f}%)에서도 플러스 수익!")
        elif market_change < 0:
            print(f"\n  하락장({market_change:+.2f}%)에서 손실 최소화")
    else:
        loss = result1['total_return'] - result2['total_return']
        print(f"\n[X] RSI 전략이 더 나음")
        print(f"  수익률 차이: {loss:+.2f}%p")

    # 전략 특징 요약
    print(f"\n{'='*80}")
    print("전략 특징 비교")
    print(f"{'='*80}")
    print("RSI 전략 (평균회귀):")
    print("  - 적합: 횡보장, 약한 추세")
    print("  - 부적합: 강한 추세장 (상승/하락)")
    print("  - 로직: 과매수/과매도에서 반대 베팅")

    print("\n추세추종 전략:")
    print("  - 적합: 강한 추세장 (상승/하락)")
    print("  - 부적합: 횡보장")
    print("  - 로직: 추세 방향으로 베팅")
    print("  - 장점: 하락장에서도 숏으로 수익 가능")


if __name__ == "__main__":
    run_trend_test()
