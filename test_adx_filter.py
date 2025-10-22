"""
ADX 시장 상태 필터 테스트

목적: ADX 필터 적용 전후 비교
- 필터 없음: 모든 상황에서 거래
- 필터 적용: 횡보장에서만 거래
"""
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from grid_strategy import GridTradingStrategy


def test_adx_filter():
    """ADX 필터 효과 테스트"""

    print("=" * 80)
    print("ADX 시장 상태 필터 테스트")
    print("=" * 80)
    print("\n목적: 추세장 회피로 손실 감소 + 횡보장 집중으로 수익 증대")

    loader = BinanceDataLoader(symbol='ETHUSDT')

    LEVERAGE = 2
    CAPITAL_PCT = 0.90

    # 기본 파라미터
    base_params = {
        'num_grids': 30,
        'range_pct': 10.0,
        'profit_per_grid': 0.3,
        'max_positions': 10,
        'rebalance_threshold': 7.0,
        'tight_sl': True,
        'use_trend_filter': True,
        'dynamic_sl': True
    }

    # 테스트 케이스
    test_cases = [
        {
            'name': '필터 없음 (기존)',
            'params': {**base_params, 'use_regime_filter': False}
        },
        {
            'name': 'ADX 필터 (25)',
            'params': {**base_params, 'use_regime_filter': True, 'adx_threshold': 25}
        },
        {
            'name': 'ADX 필터 (20)',
            'params': {**base_params, 'use_regime_filter': True, 'adx_threshold': 20}
        },
        {
            'name': 'ADX 필터 (30)',
            'params': {**base_params, 'use_regime_filter': True, 'adx_threshold': 30}
        }
    ]

    # 기간별 테스트
    periods = [30, 60, 90]

    all_results = {}

    for days in periods:
        print(f"\n{'='*80}")
        print(f"[{days}일 백테스트]")
        print(f"{'='*80}")

        df = loader.fetch_historical_data(interval='5m', days=days)

        if df is None or len(df) == 0:
            print(f"데이터 로드 실패! ({days}일)")
            continue

        print(f"\n데이터: {len(df)} 캔들")
        print(f"기간: {df['datetime'].min()} ~ {df['datetime'].max()}")
        market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
        print(f"시장 변동: {market_change:+.2f}%")

        all_results[days] = {}

        for test_case in test_cases:
            name = test_case['name']
            params = test_case['params']

            print(f"\n[{name}]")

            strategy = GridTradingStrategy(**params)
            engine = BacktestEngine(
                initial_capital=10000,
                leverage=LEVERAGE,
                maker_fee=0.0002,
                taker_fee=0.0005
            )

            # 조용히 실행
            import sys
            from io import StringIO
            old_stdout = sys.stdout
            sys.stdout = StringIO()

            try:
                result = engine.run(df, strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)
            finally:
                sys.stdout = old_stdout

            # 결과 저장
            all_results[days][name] = {
                'return': result['total_return'],
                'trades': result['total_trades'],
                'win_rate': result['win_rate'] if result['total_trades'] > 0 else 0,
                'mdd': result.get('max_drawdown', 0),
                'final_capital': result['final_capital']
            }

            print(f"  수익률: {result['total_return']:+.2f}%")
            print(f"  거래수: {result['total_trades']}건")
            if result['total_trades'] > 0:
                print(f"  승률: {result['win_rate']:.1f}%")
                print(f"  MDD: {result.get('max_drawdown', 0):.2f}%")

    # 종합 비교
    print("\n" + "=" * 80)
    print("종합 결과 비교")
    print("=" * 80)

    for name in [tc['name'] for tc in test_cases]:
        print(f"\n[{name}]")
        print(f"{'기간':<10} {'수익률':>10} {'거래':>8} {'승률':>8} {'MDD':>8}")
        print("-" * 60)

        for days in periods:
            if days in all_results and name in all_results[days]:
                r = all_results[days][name]
                win_rate_str = f"{r['win_rate']:.1f}%" if r['trades'] > 0 else "N/A"

                status = "[+]" if r['return'] > 0 else "[-]"
                print(f"{days}일{'':<6} {status} {r['return']:>7.2f}% {r['trades']:>8} "
                      f"{win_rate_str:>8} {r['mdd']:>7.2f}%")

    # ADX 필터 효과 분석
    print("\n" + "=" * 80)
    print("ADX 필터 효과 분석")
    print("=" * 80)

    baseline_name = '필터 없음 (기존)'
    adx_name = 'ADX 필터 (25)'

    for days in periods:
        if days not in all_results:
            continue

        baseline = all_results[days].get(baseline_name)
        adx = all_results[days].get(adx_name)

        if not baseline or not adx:
            continue

        improvement = adx['return'] - baseline['return']
        trade_reduction = baseline['trades'] - adx['trades']
        trade_reduction_pct = (trade_reduction / baseline['trades'] * 100) if baseline['trades'] > 0 else 0

        print(f"\n[{days}일]")
        print(f"  필터 없음: {baseline['return']:+.2f}% ({baseline['trades']}건)")
        print(f"  ADX 필터: {adx['return']:+.2f}% ({adx['trades']}건)")
        print(f"  개선도: {improvement:+.2f}%p")
        print(f"  거래 감소: {trade_reduction}건 ({trade_reduction_pct:.0f}% 감소)")

        if improvement > 0:
            print(f"  결과: [개선] ADX 필터가 효과적!")
        elif improvement > -0.5:
            print(f"  결과: [비슷] 큰 차이 없음")
        else:
            print(f"  결과: [악화] 필터 없는 게 나음")

    # 최종 추천
    print("\n" + "=" * 80)
    print("최종 분석 및 추천")
    print("=" * 80)

    # 90일 기준 비교
    if 90 in all_results:
        results_90 = all_results[90]
        best = max(results_90.items(), key=lambda x: x[1]['return'])
        best_name = best[0]
        best_result = best[1]

        print(f"\n[90일 기준 최고 성과]: {best_name}")
        print(f"  수익률: {best_result['return']:+.2f}%")
        print(f"  거래수: {best_result['trades']}건")
        print(f"  승률: {best_result['win_rate']:.1f}%")
        print(f"  MDD: {best_result['mdd']:.2f}%")

        # 모든 기간에서 플러스인지 확인
        all_positive = all(
            all_results[days][best_name]['return'] > 0
            for days in periods
            if days in all_results and best_name in all_results[days]
        )

        if all_positive:
            print(f"\n[EXCELLENT] 모든 기간에서 플러스 수익!")
            print(f"추천: '{best_name}' 설정을 실전에 적용하세요.")
        else:
            print(f"\n[CAUTION] 일부 기간에서 마이너스")
            print(f"추천: 테스트넷에서 추가 검증 필요")

    # ADX 임계값 비교
    adx_variants = ['ADX 필터 (20)', 'ADX 필터 (25)', 'ADX 필터 (30)']
    if 90 in all_results:
        print(f"\n[ADX 임계값 비교 (90일)]")
        for name in adx_variants:
            if name in all_results[90]:
                r = all_results[90][name]
                print(f"  {name}: {r['return']:+.2f}% ({r['trades']}건)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_adx_filter()
