"""
여러 전략 비교 백테스트
최근 4일간 어떤 전략이 가장 좋았는지 확인
"""
import sys
sys.path.append('backtest')
from datetime import datetime
from binance_data_loader import BinanceDataLoader
from grid_strategy import GridTradingStrategy
from adaptive_strategy import AdaptiveStrategy
from trend_following_strategy import TrendFollowingStrategy


def simple_backtest(candles, strategy, strategy_name):
    """간단한 백테스트 - 신호만 카운트"""
    balance = 1000  # 시작 자본
    positions = []
    trades = []

    in_position = False
    entry_price = 0
    entry_time = None
    position_side = None

    # 디버그 출력 억제를 위해 sys.stdout을 일시적으로 변경
    import io
    import sys
    old_stdout = sys.stdout

    for i in range(100, len(candles)):
        window = candles[i-100:i+1]
        current_candle = window[-1]
        current_price = current_candle['close']

        # 신호 체크 (출력 억제)
        sys.stdout = io.StringIO()
        signal = strategy.analyze(window)
        sys.stdout = old_stdout

        if signal and not in_position:
            # 진입
            side = signal['signal'] if isinstance(signal, dict) else signal
            entry_price = current_price
            entry_time = current_candle.get('datetime', current_candle.get('timestamp'))
            position_side = side
            in_position = True

        elif in_position:
            # 청산 조건 체크
            if isinstance(signal, dict):
                tp = signal.get('take_profit', 3.0)
                sl = signal.get('stop_loss', 2.0)
            else:
                tp = 3.0
                sl = 2.0

            # PnL 계산
            if position_side == 'long':
                pnl_pct = (current_price - entry_price) / entry_price * 100
            else:  # short
                pnl_pct = (entry_price - current_price) / entry_price * 100

            # TP/SL 체크
            should_close = False
            exit_reason = None

            if pnl_pct >= tp:
                should_close = True
                exit_reason = 'TP'
            elif pnl_pct <= -sl:
                should_close = True
                exit_reason = 'SL'

            if should_close:
                # 거래 기록
                pnl_usdt = balance * 0.5 * (pnl_pct / 100) * 7  # 50% 자본, 7배 레버리지
                balance += pnl_usdt

                trades.append({
                    'entry_time': entry_time,
                    'exit_time': current_candle.get('datetime', current_candle.get('timestamp')),
                    'side': position_side,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl_pct': pnl_pct,
                    'pnl_usdt': pnl_usdt,
                    'reason': exit_reason
                })

                in_position = False

    # 결과 계산
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t['pnl_usdt'] > 0])
    losing_trades = len([t for t in trades if t['pnl_usdt'] < 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    total_profit = sum([t['pnl_usdt'] for t in trades])
    roi = (balance - 1000) / 1000 * 100

    return {
        'strategy': strategy_name,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'total_profit': total_profit,
        'final_balance': balance,
        'roi': roi,
        'trades': trades
    }


def main():
    # 백테스트 기간
    start_date = datetime(2025, 10, 23, 2, 42, 25)
    end_date = datetime.now()
    days = (end_date - start_date).days + 1

    print("=" * 80)
    print("전략 비교 백테스트")
    print("=" * 80)
    print(f"기간: {start_date} ~ {end_date}")
    print(f"총 기간: {(end_date - start_date).total_seconds() / 3600:.1f}시간")
    print(f"시작 자본: 1,000 USDT")
    print(f"레버리지: 7x")
    print(f"자본 배분: 50% per trade")
    print("=" * 80)

    # 테스트할 전략들
    strategies = {
        'Grid Trading (ADX Filter ON)': GridTradingStrategy(
            num_grids=30,
            range_pct=10.0,
            profit_per_grid=0.3,
            max_positions=10,
            rebalance_threshold=7.0,
            tight_sl=True,
            use_trend_filter=True,  # ADX 필터 ON
            dynamic_sl=True
        ),
        'Grid Trading (NO Filter)': GridTradingStrategy(
            num_grids=30,
            range_pct=10.0,
            profit_per_grid=0.3,
            max_positions=10,
            rebalance_threshold=7.0,
            tight_sl=True,
            use_trend_filter=False,  # ADX 필터 OFF
            dynamic_sl=True
        ),
        'Adaptive Strategy': AdaptiveStrategy(
            adx_threshold=25,
            allow_short_in_downtrend=True
        ),
        'Trend Following': TrendFollowingStrategy(
            fast_ema=12,
            slow_ema=26,
            adx_threshold=25
        )
    }

    # 각 심볼별로 전략 테스트
    for symbol in ['BTC/USDT', 'ETH/USDT']:
        print(f"\n{'='*80}")
        print(f"{symbol} 백테스트")
        print(f"{'='*80}")

        # 심볼 변환
        binance_symbol = symbol.replace('/', '')

        # 데이터 로드
        loader = BinanceDataLoader(symbol=binance_symbol)
        print(f"\n데이터 로딩 중...")
        df = loader.fetch_historical_data(interval='5m', days=days)

        if df is None:
            print(f"[X] 데이터 로드 실패")
            continue

        # DataFrame을 candles 리스트로 변환
        candles = df.to_dict('records')
        print(f"[OK] {len(candles)}개 캔들 로드 완료")

        # 각 전략 테스트
        results = []
        for strategy_name, strategy in strategies.items():
            print(f"\n[테스트] {strategy_name}...")
            result = simple_backtest(candles, strategy, strategy_name)
            results.append(result)

        # 결과 출력
        print(f"\n{'='*80}")
        print(f"{symbol} 전략 비교 결과")
        print(f"{'='*80}")
        print(f"{'전략':<30} {'거래수':>8} {'승률':>8} {'수익':>12} {'ROI':>10}")
        print("-" * 80)

        for r in sorted(results, key=lambda x: x['roi'], reverse=True):
            print(f"{r['strategy']:<30} {r['total_trades']:>8} "
                  f"{r['win_rate']:>7.1f}% {r['total_profit']:>11.2f} "
                  f"{r['roi']:>9.2f}%")

        # 최고 전략
        best = max(results, key=lambda x: x['roi'])
        print(f"\n[최고 전략] {best['strategy']}")
        print(f"  ROI: {best['roi']:.2f}%")
        print(f"  거래: {best['total_trades']}건 (승률 {best['win_rate']:.1f}%)")
        print(f"  최종 잔액: {best['final_balance']:.2f} USDT")

        # 최고 전략의 최근 거래 5건
        if best['trades']:
            print(f"\n  최근 거래 5건:")
            for trade in best['trades'][-5:]:
                side_emoji = '[LONG]' if trade['side'] == 'long' else '[SHORT]'
                pnl_sign = '+' if trade['pnl_usdt'] > 0 else ''
                print(f"    {trade['entry_time']} {side_emoji} "
                      f"${trade['entry_price']:.2f} -> ${trade['exit_price']:.2f} "
                      f"| {pnl_sign}{trade['pnl_usdt']:.2f} USDT ({pnl_sign}{trade['pnl_pct']:.2f}%) "
                      f"[{trade['reason']}]")

    print(f"\n{'='*80}")
    print("백테스트 완료")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
