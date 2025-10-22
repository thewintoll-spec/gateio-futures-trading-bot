"""
그리드 트레이딩 파라미터 최적화 V2

목표: 현재 +1.69%를 넘는 파라미터 찾기

현재 설정 (baseline):
- num_grids=30, range_pct=10.0, profit_per_grid=0.3
- max_positions=10, rebalance_threshold=7.0
- tight_sl=True, use_trend_filter=True, dynamic_sl=True
- 결과: +1.69% (30일 백테스트)

최적화 전략:
1. 현재 설정 주변 세밀 탐색
2. 극단적인 설정 테스트
3. 조합 효과 분석
"""
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from grid_strategy import GridTradingStrategy
import sys
from io import StringIO


def optimize_grid_v2():
    """그리드 파라미터 최적화 V2 - 더 세밀하게"""

    print("=" * 80)
    print("그리드 트레이딩 파라미터 최적화 V2")
    print("=" * 80)
    print("\n목표: 현재 +1.69%를 넘는 설정 찾기")
    print("현재 설정: 30 grids, ±10% range, 0.3% profit, 10 max pos")

    # 데이터 로드
    loader = BinanceDataLoader(symbol='ETHUSDT')
    df = loader.fetch_historical_data(interval='5m', days=30)

    if df is None or len(df) == 0:
        print("\n❌ 데이터 로드 실패!")
        return

    print(f"\n데이터: {len(df)} 캔들")
    print(f"기간: {df['datetime'].min()} ~ {df['datetime'].max()}")
    market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
    print(f"시장 변동: {market_change:+.2f}%")

    LEVERAGE = 2
    CAPITAL_PCT = 0.90

    # 테스트 케이스들
    test_cases = [
        # ===== 1. 현재 설정 (baseline) =====
        {'num_grids': 30, 'range_pct': 10.0, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '현재설정(Baseline)'},

        # ===== 2. 그리드 개수 변화 (범위 고정) =====
        {'num_grids': 20, 'range_pct': 10.0, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '그리드20개'},

        {'num_grids': 40, 'range_pct': 10.0, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '그리드40개'},

        {'num_grids': 50, 'range_pct': 10.0, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '그리드50개'},

        # ===== 3. 가격 범위 변화 (그리드 고정) =====
        {'num_grids': 30, 'range_pct': 8.0, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '범위±8%'},

        {'num_grids': 30, 'range_pct': 12.0, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '범위±12%'},

        {'num_grids': 30, 'range_pct': 15.0, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '범위±15%'},

        # ===== 4. 그리드당 수익 변화 =====
        {'num_grids': 30, 'range_pct': 10.0, 'profit_per_grid': 0.2,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '수익0.2%'},

        {'num_grids': 30, 'range_pct': 10.0, 'profit_per_grid': 0.4,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '수익0.4%'},

        {'num_grids': 30, 'range_pct': 10.0, 'profit_per_grid': 0.5,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '수익0.5%'},

        # ===== 5. 최대 포지션 변화 =====
        {'num_grids': 30, 'range_pct': 10.0, 'profit_per_grid': 0.3,
         'max_positions': 5, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '최대5포지션'},

        {'num_grids': 30, 'range_pct': 10.0, 'profit_per_grid': 0.3,
         'max_positions': 15, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '최대15포지션'},

        {'num_grids': 30, 'range_pct': 10.0, 'profit_per_grid': 0.3,
         'max_positions': 20, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '최대20포지션'},

        # ===== 6. 리밸런싱 임계값 변화 =====
        {'num_grids': 30, 'range_pct': 10.0, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 5.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '리밸5%'},

        {'num_grids': 30, 'range_pct': 10.0, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 10.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '리밸10%'},

        # ===== 7. 필터 조합 변화 =====
        {'num_grids': 30, 'range_pct': 10.0, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': False, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '타이트SL끄기'},

        {'num_grids': 30, 'range_pct': 10.0, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': False, 'dynamic_sl': True,
         'name': '추세필터끄기'},

        {'num_grids': 30, 'range_pct': 10.0, 'profit_per_grid': 0.3,
         'max_positions': 10, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': False,
         'name': '동적SL끄기'},

        # ===== 8. 복합 최적화 - 촘촘 & 작은 수익 =====
        {'num_grids': 40, 'range_pct': 10.0, 'profit_per_grid': 0.2,
         'max_positions': 15, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '초촘촘+작은수익'},

        {'num_grids': 50, 'range_pct': 10.0, 'profit_per_grid': 0.2,
         'max_positions': 20, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '극촘촘+작은수익'},

        # ===== 9. 복합 최적화 - 넓은 범위 & 큰 수익 =====
        {'num_grids': 20, 'range_pct': 15.0, 'profit_per_grid': 0.5,
         'max_positions': 8, 'rebalance_threshold': 10.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '넓은범위+큰수익'},

        # ===== 10. 공격적 설정 =====
        {'num_grids': 40, 'range_pct': 12.0, 'profit_per_grid': 0.4,
         'max_positions': 15, 'rebalance_threshold': 5.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '공격적'},

        # ===== 11. 보수적 설정 =====
        {'num_grids': 20, 'range_pct': 8.0, 'profit_per_grid': 0.4,
         'max_positions': 5, 'rebalance_threshold': 10.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '보수적'},

        # ===== 12. 균형 설정 =====
        {'num_grids': 30, 'range_pct': 12.0, 'profit_per_grid': 0.35,
         'max_positions': 12, 'rebalance_threshold': 7.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '균형형'},

        # ===== 13. 극단 설정 =====
        {'num_grids': 60, 'range_pct': 15.0, 'profit_per_grid': 0.15,
         'max_positions': 25, 'rebalance_threshold': 5.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '극단-초고빈도'},

        {'num_grids': 15, 'range_pct': 5.0, 'profit_per_grid': 0.8,
         'max_positions': 3, 'rebalance_threshold': 15.0,
         'tight_sl': True, 'use_trend_filter': True, 'dynamic_sl': True,
         'name': '극단-초저빈도'},
    ]

    print(f"\n총 테스트: {len(test_cases)}가지 설정")
    print("=" * 80)

    results = []

    for i, params in enumerate(test_cases, 1):
        name = params.pop('name')

        print(f"\n[{i}/{len(test_cases)}] {name}")

        strategy = GridTradingStrategy(**params)

        engine = BacktestEngine(
            initial_capital=10000,
            leverage=LEVERAGE,
            maker_fee=0.0002,
            taker_fee=0.0005
        )

        # 조용히 실행
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            result = engine.run(df, strategy, capital_pct=CAPITAL_PCT, allow_reversal=False)
        finally:
            sys.stdout = old_stdout

        # Profit Factor 계산
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

        # 실시간 피드백
        status = "[+]" if result['total_return'] > 1.69 else "[~]" if result['total_return'] > 0 else "[-]"
        print(f"  {status} 수익률: {result['total_return']:+.2f}%, "
              f"거래: {result['total_trades']}건, "
              f"승률: {result['win_rate']:.1f}%" if result['total_trades'] > 0 else "거래 없음")

    # 결과 정렬 (수익률 기준)
    results.sort(key=lambda x: x['return'], reverse=True)

    # 상위 결과 출력
    print("\n" + "=" * 80)
    print("최적화 결과 (수익률 TOP 10)")
    print("=" * 80)
    print(f"{'순위':<5} {'전략':<20} {'수익률':>10} {'거래':>6} {'승률':>8} {'MDD':>8} {'PF':>6}")
    print("-" * 80)

    for i, r in enumerate(results[:10], 1):
        win_rate_str = f"{r['win_rate']:.1f}%" if r['trades'] > 0 else "N/A"
        pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] > 0 else "N/A"
        status = "[1]" if r['return'] > 1.69 else "[2]" if r['return'] > 0 else "[3]"

        print(f"{i:<5} {status}{r['name']:<19} {r['return']:>9.2f}% {r['trades']:>6} "
              f"{win_rate_str:>8} {r['mdd']:>7.2f}% {pf_str:>6}")

    # 최고 성과
    best = results[0]
    print("\n" + "=" * 80)
    print("[ 최적 파라미터 ]")
    print("=" * 80)
    print(f"\n전략: {best['name']}")
    print(f"수익률: {best['return']:+.2f}%")
    print(f"거래수: {best['trades']}건")
    if best['trades'] > 0:
        print(f"승률: {best['win_rate']:.1f}%")
    print(f"MDD: {best['mdd']:.2f}%")
    if best['profit_factor'] > 0:
        print(f"Profit Factor: {best['profit_factor']:.2f}")

    print("\n파라미터:")
    for key, value in best['params'].items():
        print(f"  {key}: {value}")

    # Baseline과 비교
    baseline = next(r for r in results if r['name'] == '현재설정(Baseline)')
    improvement = best['return'] - baseline['return']

    print("\n" + "=" * 80)
    print("Baseline 대비 개선도")
    print("=" * 80)
    print(f"Baseline:  {baseline['return']:+.2f}%")
    print(f"최적설정:  {best['return']:+.2f}%")
    print(f"개선:      {improvement:+.2f}%p")

    if best['return'] > baseline['return']:
        print(f"\n[SUCCESS] 개선 성공! {improvement:+.2f}%p 향상")
        if best['return'] > 2.0:
            print("[GREAT] 수익률 2% 돌파!")
    else:
        print(f"\n[INFO] 현재 설정이 최적")

    # 1.69%를 넘는 설정들
    better_than_baseline = [r for r in results if r['return'] > 1.69]
    if better_than_baseline:
        print(f"\n[GOOD] Baseline(+1.69%)을 넘는 설정: {len(better_than_baseline)}개")
        print("\n상위 5개:")
        for i, r in enumerate(better_than_baseline[:5], 1):
            print(f"  {i}. {r['name']}: {r['return']:+.2f}%")

    # 최적 설정으로 상세 백테스트
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
    print(f"  초기 자본: 10,000 USDT")
    print(f"  최종 자본: {final_result['final_capital']:.2f} USDT")
    print(f"  수익률: {final_result['total_return']:.2f}%")
    print(f"  순수익: {final_result['final_capital'] - 10000:.2f} USDT")
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

        if len(winning) > 0:
            print(f"\n  평균 수익 거래: {winning['pnl'].mean():.2f} USDT")
            print(f"  최대 수익: {winning['pnl'].max():.2f} USDT")

        if len(losing) > 0:
            print(f"  평균 손실 거래: {losing['pnl'].mean():.2f} USDT")
            print(f"  최대 손실: {losing['pnl'].min():.2f} USDT")

        if len(winning) > 0 and len(losing) > 0:
            pf = winning['pnl'].sum() / abs(losing['pnl'].sum())
            print(f"\n  Profit Factor: {pf:.2f}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    optimize_grid_v2()
