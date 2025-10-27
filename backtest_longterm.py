"""
Adaptive V1 vs V2 장기 백테스트 (30일, 60일)
"""
import sys
sys.path.append('backtest')
from datetime import datetime, timedelta
from binance_data_loader import BinanceDataLoader
from adaptive_strategy import AdaptiveStrategy
from adaptive_strategy_v2 import AdaptiveStrategyV2


def simple_backtest(candles, strategy, strategy_name):
    """간단한 백테스트"""
    balance = 1000  # 시작 자본
    trades = []

    in_position = False
    entry_price = 0
    entry_time = None
    position_side = None

    # 디버그 출력 억제
    import io
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

                # Record result for V2
                if hasattr(strategy, 'record_trade_result'):
                    strategy.record_trade_result(pnl_usdt < 0)

                in_position = False

    # 결과 계산
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t['pnl_usdt'] > 0])
    losing_trades = len([t for t in trades if t['pnl_usdt'] < 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    total_profit = sum([t['pnl_usdt'] for t in trades])
    roi = (balance - 1000) / 1000 * 100

    # Calculate max drawdown
    peak = 1000
    max_dd = 0
    running_balance = 1000

    for trade in trades:
        running_balance += trade['pnl_usdt']
        if running_balance > peak:
            peak = running_balance
        dd = (peak - running_balance) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Calculate Sharpe-like metric (simple version)
    if trades:
        returns = [t['pnl_usdt'] for t in trades]
        avg_return = sum(returns) / len(returns)
        std_dev = (sum([(r - avg_return) ** 2 for r in returns]) / len(returns)) ** 0.5
        sharpe = (avg_return / std_dev) if std_dev > 0 else 0
    else:
        sharpe = 0

    return {
        'strategy': strategy_name,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'total_profit': total_profit,
        'final_balance': balance,
        'roi': roi,
        'max_drawdown': max_dd,
        'sharpe': sharpe,
        'trades': trades
    }


def run_backtest_for_period(days, label):
    """특정 기간에 대한 백테스트 실행"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    print("=" * 80)
    print(f"{label} 백테스트")
    print("=" * 80)
    print(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"총 기간: {days}일")
    print(f"시작 자본: 1,000 USDT")
    print(f"레버리지: 7x")
    print(f"자본 배분: 50% per trade")
    print("=" * 80)

    # 테스트할 전략들
    strategies = {
        'V1 (Original)': AdaptiveStrategy(
            adx_threshold=25,
            allow_short_in_downtrend=True
        ),
        'V2 (Anti-Whipsaw)': AdaptiveStrategyV2(
            adx_threshold=35,
            adx_strong=45,
            allow_short_in_downtrend=True,
            ema_period=20,
            atr_multiplier=2.5
        )
    }

    # 각 심볼별로 전략 테스트
    all_results = {}

    for symbol in ['BTC/USDT', 'ETH/USDT']:
        print(f"\n{'='*80}")
        print(f"{symbol} 테스트 중...")
        print(f"{'='*80}")

        # 심볼 변환
        binance_symbol = symbol.replace('/', '')

        # 데이터 로드
        loader = BinanceDataLoader(symbol=binance_symbol)
        print(f"데이터 로딩 중... (약 {days}일)")
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
            print(f"  {strategy_name} 테스트 중...")
            result = simple_backtest(candles, strategy, strategy_name)
            results.append(result)
            print(f"    거래: {result['total_trades']}건, 승률: {result['win_rate']:.1f}%, ROI: {result['roi']:+.2f}%")

        all_results[symbol] = results

    # 결과 출력
    print(f"\n{'='*80}")
    print(f"{label} 비교 결과")
    print(f"{'='*80}")
    print(f"{'심볼':<10} {'전략':<20} {'거래':>6} {'승률':>7} {'ROI':>9} {'MDD':>7} {'Sharpe':>7}")
    print("-" * 80)

    total_v1_roi = 0
    total_v2_roi = 0
    total_v1_trades = 0
    total_v2_trades = 0

    for symbol in ['BTC/USDT', 'ETH/USDT']:
        if symbol not in all_results:
            continue

        results = all_results[symbol]
        v1, v2 = results[0], results[1]

        print(f"{symbol:<10} {v1['strategy']:<20} {v1['total_trades']:>6} "
              f"{v1['win_rate']:>6.1f}% {v1['roi']:>8.2f}% {v1['max_drawdown']:>6.1f}% {v1['sharpe']:>7.2f}")
        print(f"{symbol:<10} {v2['strategy']:<20} {v2['total_trades']:>6} "
              f"{v2['win_rate']:>6.1f}% {v2['roi']:>8.2f}% {v2['max_drawdown']:>6.1f}% {v2['sharpe']:>7.2f}")

        total_v1_roi += v1['roi']
        total_v2_roi += v2['roi']
        total_v1_trades += v1['total_trades']
        total_v2_trades += v2['total_trades']

        # 개선율
        if v1['total_trades'] > 0:
            improvement = v2['roi'] - v1['roi']
            if improvement > 0:
                print(f"{'':>10} => V2가 {improvement:+.2f}%p 더 좋음")
            else:
                print(f"{'':>10} => V1이 {-improvement:+.2f}%p 더 좋음")
        print()

    # 전체 요약
    print("-" * 80)
    print(f"{'전체 합계':<10}")
    print(f"  V1: 거래 {total_v1_trades}건, 평균 ROI {total_v1_roi/2:.2f}%")
    print(f"  V2: 거래 {total_v2_trades}건, 평균 ROI {total_v2_roi/2:.2f}%")

    avg_improvement = (total_v2_roi - total_v1_roi) / 2
    if avg_improvement > 0:
        print(f"  => V2가 평균 {avg_improvement:+.2f}%p 개선")
    else:
        print(f"  => V1이 평균 {-avg_improvement:+.2f}%p 더 좋음")

    print("=" * 80)

    return all_results


def main():
    print("\n")
    print("=" * 80)
    print("Adaptive V1 vs V2 장기 백테스트")
    print("=" * 80)
    print()

    # 30일 백테스트
    results_30 = run_backtest_for_period(30, "30일")

    print("\n\n")

    # 60일 백테스트
    results_60 = run_backtest_for_period(60, "60일")

    print("\n\n")
    print("=" * 80)
    print("최종 요약")
    print("=" * 80)

    print("\n[30일 결과]")
    for symbol in ['BTC/USDT', 'ETH/USDT']:
        if symbol in results_30:
            v1, v2 = results_30[symbol]
            print(f"{symbol}: V1 {v1['roi']:+.2f}% vs V2 {v2['roi']:+.2f}% (차이: {v2['roi']-v1['roi']:+.2f}%p)")

    print("\n[60일 결과]")
    for symbol in ['BTC/USDT', 'ETH/USDT']:
        if symbol in results_60:
            v1, v2 = results_60[symbol]
            print(f"{symbol}: V1 {v1['roi']:+.2f}% vs V2 {v2['roi']:+.2f}% (차이: {v2['roi']-v1['roi']:+.2f}%p)")

    print("\n" + "=" * 80)
    print("백테스트 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()
