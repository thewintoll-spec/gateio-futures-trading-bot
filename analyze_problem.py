"""
백테스트 결과 상세 분석
"""
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from inverse_strategy import InverseRSIStrategy
from improved_strategy_v2 import ImprovedRSIStrategyV2
import pandas as pd


def analyze_trades(result, strategy_name):
    """거래 상세 분석"""
    print(f"\n{'='*80}")
    print(f"{strategy_name} 상세 분석")
    print(f"{'='*80}")

    if result['total_trades'] == 0:
        print("거래 없음!")
        return

    trades_df = result['trades']

    # 기본 통계
    print(f"\n[기본 통계]")
    print(f"  총 거래수: {len(trades_df)}개")
    print(f"  수익률: {result['total_return']:.2f}%")
    print(f"  승률: {result['win_rate']:.1f}%")
    print(f"  MDD: {result.get('max_drawdown', 0):.2f}%")

    # 롱/숏 분석
    long_trades = trades_df[trades_df['side'] == 'long']
    short_trades = trades_df[trades_df['side'] == 'short']

    print(f"\n[롱/숏 분석]")
    print(f"  롱 거래: {len(long_trades)}개")
    if len(long_trades) > 0:
        long_wins = len(long_trades[long_trades['pnl'] > 0])
        print(f"    승: {long_wins}개 ({long_wins/len(long_trades)*100:.1f}%)")
        print(f"    총 PnL: {long_trades['pnl'].sum():+.2f} USDT")
        print(f"    평균 PnL: {long_trades['pnl'].mean():+.2f} USDT")

    print(f"  숏 거래: {len(short_trades)}개")
    if len(short_trades) > 0:
        short_wins = len(short_trades[short_trades['pnl'] > 0])
        print(f"    승: {short_wins}개 ({short_wins/len(short_trades)*100:.1f}%)")
        print(f"    총 PnL: {short_trades['pnl'].sum():+.2f} USDT")
        print(f"    평균 PnL: {short_trades['pnl'].mean():+.2f} USDT")

    # TP/SL 분석
    tp_trades = trades_df[trades_df['reason'] == 'take_profit']
    sl_trades = trades_df[trades_df['reason'] == 'stop_loss']
    reverse_trades = trades_df[trades_df['reason'] == 'reverse']

    print(f"\n[청산 사유 분석]")
    print(f"  TP 도달: {len(tp_trades)}개 ({len(tp_trades)/len(trades_df)*100:.1f}%)")
    if len(tp_trades) > 0:
        print(f"    평균 PnL: {tp_trades['pnl'].mean():+.2f} USDT")

    print(f"  SL 손절: {len(sl_trades)}개 ({len(sl_trades)/len(trades_df)*100:.1f}%)")
    if len(sl_trades) > 0:
        print(f"    평균 PnL: {sl_trades['pnl'].mean():+.2f} USDT")

    print(f"  반전: {len(reverse_trades)}개 ({len(reverse_trades)/len(trades_df)*100:.1f}%)")
    if len(reverse_trades) > 0:
        print(f"    평균 PnL: {reverse_trades['pnl'].mean():+.2f} USDT")

    # 수익/손실 거래 분석
    winning_trades = trades_df[trades_df['pnl'] > 0]
    losing_trades = trades_df[trades_df['pnl'] <= 0]

    print(f"\n[수익/손실 거래]")
    print(f"  수익 거래: {len(winning_trades)}개")
    if len(winning_trades) > 0:
        print(f"    평균 수익: {winning_trades['pnl'].mean():+.2f} USDT")
        print(f"    최대 수익: {winning_trades['pnl'].max():+.2f} USDT")

    print(f"  손실 거래: {len(losing_trades)}개")
    if len(losing_trades) > 0:
        print(f"    평균 손실: {losing_trades['pnl'].mean():+.2f} USDT")
        print(f"    최대 손실: {losing_trades['pnl'].min():+.2f} USDT")

    # Profit Factor
    if len(winning_trades) > 0 and len(losing_trades) > 0:
        total_profit = winning_trades['pnl'].sum()
        total_loss = abs(losing_trades['pnl'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        print(f"\n[Profit Factor]")
        print(f"  총 수익: {total_profit:+.2f} USDT")
        print(f"  총 손실: {-total_loss:+.2f} USDT")
        print(f"  Profit Factor: {profit_factor:.2f}")

    # 최악의 거래 5개
    print(f"\n[최악의 거래 Top 5]")
    worst_trades = trades_df.nsmallest(5, 'pnl')
    for idx, trade in worst_trades.iterrows():
        print(f"  {trade['side'].upper():5s} | PnL: {trade['pnl']:+8.2f} | "
              f"사유: {trade['reason']:12s} | "
              f"진입: {trade['entry_price']:.2f} → 청산: {trade['exit_price']:.2f}")


def main():
    print("="*80)
    print("백테스트 결과 상세 분석")
    print("="*80)

    # 데이터 로드
    loader = BinanceDataLoader(symbol='ETHUSDT')
    df = loader.fetch_historical_data(interval='5m', days=30)

    if df is None or len(df) == 0:
        print("데이터 로드 실패!")
        return

    print(f"\n[시장 환경]")
    print(f"  데이터: {len(df)} 캔들")
    print(f"  기간: {df['datetime'].min()} ~ {df['datetime'].max()}")
    market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
    print(f"  시장 변동: {market_change:+.2f}%")

    # 변동성 분석
    df['return'] = df['close'].pct_change()
    volatility = df['return'].std() * 100
    print(f"  변동성 (std): {volatility:.4f}%")

    # 추세 분석
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma50'] = df['close'].rolling(50).mean()

    uptrend_candles = len(df[df['close'] > df['ma20']])
    print(f"  20MA 위: {uptrend_candles}개 ({uptrend_candles/len(df)*100:.1f}%)")

    LEVERAGE = 5
    CAPITAL_PCT = 0.95

    # 정방향 전략
    normal_strategy = ImprovedRSIStrategyV2(period=9, oversold=25, overbought=65)
    engine1 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )
    result1 = engine1.run(df, normal_strategy, capital_pct=CAPITAL_PCT)
    analyze_trades(result1, "정방향 전략 (개선 v2)")

    # 역발상 전략
    inverse_strategy = InverseRSIStrategy(period=9, oversold=25, overbought=65)
    engine2 = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )
    result2 = engine2.run(df, inverse_strategy, capital_pct=CAPITAL_PCT)
    analyze_trades(result2, "역발상 전략")

    # 결론
    print(f"\n{'='*80}")
    print("문제점 진단")
    print(f"{'='*80}")

    print(f"\n1. 시장 환경 문제:")
    if market_change < -10:
        print(f"   - 강한 하락장 ({market_change:+.2f}%)")
        print(f"   - RSI 전략은 횡보장/약한 추세에서 유리")
        print(f"   - 강한 추세장에서는 역추세 포지션이 계속 손실")

    print(f"\n2. 레버리지 문제:")
    print(f"   - 현재 5배 레버리지")
    print(f"   - 손실이 5배로 증폭됨")
    print(f"   - 강한 추세장에서는 레버리지 낮춰야 함")

    print(f"\n3. 전략 근본 문제:")
    if result1['total_return'] < -50 and result2['total_return'] < -50:
        print(f"   - 두 전략 모두 -50% 이상 손실")
        print(f"   - RSI 평균회귀 전략이 이 시장에 안 맞음")
        print(f"   - 추세추종 전략이 필요할 수도")


if __name__ == "__main__":
    main()
