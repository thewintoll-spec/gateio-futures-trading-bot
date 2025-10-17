"""
스캘핑 전략 백테스트 실행
"""
from backtest.data_loader import DataLoader
from backtest.backtest import BacktestEngine
from scalping_strategy import (
    MomentumScalpingStrategy,
    EMAScalpingStrategy,
    VolumeBreakoutStrategy,
    ScalpingRSIStrategy,
    MACDScalpingStrategy,
    SupertrendStrategy,
    StochasticScalpingStrategy,
    PriceActionStrategy,
    VWAPStrategy
)
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
        print(f"  손익비: {abs(results['avg_win'] / results['avg_loss']):.2f}" if results['avg_loss'] != 0 else "  손익비: N/A")

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


def run_scalping_backtest(strategy_name, strategy, data, initial_capital=10000,
                          stop_loss=1.5, take_profit=2.0):
    """
    스캘핑 백테스트 실행

    Args:
        strategy_name: 전략 이름
        strategy: 전략 인스턴스
        data: 가격 데이터
        initial_capital: 초기 자본
        stop_loss: 손절 % (단타용 - 타이트하게)
        take_profit: 익절 % (단타용 - 빠르게)
    """
    # 백테스트 엔진 - 단타용 설정
    engine = BacktestEngine(
        initial_capital=initial_capital,
        leverage=config.LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    # 손절/익절 파라미터를 전달하도록 수정
    # 임시로 엔진의 메서드를 래핑
    original_check = engine._check_stop_loss_take_profit

    def wrapped_check(price, time):
        return original_check(price, time, stop_loss_pct=stop_loss, take_profit_pct=take_profit)

    engine._check_stop_loss_take_profit = wrapped_check

    results = engine.run(data, strategy, capital_pct=0.8)
    print_results(results, strategy_name)

    return results


def main():
    """메인 함수"""
    print("=" * 70)
    print("Gate.io Futures 스캘핑 백테스트 시스템")
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

    # 스캘핑 전략 목록
    # 단타용 손절/익절: 타이트하게 설정
    strategies = {
        # 기존 전략
        'Momentum (0.3%)': {
            'strategy': MomentumScalpingStrategy(momentum_period=5, strength_threshold=0.003),
            'stop_loss': 1.5,
            'take_profit': 2.5
        },
        'EMA Cross (8/21)': {
            'strategy': EMAScalpingStrategy(fast_period=8, slow_period=21),
            'stop_loss': 2.0,
            'take_profit': 3.0
        },
        'Volume Breakout': {
            'strategy': VolumeBreakoutStrategy(breakout_period=10, volume_multiplier=2.0),
            'stop_loss': 2.0,
            'take_profit': 3.5
        },
        'Scalping RSI (7)': {
            'strategy': ScalpingRSIStrategy(period=7, oversold=35, overbought=65),
            'stop_loss': 2.0,
            'take_profit': 3.0
        },
        # 새 전략들
        'MACD (12/26/9)': {
            'strategy': MACDScalpingStrategy(fast=12, slow=26, signal=9),
            'stop_loss': 2.0,
            'take_profit': 3.0
        },
        'MACD Fast (8/17/9)': {
            'strategy': MACDScalpingStrategy(fast=8, slow=17, signal=9),
            'stop_loss': 1.5,
            'take_profit': 2.5
        },
        'Supertrend (10x3)': {
            'strategy': SupertrendStrategy(period=10, multiplier=3),
            'stop_loss': 2.5,
            'take_profit': 4.0
        },
        'Supertrend (7x2)': {
            'strategy': SupertrendStrategy(period=7, multiplier=2),
            'stop_loss': 1.5,
            'take_profit': 2.5
        },
        'Stochastic (14,3)': {
            'strategy': StochasticScalpingStrategy(k_period=14, d_period=3, oversold=20, overbought=80),
            'stop_loss': 2.0,
            'take_profit': 3.0
        },
        'Stochastic Fast (8,3)': {
            'strategy': StochasticScalpingStrategy(k_period=8, d_period=3, oversold=25, overbought=75),
            'stop_loss': 1.5,
            'take_profit': 2.5
        },
        'Price Action': {
            'strategy': PriceActionStrategy(lookback=20, breakout_threshold=0.002),
            'stop_loss': 2.0,
            'take_profit': 3.5
        },
        'VWAP (20)': {
            'strategy': VWAPStrategy(period=20),
            'stop_loss': 1.5,
            'take_profit': 2.5
        },
        'VWAP (30)': {
            'strategy': VWAPStrategy(period=30),
            'stop_loss': 2.0,
            'take_profit': 3.0
        },
    }

    # 각 전략 백테스트
    all_results = {}
    for name, config_dict in strategies.items():
        print(f"\n{'='*70}")
        print(f"백테스트 실행: {name}")
        print(f"{'='*70}")

        results = run_scalping_backtest(
            name,
            config_dict['strategy'],
            df,
            stop_loss=config_dict['stop_loss'],
            take_profit=config_dict['take_profit']
        )
        all_results[name] = results

    # 전략 비교
    print("\n" + "=" * 70)
    print("전략 비교 (스캘핑)")
    print("=" * 70)
    print(f"{'전략':<25} {'수익률':>10} {'거래수':>8} {'승률':>8} {'손익비':>8} {'MDD':>10}")
    print("-" * 70)

    for name, results in all_results.items():
        mdd = results.get('max_drawdown', 0)
        win_rate = results.get('win_rate', 0)
        avg_win = results.get('avg_win', 0)
        avg_loss = results.get('avg_loss', 0)
        profit_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        print(f"{name:<25} {results['total_return']:>9.2f}% {results['total_trades']:>8} "
              f"{win_rate:>7.1f}% {profit_ratio:>7.2f} {mdd:>9.2f}%")

    print("=" * 70)


if __name__ == "__main__":
    main()
