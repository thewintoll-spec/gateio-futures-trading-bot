"""
Adaptive V1 vs V2 비교 백테스트
최근 5일간 성능 비교
"""
import sys
sys.path.append('backtest')
from datetime import datetime
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

    # Calculate average win/loss
    wins = [t['pnl_usdt'] for t in trades if t['pnl_usdt'] > 0]
    losses = [t['pnl_usdt'] for t in trades if t['pnl_usdt'] < 0]

    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0

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
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'trades': trades
    }


def main():
    # 백테스트 기간
    start_date = datetime(2025, 10, 23, 2, 42, 25)
    end_date = datetime.now()
    days = (end_date - start_date).days + 1

    print("=" * 80)
    print("Adaptive V1 vs V2 비교 백테스트")
    print("=" * 80)
    print(f"기간: {start_date} ~ {end_date}")
    print(f"총 기간: {(end_date - start_date).total_seconds() / 3600:.1f}시간")
    print(f"시작 자본: 1,000 USDT")
    print(f"레버리지: 7x")
    print(f"자본 배분: 50% per trade")
    print("=" * 80)

    # V2 개선사항
    print("\n[V2 개선사항]")
    print("1. ADX threshold: 25 -> 35 (더 강한 트렌드만 진입)")
    print("2. Strong trend: ADX 45+ (공격적 진입)")
    print("3. Trend confirmation: EMA + 가격 위치 + 최근 캔들 방향")
    print("4. Volatility filter: ATR < 3% (변동성 너무 높으면 대기)")
    print("5. Loss protection: 연속 3회 손실 시 대기")
    print("=" * 80)

    # 테스트할 전략들
    strategies = {
        'Adaptive V1 (Original)': AdaptiveStrategy(
            adx_threshold=25,
            allow_short_in_downtrend=True
        ),
        'Adaptive V2 (Anti-Whipsaw)': AdaptiveStrategyV2(
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

        all_results[symbol] = results

        # 결과 출력
        print(f"\n{'='*80}")
        print(f"{symbol} 비교 결과")
        print(f"{'='*80}")
        print(f"{'전략':<30} {'거래수':>8} {'승률':>8} {'수익':>12} {'ROI':>10} {'MDD':>8}")
        print("-" * 80)

        for r in results:
            print(f"{r['strategy']:<30} {r['total_trades']:>8} "
                  f"{r['win_rate']:>7.1f}% {r['total_profit']:>11.2f} "
                  f"{r['roi']:>9.2f}% {r['max_drawdown']:>7.1f}%")

        # 개선율 계산
        if len(results) == 2:
            v1, v2 = results[0], results[1]
            print(f"\n[개선율]")

            if v1['total_trades'] > 0:
                win_rate_improvement = v2['win_rate'] - v1['win_rate']
                roi_improvement = v2['roi'] - v1['roi']
                trade_reduction = ((v1['total_trades'] - v2['total_trades']) / v1['total_trades'] * 100) if v1['total_trades'] > 0 else 0

                print(f"  승률: {v1['win_rate']:.1f}% -> {v2['win_rate']:.1f}% ({win_rate_improvement:+.1f}%p)")
                print(f"  ROI: {v1['roi']:.2f}% -> {v2['roi']:.2f}% ({roi_improvement:+.2f}%p)")
                print(f"  거래수: {v1['total_trades']}건 -> {v2['total_trades']}건 ({trade_reduction:+.1f}%)")
                print(f"  MDD: {v1['max_drawdown']:.1f}% -> {v2['max_drawdown']:.1f}%")
            else:
                print(f"  V1 거래 없음, V2: {v2['total_trades']}건")

    # 전체 요약
    print(f"\n{'='*80}")
    print("전체 요약")
    print(f"{'='*80}")

    for symbol in ['BTC/USDT', 'ETH/USDT']:
        if symbol not in all_results:
            continue

        results = all_results[symbol]
        v1 = results[0]
        v2 = results[1]

        print(f"\n{symbol}:")
        print(f"  V1: {v1['total_trades']}건 | 승률 {v1['win_rate']:.1f}% | ROI {v1['roi']:+.2f}%")
        print(f"  V2: {v2['total_trades']}건 | 승률 {v2['win_rate']:.1f}% | ROI {v2['roi']:+.2f}%")

        if v1['roi'] < 0 and v2['roi'] > v1['roi']:
            improvement = v2['roi'] - v1['roi']
            print(f"  => V2가 {improvement:+.2f}%p 개선!")
        elif v2['roi'] > v1['roi']:
            print(f"  => V2가 더 좋음!")

    print(f"\n{'='*80}")
    print("백테스트 완료")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
