"""
그리드 트레이딩 파라미터 최적화

테스트할 조합:
- range_pct: 그리드 범위 (5%, 7%, 10%, 15%)
- num_grids: 그리드 개수 (10, 15, 20, 30)
- profit_per_grid: 목표 수익 (0.3%, 0.5%, 0.8%, 1.0%)
- max_positions: 최대 포지션 (3, 5, 8, 10)
"""
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from grid_strategy import GridTradingStrategy
import itertools


def optimize_grid_parameters():
    """그리드 파라미터 최적화"""

    print("=" * 80)
    print("그리드 트레이딩 파라미터 최적화")
    print("=" * 80)

    # 데이터 로드
    loader = BinanceDataLoader(symbol='ETHUSDT')
    df = loader.fetch_historical_data(interval='5m', days=30)

    if df is None or len(df) == 0:
        print("데이터 로드 실패!")
        return

    print(f"\n데이터: {len(df)} 캔들")
    print(f"기간: {df['datetime'].min()} ~ {df['datetime'].max()}")
    market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
    print(f"시장 변동: {market_change:+.2f}%")

    # 테스트할 파라미터 조합
    param_combinations = {
        'range_pct': [5.0, 7.0, 10.0, 15.0],
        'num_grids': [10, 15, 20, 30],
        'profit_per_grid': [0.3, 0.5, 0.8, 1.0],
        'max_positions': [3, 5, 8, 10],
        'rebalance_threshold': [5.0, 7.0, 10.0]
    }

    # 전체 조합 수
    total_combinations = 1
    for values in param_combinations.values():
        total_combinations *= len(values)

    print(f"\n총 테스트 조합: {total_combinations}개")
    print("=" * 80)

    # 결과 저장
    results = []

    # 빠른 테스트를 위해 일부만 샘플링
    # 전체 조합이 너무 많으면 시간이 오래 걸림
    print("\n[전략 1] 빠른 샘플링: 주요 조합만 테스트")

    # 주요 조합 선택
    test_cases = [
        # 기본 (현재)
        {'range_pct': 5.0, 'num_grids': 10, 'profit_per_grid': 1.0,
         'max_positions': 5, 'rebalance_threshold': 7.0, 'name': '기본'},

        # 넓은 범위
        {'range_pct': 10.0, 'num_grids': 10, 'profit_per_grid': 1.0,
         'max_positions': 5, 'rebalance_threshold': 7.0, 'name': '넓은범위'},

        {'range_pct': 15.0, 'num_grids': 10, 'profit_per_grid': 1.0,
         'max_positions': 5, 'rebalance_threshold': 7.0, 'name': '매우넓은범위'},

        # 촘촘한 그리드
        {'range_pct': 10.0, 'num_grids': 20, 'profit_per_grid': 0.5,
         'max_positions': 8, 'rebalance_threshold': 7.0, 'name': '촘촘한그리드'},

        {'range_pct': 10.0, 'num_grids': 30, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 7.0, 'name': '초촘촘그리드'},

        # 공격적
        {'range_pct': 15.0, 'num_grids': 20, 'profit_per_grid': 0.5,
         'max_positions': 10, 'rebalance_threshold': 5.0, 'name': '공격적'},

        # 보수적
        {'range_pct': 7.0, 'num_grids': 10, 'profit_per_grid': 0.8,
         'max_positions': 3, 'rebalance_threshold': 10.0, 'name': '보수적'},

        # 균형
        {'range_pct': 10.0, 'num_grids': 15, 'profit_per_grid': 0.5,
         'max_positions': 5, 'rebalance_threshold': 7.0, 'name': '균형'},

        # 고빈도
        {'range_pct': 10.0, 'num_grids': 30, 'profit_per_grid': 0.5,
         'max_positions': 10, 'rebalance_threshold': 5.0, 'name': '고빈도'},

        # 안정적
        {'range_pct': 15.0, 'num_grids': 15, 'profit_per_grid': 0.8,
         'max_positions': 8, 'rebalance_threshold': 7.0, 'name': '안정적'},
    ]

    LEVERAGE = 2
    CAPITAL_PCT = 0.90

    for i, params in enumerate(test_cases, 1):
        name = params.pop('name')

        print(f"\n[{i}/{len(test_cases)}] {name} 테스트")
        print(f"  파라미터: {params}")

        strategy = GridTradingStrategy(**params)

        engine = BacktestEngine(
            initial_capital=10000,
            leverage=LEVERAGE,
            maker_fee=0.0002,
            taker_fee=0.0005
        )

        # 출력 억제를 위해 조용히 실행
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            result = engine.run(df, strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)
        finally:
            sys.stdout = old_stdout

        # 결과 저장
        pf = 0
        if result['total_trades'] > 0:
            trades_df = result['trades']
            winning = trades_df[trades_df['pnl'] > 0]
            losing = trades_df[trades_df['pnl'] <= 0]
            if len(winning) > 0 and len(losing) > 0:
                pf = winning['pnl'].sum() / abs(losing['pnl'].sum())

        results.append({
            'name': name,
            'params': params,
            'return': result['total_return'],
            'win_rate': result['win_rate'] if result['total_trades'] > 0 else 0,
            'trades': result['total_trades'],
            'mdd': result.get('max_drawdown', 0),
            'profit_factor': pf
        })

        print(f"  결과: 수익률 {result['total_return']:+.2f}%, "
              f"거래 {result['total_trades']}건, "
              f"승률 {result['win_rate']:.1f}%" if result['total_trades'] > 0 else "거래 없음")

    # 결과 정렬 (수익률 기준)
    results.sort(key=lambda x: x['return'], reverse=True)

    # 상위 결과 출력
    print("\n" + "=" * 80)
    print("최적화 결과 (수익률 기준 상위 10개)")
    print("=" * 80)
    print(f"{'순위':<5} {'전략':<15} {'수익률':>10} {'거래수':>8} {'승률':>8} {'MDD':>10} {'PF':>8}")
    print("-" * 80)

    for i, r in enumerate(results[:10], 1):
        win_rate_str = f"{r['win_rate']:.1f}%" if r['trades'] > 0 else "N/A"
        pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] > 0 else "N/A"

        print(f"{i:<5} {r['name']:<15} {r['return']:>9.2f}% {r['trades']:>8} "
              f"{win_rate_str:>8} {r['mdd']:>9.2f}% {pf_str:>8}")

    # 최고 성과
    best = results[0]
    print("\n" + "=" * 80)
    print("최적 파라미터")
    print("=" * 80)
    print(f"\n전략: {best['name']}")
    print(f"수익률: {best['return']:+.2f}%")
    print(f"거래수: {best['trades']}건")
    print(f"승률: {best['win_rate']:.1f}%" if best['trades'] > 0 else "거래 없음")
    print(f"MDD: {best['mdd']:.2f}%")
    print(f"Profit Factor: {best['profit_factor']:.2f}" if best['profit_factor'] > 0 else "N/A")
    print("\n파라미터:")
    for key, value in best['params'].items():
        print(f"  {key}: {value}")

    # 최적 파라미터로 상세 테스트
    print("\n" + "=" * 80)
    print("최적 파라미터로 상세 백테스트")
    print("=" * 80)

    best_strategy = GridTradingStrategy(**best['params'])

    engine = BacktestEngine(
        initial_capital=10000,
        leverage=LEVERAGE,
        maker_fee=0.0002,
        taker_fee=0.0005
    )

    final_result = engine.run(df, best_strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)

    print(f"\n[최종 결과]")
    print(f"  수익률: {final_result['total_return']:.2f}%")
    print(f"  거래수: {final_result['total_trades']}")
    if final_result['total_trades'] > 0:
        print(f"  승률: {final_result['win_rate']:.1f}%")
        print(f"  MDD: {final_result.get('max_drawdown', 0):.2f}%")

        trades_df = final_result['trades']
        tp_trades = trades_df[trades_df['reason'] == 'take_profit']
        sl_trades = trades_df[trades_df['reason'] == 'stop_loss']

        print(f"\n  TP: {len(tp_trades)}개 ({len(tp_trades)/len(trades_df)*100:.1f}%)")
        print(f"  SL: {len(sl_trades)}개 ({len(sl_trades)/len(trades_df)*100:.1f}%)")

        winning = trades_df[trades_df['pnl'] > 0]
        losing = trades_df[trades_df['pnl'] <= 0]
        if len(winning) > 0 and len(losing) > 0:
            pf = winning['pnl'].sum() / abs(losing['pnl'].sum())
            print(f"\n  Profit Factor: {pf:.2f}")

        print(f"\n  평균 수익 거래: {winning['pnl'].mean():.2f} USDT" if len(winning) > 0 else "")
        print(f"  평균 손실 거래: {losing['pnl'].mean():.2f} USDT" if len(losing) > 0 else "")

    # 비교
    print("\n" + "=" * 80)
    print("기본 설정과 비교")
    print("=" * 80)

    baseline = next(r for r in results if r['name'] == '기본')
    improvement = best['return'] - baseline['return']

    print(f"기본 설정: {baseline['return']:+.2f}%")
    print(f"최적 설정: {best['return']:+.2f}%")
    print(f"개선도: {improvement:+.2f}%p")

    if best['return'] > 0:
        print(f"\n[대성공] 플러스 수익 달성!")
    elif improvement > 0:
        print(f"\n[개선] 손실 {abs(improvement):.2f}%p 감소!")


if __name__ == "__main__":
    optimize_grid_parameters()
