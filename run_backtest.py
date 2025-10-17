"""
백테스트 실행 스크립트
"""
from backtest.data_loader import DataLoader
from backtest.backtest import BacktestEngine
from strategy import RSIStrategy, MovingAverageCrossStrategy
import config


def print_results(results, strategy_name):
    """백테스트 결과 출력"""
    print("\n" + "=" * 70)
    print(f"백테스트 결과: {strategy_name}")
    print("=" * 70)

    print(f"\n[자본]")
    print(f"  초기 자본: {results['initial_capital']:.2f} USDT")
    print(f"  최종 자본: {results['final_capital']:.2f} USDT")
    print(f"  총 수익률: {results['total_return']:.2f}%")

    if results['total_trades'] > 0:
        print(f"\n[거래 통계]")
        print(f"  총 거래 수: {results['total_trades']}")
        print(f"  승리 거래: {results['winning_trades']} ({results['win_rate']:.1f}%)")
        print(f"  패배 거래: {results['losing_trades']}")
        print(f"  평균 승리: {results['avg_win']:.2f} USDT")
        print(f"  평균 손실: {results['avg_loss']:.2f} USDT")
        print(f"  최대 승리: {results['largest_win']:.2f} USDT")
        print(f"  최대 손실: {results['largest_loss']:.2f} USDT")
        print(f"  총 수수료: {results['total_fees']:.2f} USDT")

        if 'max_drawdown' in results:
            print(f"\n[리스크]")
            print(f"  최대 낙폭 (MDD): {results['max_drawdown']:.2f}%")

        # Show some trades
        print(f"\n[최근 거래 5건]")
        trades_df = results['trades']
        for idx, trade in trades_df.tail(5).iterrows():
            pnl_sign = "+" if trade['pnl'] > 0 else ""
            print(f"  {trade['entry_time']:%Y-%m-%d %H:%M} {trade['side'].upper():5} "
                  f"진입:{trade['entry_price']:8.2f} 청산:{trade['exit_price']:8.2f} "
                  f"PnL: {pnl_sign}{trade['pnl']:7.2f} USDT ({pnl_sign}{trade['pnl_percent']:.1f}%) "
                  f"[{trade['reason']}]")
    else:
        print("\n거래가 발생하지 않았습니다.")

    print("=" * 70)


def run_backtest(strategy_name, strategy, data, initial_capital=10000):
    """백테스트 실행"""
    engine = BacktestEngine(
        initial_capital=initial_capital,
        leverage=config.LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    results = engine.run(data, strategy, capital_pct=0.8)
    print_results(results, strategy_name)

    return results


def main():
    """메인 함수"""
    print("=" * 70)
    print("Gate.io Futures 백테스트 시스템")
    print("=" * 70)

    # 데이터 로드
    print("\n1. 과거 데이터 로딩...")
    loader = DataLoader(config.SYMBOL, testnet=config.TESTNET)

    # 7일치 5분봉 데이터
    df = loader.fetch_historical_data(interval='5m', days=7)

    if df is None or len(df) == 0:
        print("데이터 로드 실패!")
        return

    print(f"데이터 로드 완료: {len(df)} 캔들")

    # 전략 목록
    strategies = {
        'RSI (14, 30/70)': RSIStrategy(period=14, oversold=30, overbought=70),
        'RSI (14, 25/75)': RSIStrategy(period=14, oversold=25, overbought=75),
        'RSI (21, 30/70)': RSIStrategy(period=21, oversold=30, overbought=70),
        'MA Cross (10/30)': MovingAverageCrossStrategy(fast_period=10, slow_period=30),
        'MA Cross (20/50)': MovingAverageCrossStrategy(fast_period=20, slow_period=50),
    }

    # 각 전략 백테스트
    all_results = {}
    for name, strategy in strategies.items():
        print(f"\n{'='*70}")
        print(f"백테스트 실행: {name}")
        print(f"{'='*70}")
        results = run_backtest(name, strategy, df)
        all_results[name] = results

    # 전략 비교
    print("\n" + "=" * 70)
    print("전략 비교")
    print("=" * 70)
    print(f"{'전략':<20} {'수익률':>10} {'거래수':>8} {'승률':>8} {'MDD':>10}")
    print("-" * 70)

    for name, results in all_results.items():
        mdd = results.get('max_drawdown', 0)
        win_rate = results.get('win_rate', 0)
        print(f"{name:<20} {results['total_return']:>9.2f}% {results['total_trades']:>8} "
              f"{win_rate:>7.1f}% {mdd:>9.2f}%")

    print("=" * 70)


if __name__ == "__main__":
    main()
