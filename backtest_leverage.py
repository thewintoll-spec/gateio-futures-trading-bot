"""
레버리지별 백테스트 (3x, 5x, 7x, 10x)
V1 Adaptive 전략 사용
"""
import sys
sys.path.append('backtest')
from datetime import datetime, timedelta
from binance_data_loader import BinanceDataLoader
from adaptive_strategy import AdaptiveStrategy


def simple_backtest(candles, strategy, leverage, strategy_name):
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
                pnl_usdt = balance * 0.5 * (pnl_pct / 100) * leverage
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

    # Calculate Sharpe-like metric
    if trades:
        returns = [t['pnl_usdt'] for t in trades]
        avg_return = sum(returns) / len(returns)
        std_dev = (sum([(r - avg_return) ** 2 for r in returns]) / len(returns)) ** 0.5
        sharpe = (avg_return / std_dev) if std_dev > 0 else 0
    else:
        sharpe = 0

    # Average win/loss
    wins = [t['pnl_usdt'] for t in trades if t['pnl_usdt'] > 0]
    losses = [t['pnl_usdt'] for t in trades if t['pnl_usdt'] < 0]
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0

    return {
        'strategy': strategy_name,
        'leverage': leverage,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'total_profit': total_profit,
        'final_balance': balance,
        'roi': roi,
        'max_drawdown': max_dd,
        'sharpe': sharpe,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'trades': trades
    }


def run_leverage_backtest(days, leverages):
    """레버리지별 백테스트"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    print("=" * 100)
    print(f"{days}일 레버리지별 백테스트 (V1 Adaptive Strategy)")
    print("=" * 100)
    print(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"레버리지: {', '.join([f'{lev}x' for lev in leverages])}")
    print(f"시작 자본: 1,000 USDT")
    print(f"자본 배분: 50% per trade")
    print("=" * 100)

    all_results = {}

    for symbol in ['BTC/USDT', 'ETH/USDT']:
        print(f"\n{'='*100}")
        print(f"{symbol} 데이터 로딩 중...")
        print(f"{'='*100}")

        # 심볼 변환
        binance_symbol = symbol.replace('/', '')

        # 데이터 로드
        loader = BinanceDataLoader(symbol=binance_symbol)
        df = loader.fetch_historical_data(interval='5m', days=days)

        if df is None:
            print(f"[X] 데이터 로드 실패")
            continue

        candles = df.to_dict('records')
        print(f"[OK] {len(candles)}개 캔들 로드 완료\n")

        # 각 레버리지별 테스트
        results = []
        for leverage in leverages:
            # 전략 생성 (매번 새로 생성)
            strategy = AdaptiveStrategy(
                adx_threshold=25,
                allow_short_in_downtrend=True
            )

            print(f"  레버리지 {leverage}x 테스트 중...")
            result = simple_backtest(candles, strategy, leverage, f"V1 ({leverage}x)")
            results.append(result)
            print(f"    거래: {result['total_trades']}건, 승률: {result['win_rate']:.1f}%, "
                  f"ROI: {result['roi']:+.2f}%, MDD: {result['max_drawdown']:.1f}%")

        all_results[symbol] = results

    return all_results


def print_results(results, days):
    """결과 출력"""
    print(f"\n{'='*100}")
    print(f"{days}일 레버리지별 비교 결과")
    print(f"{'='*100}")
    print(f"{'심볼':<12} {'레버리지':<10} {'거래':>6} {'승률':>7} {'ROI':>9} "
          f"{'MDD':>7} {'Sharpe':>7} {'평균승':>9} {'평균패':>9}")
    print("-" * 100)

    leverage_summary = {}

    for symbol in ['BTC/USDT', 'ETH/USDT']:
        if symbol not in results:
            continue

        for result in results[symbol]:
            leverage = result['leverage']

            if leverage not in leverage_summary:
                leverage_summary[leverage] = {
                    'total_roi': 0,
                    'total_trades': 0,
                    'count': 0
                }

            leverage_summary[leverage]['total_roi'] += result['roi']
            leverage_summary[leverage]['total_trades'] += result['total_trades']
            leverage_summary[leverage]['count'] += 1

            print(f"{symbol:<12} {result['leverage']:>2}x{' '*7} {result['total_trades']:>6} "
                  f"{result['win_rate']:>6.1f}% {result['roi']:>8.2f}% "
                  f"{result['max_drawdown']:>6.1f}% {result['sharpe']:>7.2f} "
                  f"{result['avg_win']:>9.2f} {result['avg_loss']:>9.2f}")

        print()

    # 레버리지별 요약
    print("-" * 100)
    print(f"{'레버리지별 평균':<12}")
    print("-" * 100)

    best_leverage = None
    best_roi = -float('inf')

    for leverage in sorted(leverage_summary.keys()):
        summary = leverage_summary[leverage]
        avg_roi = summary['total_roi'] / summary['count']
        avg_trades = summary['total_trades'] / summary['count']

        print(f"  {leverage}x: 평균 ROI {avg_roi:+.2f}%, 평균 거래 {avg_trades:.0f}건")

        if avg_roi > best_roi:
            best_roi = avg_roi
            best_leverage = leverage

    print("\n" + "=" * 100)
    print(f"최적 레버리지: {best_leverage}x (평균 ROI: {best_roi:+.2f}%)")
    print("=" * 100)


def main():
    print("\n")
    print("=" * 100)
    print("레버리지별 백테스트 (V1 Adaptive Strategy)")
    print("=" * 100)
    print()

    leverages = [3, 5, 7, 10]

    # 30일 백테스트
    print("\n[30일 백테스트]")
    results_30 = run_leverage_backtest(30, leverages)
    print_results(results_30, 30)

    print("\n\n")

    # 60일 백테스트
    print("[60일 백테스트]")
    results_60 = run_leverage_backtest(60, leverages)
    print_results(results_60, 60)

    # 최종 요약
    print("\n\n")
    print("=" * 100)
    print("최종 요약 및 추천")
    print("=" * 100)

    print("\n[30일 심볼별 결과]")
    for symbol in ['BTC/USDT', 'ETH/USDT']:
        if symbol not in results_30:
            continue
        print(f"\n{symbol}:")
        for result in results_30[symbol]:
            print(f"  {result['leverage']}x: ROI {result['roi']:+.2f}%, "
                  f"MDD {result['max_drawdown']:.1f}%, 거래 {result['total_trades']}건")

    print("\n[60일 심볼별 결과]")
    for symbol in ['BTC/USDT', 'ETH/USDT']:
        if symbol not in results_60:
            continue
        print(f"\n{symbol}:")
        for result in results_60[symbol]:
            print(f"  {result['leverage']}x: ROI {result['roi']:+.2f}%, "
                  f"MDD {result['max_drawdown']:.1f}%, 거래 {result['total_trades']}건")

    print("\n" + "=" * 100)
    print("백테스트 완료!")
    print("=" * 100)


if __name__ == "__main__":
    main()
