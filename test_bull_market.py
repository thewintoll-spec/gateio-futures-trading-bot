"""
상승장에서 기본 RSI 전략 성과 테스트
"""
from backtest.data_loader import DataLoader
from backtest.backtest import BacktestEngine
from scalping_strategy import ScalpingRSIStrategy
import config


def test_different_periods(days_list=[7, 14, 30, 60]):
    """여러 기간 테스트하여 상승장/하락장 구간 찾기"""

    print("=" * 80)
    print("다양한 기간별 시장 변동 분석")
    print("=" * 80)

    loader = DataLoader(config.SYMBOL, testnet=config.TESTNET)

    for days in days_list:
        print(f"\n[{days}일 데이터]")
        df = loader.fetch_historical_data(interval='5m', days=days)

        if df is None or len(df) == 0:
            print(f"  데이터 로드 실패!")
            continue

        start_price = df.iloc[0]['close']
        end_price = df.iloc[-1]['close']
        market_change = (end_price - start_price) / start_price * 100

        print(f"  기간: {df['datetime'].min()} ~ {df['datetime'].max()}")
        print(f"  시작가: {start_price:.2f}, 종가: {end_price:.2f}")
        print(f"  시장 변동: {market_change:+.2f}%")

        # 상승장/하락장 판단
        if market_change > 5:
            print(f"  >>> 강한 상승장!")
        elif market_change > 0:
            print(f"  >>> 약한 상승장")
        elif market_change > -5:
            print(f"  >>> 약한 하락장")
        else:
            print(f"  >>> 강한 하락장!")


def run_bull_test(df, market_change):
    """상승장 백테스트"""

    print(f"\n{'='*80}")
    print(f"상승장 백테스트 (시장 변동: {market_change:+.2f}%)")
    print(f"{'='*80}")

    # 최적 파라미터로 테스트
    strategy = ScalpingRSIStrategy(period=9, oversold=25, overbought=65)

    engine = BacktestEngine(
        initial_capital=10000,
        leverage=5,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    original_check = engine._check_stop_loss_take_profit
    def wrapped_check(price, time):
        return original_check(price, time, stop_loss_pct=1.5, take_profit_pct=5.0)
    engine._check_stop_loss_take_profit = wrapped_check

    result = engine.run(df, strategy, capital_pct=0.95)

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

        # 롱/숏 분석
        trades_df = result['trades']
        long_trades = trades_df[trades_df['side'] == 'long']
        short_trades = trades_df[trades_df['side'] == 'short']

        print(f"\n[거래 분석]")
        print(f"  롱 거래: {len(long_trades)}개")
        if len(long_trades) > 0:
            long_win = len(long_trades[long_trades['pnl'] > 0])
            long_pnl = long_trades['pnl'].sum()
            print(f"    승리: {long_win}개 ({long_win/len(long_trades)*100:.1f}%)")
            print(f"    총 PnL: {long_pnl:+.2f} USDT")

        print(f"  숏 거래: {len(short_trades)}개")
        if len(short_trades) > 0:
            short_win = len(short_trades[short_trades['pnl'] > 0])
            short_pnl = short_trades['pnl'].sum()
            print(f"    승리: {short_win}개 ({short_win/len(short_trades)*100:.1f}%)")
            print(f"    총 PnL: {short_pnl:+.2f} USDT")

    print(f"\n[시장 대비 성과]")
    alpha = result['total_return'] - market_change
    print(f"  시장 수익률: {market_change:+.2f}%")
    print(f"  전략 수익률: {result['total_return']:+.2f}%")
    print(f"  알파(초과수익): {alpha:+.2f}%")

    return result


def main():
    """메인 실행"""

    # 1단계: 여러 기간 분석하여 상승장 찾기
    print("\n" + "=" * 80)
    print("STEP 1: 상승장 기간 찾기")
    print("=" * 80)
    test_different_periods([7, 14, 30, 60, 90])

    # 2단계: 사용자가 선택한 상승장 기간으로 테스트
    print("\n\n" + "=" * 80)
    print("STEP 2: 상승장 백테스트")
    print("=" * 80)

    days = int(input("\n테스트할 기간(일) 입력: "))

    loader = DataLoader(config.SYMBOL, testnet=config.TESTNET)
    df = loader.fetch_historical_data(interval='5m', days=days)

    if df is None or len(df) == 0:
        print("데이터 로드 실패!")
        return

    market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100

    run_bull_test(df, market_change)


if __name__ == "__main__":
    main()
