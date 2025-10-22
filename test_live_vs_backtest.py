# -*- coding: utf-8 -*-
"""
Live Trading vs Backtest Comparison

Compare actual live trading results with backtest on same period
Period: 2025-10-20 23:30 ~ 2025-10-22 20:00 (약 44시간)
"""
from datetime import datetime, timedelta
import pandas as pd
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from grid_strategy import GridTradingStrategy


def test_live_vs_backtest():
    """Test if backtest matches live trading results"""

    print("=" * 80)
    print("Live Trading vs Backtest Comparison")
    print("=" * 80)

    # Live trading period
    start_time = datetime(2025, 10, 20, 23, 30)
    end_time = datetime(2025, 10, 22, 20, 0)
    duration = end_time - start_time
    hours = duration.total_seconds() / 3600

    print(f"\n[Period]")
    print(f"Start: {start_time}")
    print(f"End: {end_time}")
    print(f"Duration: {hours:.1f} hours (~{hours/24:.1f} days)")

    # Live trading results
    print(f"\n[Live Trading Results]")
    print(f"Strategy: Grid Trading")
    print(f"Symbols: ETH_USDT, BTC_USDT")
    print(f"Leverage: 2x")
    print(f"Check Interval: 60 seconds (original)")
    print(f"\nResults:")
    print(f"  Total Trades: 5")
    print(f"  Wins: 3 | Losses: 2")
    print(f"  Win Rate: 60%")
    print(f"  Total PnL: +25.52 USDT")
    print(f"  ETH: 4 trades (+40.59 USDT)")
    print(f"  BTC: 1 trade (-11.55 USDT)")

    # Load data for backtest
    print(f"\n{'='*80}")
    print("[Backtest]")
    print(f"{'='*80}")

    loader = BinanceDataLoader(symbol='ETHUSDT')

    # Calculate days needed (44 hours = ~2 days)
    days_needed = 3  # Get a bit more to ensure coverage

    print(f"\nLoading {days_needed} days of ETHUSDT data...")
    df = loader.fetch_historical_data(interval='5m', days=days_needed)

    if df is None or len(df) == 0:
        print("Failed to load data!")
        return

    print(f"Total candles: {len(df)}")
    print(f"Data period: {df['datetime'].min()} ~ {df['datetime'].max()}")

    # Filter to exact period (if possible)
    # Note: We can't get exact minute-by-minute match, but close enough
    total_candles = len(df)

    # Filter to match live trading start time: 2025-10-20 23:30
    # Find the closest candle to that time
    target_start = datetime(2025, 10, 20, 23, 30)

    # Filter dataframe to start from target time
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df[df['datetime'] >= target_start].copy()

    if len(df) == 0:
        print(f"No data available after {target_start}")
        return

    print(f"\nFiltered to match live trading start time")
    print(f"Backtest period: {df['datetime'].min()} ~ {df['datetime'].max()}")
    market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
    print(f"ETH Price Change: {market_change:+.2f}%")

    # Same strategy as live trading
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

    # Backtest engine
    engine = BacktestEngine(
        initial_capital=1000,  # Approximate starting capital
        leverage=2,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    print(f"\n[Running Backtest...]")
    print(f"Strategy: Grid Trading (same as live)")
    print(f"Leverage: 2x")
    print(f"Capital: Similar to live")

    result = engine.run(
        df,
        strategy,
        capital_pct=0.50,  # First position 50%
        allow_reversal=False
    )

    # Display results
    print(f"\n{'='*80}")
    print("[Backtest Results]")
    print(f"{'='*80}")

    print(f"\nETH Only:")
    print(f"  Total Trades: {result['total_trades']}")
    print(f"  Wins: {result['winning_trades']} | Losses: {result['losing_trades']}")
    print(f"  Win Rate: {result['win_rate']:.1f}%")
    print(f"  Total Return: {result['total_return']:+.2f}%")
    print(f"  Final Capital: {result['final_capital']:.2f}")
    print(f"  PnL: {result['final_capital'] - 1000:+.2f} USDT")

    if result['total_trades'] > 0:
        print(f"  Avg Win: {result.get('avg_win', 0):.2f}%")
        print(f"  Avg Loss: {result.get('avg_loss', 0):.2f}%")
        print(f"  Max Drawdown: {result.get('max_drawdown', 0):.2f}%")

    # Comparison
    print(f"\n{'='*80}")
    print("[Comparison: Live vs Backtest]")
    print(f"{'='*80}")

    backtest_pnl = result['final_capital'] - 1000
    live_eth_pnl = 40.59  # ETH only from live

    print(f"\nETH Trading (Live had 4 trades, Backtest had {result['total_trades']} trades):")
    print(f"  Live PnL (ETH):      +{live_eth_pnl:.2f} USDT (4 trades)")
    print(f"  Backtest PnL (ETH):  {backtest_pnl:+.2f} USDT ({result['total_trades']} trades)")
    print(f"  Difference:          {backtest_pnl - live_eth_pnl:+.2f} USDT")

    diff_pct = abs(backtest_pnl - live_eth_pnl) / live_eth_pnl * 100 if live_eth_pnl != 0 else 0

    print(f"\n[Analysis]")
    if result['total_trades'] != 4:
        print(f"  Trade Count Mismatch: Backtest found {result['total_trades']} trades vs Live 4 trades")
        print(f"  Reason: Different data source (Binance vs Gate.io) or timing differences")

    if diff_pct < 10:
        print(f"  Result: [SIMILAR] PnL difference is {diff_pct:.1f}% - Reasonably close!")
    elif diff_pct < 30:
        print(f"  Result: [MODERATE] PnL difference is {diff_pct:.1f}% - Some deviation")
    else:
        print(f"  Result: [DIFFERENT] PnL difference is {diff_pct:.1f}% - Significant deviation")

    print(f"\n[Possible Reasons for Differences]")
    print(f"  1. Data Source: Binance (backtest) vs Gate.io (live)")
    print(f"  2. Price Differences: Different exchange prices")
    print(f"  3. Slippage: Live trading has slippage, backtest doesn't")
    print(f"  4. Fees: Actual fees vs simulated fees")
    print(f"  5. Execution Timing: 60-second intervals may catch different signals")
    print(f"  6. BTC: Live also traded BTC (1 trade, -11.55 USDT)")

    print(f"\n{'='*80}")
    print("[Note]")
    print(f"{'='*80}")
    print(f"This backtest only simulates ETH trading on Binance data.")
    print(f"Live trading used Gate.io data for both ETH and BTC.")
    print(f"Perfect match is not expected due to:")
    print(f"  - Different exchanges (Binance vs Gate.io)")
    print(f"  - Different symbols traded (ETH only vs ETH+BTC)")
    print(f"  - Real slippage and execution delays")
    print(f"  - Multi-symbol capital allocation in live trading")

    print(f"\n{'='*80}")


if __name__ == "__main__":
    test_live_vs_backtest()
