"""
기본 전략 vs 하락장 대응 전략 비교
"""
from backtest.data_loader import DataLoader
from backtest.backtest import BacktestEngine
from scalping_strategy import ScalpingRSIStrategy
from bear_market_strategy import (
    BearMarketRSIStrategy,
    BearMarketMomentumStrategy,
    AdaptiveBearMarketStrategy
)
import config


def run_backtest(strategy_name, strategy, df, leverage=5, stop_loss=1.5, take_profit=5.0):
    """백테스트 실행"""
    print(f"\n{'='*80}")
    print(f"백테스트: {strategy_name}")
    print(f"{'='*80}")

    engine = BacktestEngine(
        initial_capital=10000,
        leverage=leverage,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    # 손절/익절 설정
    original_check = engine._check_stop_loss_take_profit
    def wrapped_check(price, time):
        return original_check(price, time, stop_loss_pct=stop_loss, take_profit_pct=take_profit)
    engine._check_stop_loss_take_profit = wrapped_check

    result = engine.run(df, strategy, capital_pct=1.0)

    print(f"\n[결과]")
    print(f"  초기 자본: {result['initial_capital']:.2f} USDT")
    print(f"  최종 자본: {result['final_capital']:.2f} USDT")
    print(f"  총 수익률: {result['total_return']:.2f}%")
    print(f"  총 거래수: {result['total_trades']}")

    if result['total_trades'] > 0:
        print(f"  승률: {result['win_rate']:.1f}%")
        print(f"  평균 수익: {result['avg_win']:.2f} USDT")
        print(f"  평균 손실: {result['avg_loss']:.2f} USDT")
        print(f"  최대 낙폭: {result['max_drawdown']:.2f}%")
        print(f"  총 수수료: {result['total_fees']:.2f} USDT")

        # 롱/숏 거래 분석
        trades_df = result['trades']
        long_trades = trades_df[trades_df['side'] == 'long']
        short_trades = trades_df[trades_df['side'] == 'short']

        print(f"\n[거래 분석]")
        print(f"  롱 거래: {len(long_trades)}개")
        if len(long_trades) > 0:
            long_win = len(long_trades[long_trades['pnl'] > 0])
            long_pnl = long_trades['pnl'].sum()
            print(f"    승리: {long_win}개 ({long_win/len(long_trades)*100:.1f}%)")
            print(f"    총 PnL: {long_pnl:.2f} USDT")

        print(f"  숏 거래: {len(short_trades)}개")
        if len(short_trades) > 0:
            short_win = len(short_trades[short_trades['pnl'] > 0])
            short_pnl = short_trades['pnl'].sum()
            print(f"    승리: {short_win}개 ({short_win/len(short_trades)*100:.1f}%)")
            print(f"    총 PnL: {short_pnl:.2f} USDT")

    return result


def main():
    """메인 비교"""
    print("=" * 80)
    print("기본 전략 vs 하락장 대응 전략 비교")
    print("=" * 80)

    # 데이터 로드
    print("\n데이터 로딩...")
    loader = DataLoader(config.SYMBOL, testnet=config.TESTNET)
    df = loader.fetch_historical_data(interval='5m', days=30)

    if df is None or len(df) == 0:
        print("데이터 로드 실패!")
        return

    print(f"데이터 로드 완료: {len(df)} 캔들")
    print(f"기간: {df['datetime'].min()} ~ {df['datetime'].max()}")
    print(f"시작가: {df.iloc[0]['close']:.2f}, 종가: {df.iloc[-1]['close']:.2f}")
    market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
    print(f"시장 변동: {market_change:+.2f}%")

    # 최적 파라미터 (7일 최적화 결과)
    LEVERAGE = 5
    STOP_LOSS = 1.5
    TAKE_PROFIT = 5.0

    print(f"\n[파라미터]")
    print(f"  레버리지: {LEVERAGE}배")
    print(f"  손절: {STOP_LOSS}%")
    print(f"  익절: {TAKE_PROFIT}%")

    # 전략 목록
    strategies = {
        '1. 기본 RSI (9, 25/65)': ScalpingRSIStrategy(period=9, oversold=25, overbought=65),
        '2. 하락장 RSI': BearMarketRSIStrategy(period=9, oversold=20, overbought=70),
        '3. 하락장 모멘텀': BearMarketMomentumStrategy(momentum_period=5, threshold=0.005),
        '4. 적응형 하락장': AdaptiveBearMarketStrategy(),
    }

    # 각 전략 테스트
    results = {}
    for name, strategy in strategies.items():
        result = run_backtest(name, strategy, df, LEVERAGE, STOP_LOSS, TAKE_PROFIT)
        results[name] = result

    # 비교 테이블
    print("\n\n" + "=" * 80)
    print("전략 비교 요약")
    print("=" * 80)
    print(f"{'전략':<25} {'수익률%':>10} {'거래수':>8} {'승률%':>8} {'MDD%':>10} {'수수료':>10}")
    print("-" * 80)

    for name, result in results.items():
        if result['total_trades'] > 0:
            print(f"{name:<25} {result['total_return']:>9.2f}% {result['total_trades']:>8} "
                  f"{result.get('win_rate', 0):>7.1f}% {result.get('max_drawdown', 0):>9.2f}% "
                  f"{result.get('total_fees', 0):>9.2f}")
        else:
            print(f"{name:<25} {'거래없음':>10} {0:>8} {0:>8.1f}% {0:>10.2f}% {0:>10.2f}")

    print("=" * 80)

    # 최고 성능
    best_strategy = max(results.items(), key=lambda x: x[1]['total_return'])
    print(f"\n✅ 최고 성능: {best_strategy[0]}")
    print(f"   수익률: {best_strategy[1]['total_return']:.2f}%")
    print(f"   시장 대비 초과수익: {best_strategy[1]['total_return'] - market_change:+.2f}%")


if __name__ == "__main__":
    main()
