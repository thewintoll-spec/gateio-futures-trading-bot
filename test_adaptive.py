# -*- coding: utf-8 -*-
"""
Adaptive Multi-Regime Strategy Backtest

Compare 3 strategies:
1. Grid Trading only
2. Trend Following only
3. Adaptive (auto-switch based on market regime)
"""
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from grid_strategy import GridTradingStrategy
from trend_following_strategy import TrendFollowingStrategy
from adaptive_strategy import AdaptiveStrategy


def test_adaptive_strategy():
    """Test adaptive strategy vs single strategies"""

    print("=" * 80)
    print("Adaptive Multi-Regime Strategy Backtest")
    print("=" * 80)
    print("\nGoal: Compare Grid vs Trend vs Adaptive strategies")

    loader = BinanceDataLoader(symbol='ETHUSDT')

    LEVERAGE = 2
    CAPITAL_PCT = 0.90

    # Test cases
    test_cases = [
        {
            'name': 'Grid Only',
            'strategy': GridTradingStrategy(
                num_grids=30,
                range_pct=10.0,
                profit_per_grid=0.3,
                max_positions=10,
                rebalance_threshold=7.0,
                tight_sl=True,
                use_trend_filter=True,
                dynamic_sl=True,
                use_regime_filter=False
            )
        },
        {
            'name': 'Trend Only',
            'strategy': TrendFollowingStrategy(
                fast_ema=12,
                slow_ema=26,
                adx_threshold=25,
                trailing_stop_atr=2.0,
                min_profit_before_trail=1.0
            )
        },
        {
            'name': 'Adaptive (ADX=25)',
            'strategy': AdaptiveStrategy(
                adx_threshold=25,
                allow_short_in_downtrend=True
            )
        },
        {
            'name': 'Adaptive (ADX=20)',
            'strategy': AdaptiveStrategy(
                adx_threshold=20,
                allow_short_in_downtrend=True
            )
        },
        {
            'name': 'Adaptive (ADX=30)',
            'strategy': AdaptiveStrategy(
                adx_threshold=30,
                allow_short_in_downtrend=True
            )
        }
    ]

    # Test periods
    periods = [30, 60, 90]

    all_results = {}

    for days in periods:
        print(f"\n{'='*80}")
        print(f"[{days}-Day Backtest]")
        print(f"{'='*80}")

        df = loader.fetch_historical_data(interval='5m', days=days)

        if df is None or len(df) == 0:
            print(f"Data load failed! ({days} days)")
            continue

        print(f"\nData: {len(df)} candles")
        print(f"Period: {df['datetime'].min()} ~ {df['datetime'].max()}")
        market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
        print(f"Market Change: {market_change:+.2f}%")

        all_results[days] = {}

        for test_case in test_cases:
            name = test_case['name']
            strategy = test_case['strategy']

            print(f"\n[{name}]")

            engine = BacktestEngine(
                initial_capital=10000,
                leverage=LEVERAGE,
                maker_fee=0.0002,
                taker_fee=0.0005
            )

            # Run quietly
            import sys
            from io import StringIO
            old_stdout = sys.stdout
            sys.stdout = StringIO()

            try:
                result = engine.run(df, strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)
            finally:
                sys.stdout = old_stdout

            # Save results
            all_results[days][name] = {
                'return': result['total_return'],
                'trades': result['total_trades'],
                'win_rate': result['win_rate'] if result['total_trades'] > 0 else 0,
                'mdd': result.get('max_drawdown', 0),
                'final_capital': result['final_capital']
            }

            print(f"  Return: {result['total_return']:+.2f}%")
            print(f"  Trades: {result['total_trades']}")
            if result['total_trades'] > 0:
                print(f"  Win Rate: {result['win_rate']:.1f}%")
                print(f"  MDD: {result.get('max_drawdown', 0):.2f}%")

    # Summary comparison
    print("\n" + "=" * 80)
    print("Summary Results")
    print("=" * 80)

    for name in [tc['name'] for tc in test_cases]:
        print(f"\n[{name}]")
        print(f"{'Period':<10} {'Return':>10} {'Trades':>8} {'WinRate':>8} {'MDD':>8}")
        print("-" * 60)

        for days in periods:
            if days in all_results and name in all_results[days]:
                r = all_results[days][name]
                win_rate_str = f"{r['win_rate']:.1f}%" if r['trades'] > 0 else "N/A"

                status = "[+]" if r['return'] > 0 else "[-]"
                print(f"{days}d{'':<6} {status} {r['return']:>7.2f}% {r['trades']:>8} "
                      f"{win_rate_str:>8} {r['mdd']:>7.2f}%")

    # Comparison: Adaptive vs others
    print("\n" + "=" * 80)
    print("Adaptive Strategy Effectiveness")
    print("=" * 80)

    adaptive_name = 'Adaptive (ADX=25)'

    for days in periods:
        if days not in all_results:
            continue

        print(f"\n[{days} days]")

        baseline_names = ['Grid Only', 'Trend Only']
        adaptive = all_results[days].get(adaptive_name)

        if not adaptive:
            continue

        print(f"  {adaptive_name}: {adaptive['return']:+.2f}% ({adaptive['trades']} trades)")

        for baseline_name in baseline_names:
            baseline = all_results[days].get(baseline_name)
            if not baseline:
                continue

            improvement = adaptive['return'] - baseline['return']
            print(f"  vs {baseline_name}: {baseline['return']:+.2f}% ({baseline['trades']} trades)")
            print(f"    Improvement: {improvement:+.2f}%p")

            if improvement > 1.0:
                print(f"    Result: [MUCH BETTER] Adaptive wins!")
            elif improvement > 0:
                print(f"    Result: [BETTER] Adaptive slightly better")
            elif improvement > -1.0:
                print(f"    Result: [SIMILAR] No major difference")
            else:
                print(f"    Result: [WORSE] {baseline_name} is better")

    # Final recommendation
    print("\n" + "=" * 80)
    print("Final Analysis & Recommendation")
    print("=" * 80)

    # 90-day comparison
    if 90 in all_results:
        results_90 = all_results[90]
        best = max(results_90.items(), key=lambda x: x[1]['return'])
        best_name = best[0]
        best_result = best[1]

        print(f"\n[Best Performance (90-day)]: {best_name}")
        print(f"  Return: {best_result['return']:+.2f}%")
        print(f"  Trades: {best_result['trades']}")
        print(f"  Win Rate: {best_result['win_rate']:.1f}%")
        print(f"  MDD: {best_result['mdd']:.2f}%")

        # Check consistency across all periods
        all_positive = all(
            all_results[days][best_name]['return'] > 0
            for days in periods
            if days in all_results and best_name in all_results[days]
        )

        if all_positive:
            print(f"\n[EXCELLENT] Positive returns in all periods!")
            print(f"Recommendation: Deploy '{best_name}' to testnet")
        else:
            print(f"\n[CAUTION] Negative returns in some periods")
            print(f"Recommendation: Further testing needed")

    # ADX threshold comparison
    adaptive_variants = ['Adaptive (ADX=20)', 'Adaptive (ADX=25)', 'Adaptive (ADX=30)']
    if 90 in all_results:
        print(f"\n[ADX Threshold Comparison (90-day)]")
        for name in adaptive_variants:
            if name in all_results[90]:
                r = all_results[90][name]
                print(f"  {name}: {r['return']:+.2f}% ({r['trades']} trades)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_adaptive_strategy()
