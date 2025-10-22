"""
그리드 전략 장기 백테스트

목적: 더 많은 거래 샘플로 전략 검증
- 60일 백테스트
- 90일 백테스트
- 현재 설정 vs 균형형 비교
"""
from backtest.binance_data_loader import BinanceDataLoader
from backtest.backtest import BacktestEngine
from grid_strategy import GridTradingStrategy


def test_long_term():
    """장기 백테스트 (60일, 90일)"""

    print("=" * 80)
    print("그리드 전략 장기 백테스트")
    print("=" * 80)
    print("\n목적: 더 많은 거래 샘플로 전략 검증")

    loader = BinanceDataLoader(symbol='ETHUSDT')

    LEVERAGE = 2
    CAPITAL_PCT = 0.90

    # 테스트할 전략들
    strategies = {
        '현재설정': {
            'num_grids': 30,
            'range_pct': 10.0,
            'profit_per_grid': 0.3,
            'max_positions': 10,
            'rebalance_threshold': 7.0,
            'tight_sl': True,
            'use_trend_filter': True,
            'dynamic_sl': True
        },
        '균형형': {
            'num_grids': 30,
            'range_pct': 12.0,
            'profit_per_grid': 0.35,
            'max_positions': 12,
            'rebalance_threshold': 7.0,
            'tight_sl': True,
            'use_trend_filter': True,
            'dynamic_sl': True
        },
        '최대20포지션': {
            'num_grids': 30,
            'range_pct': 10.0,
            'profit_per_grid': 0.3,
            'max_positions': 20,
            'rebalance_threshold': 7.0,
            'tight_sl': True,
            'use_trend_filter': True,
            'dynamic_sl': True
        }
    }

    # 테스트 기간들
    periods = [30, 60, 90]

    all_results = {}

    for days in periods:
        print(f"\n{'='*80}")
        print(f"[{days}일 백테스트]")
        print(f"{'='*80}")

        # 데이터 로드
        df = loader.fetch_historical_data(interval='5m', days=days)

        if df is None or len(df) == 0:
            print(f"데이터 로드 실패! ({days}일)")
            continue

        print(f"\n데이터: {len(df)} 캔들")
        print(f"기간: {df['datetime'].min()} ~ {df['datetime'].max()}")
        market_change = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
        print(f"시장 변동: {market_change:+.2f}%")

        all_results[days] = {}

        for strategy_name, params in strategies.items():
            print(f"\n[{strategy_name}]")

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

            # Profit Factor 계산
            pf = 0
            avg_win = 0
            avg_loss = 0
            if result['total_trades'] > 0:
                trades_df = result['trades']
                winning = trades_df[trades_df['pnl'] > 0]
                losing = trades_df[trades_df['pnl'] <= 0]

                if len(winning) > 0:
                    avg_win = winning['pnl'].mean()
                if len(losing) > 0:
                    avg_loss = losing['pnl'].mean()

                if len(winning) > 0 and len(losing) > 0:
                    pf = winning['pnl'].sum() / abs(losing['pnl'].sum())

            all_results[days][strategy_name] = {
                'return': result['total_return'],
                'trades': result['total_trades'],
                'win_rate': result['win_rate'] if result['total_trades'] > 0 else 0,
                'mdd': result.get('max_drawdown', 0),
                'pf': pf,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'final_capital': result['final_capital']
            }

            # 결과 출력
            print(f"  수익률: {result['total_return']:+.2f}%")
            print(f"  거래수: {result['total_trades']}건")
            if result['total_trades'] > 0:
                print(f"  승률: {result['win_rate']:.1f}%")
                print(f"  MDD: {result.get('max_drawdown', 0):.2f}%")
                if pf > 0:
                    print(f"  Profit Factor: {pf:.2f}")
                if avg_win > 0:
                    print(f"  평균 수익: {avg_win:.2f} USDT")
                if avg_loss < 0:
                    print(f"  평균 손실: {avg_loss:.2f} USDT")

    # 종합 비교표
    print("\n" + "=" * 80)
    print("종합 결과 비교")
    print("=" * 80)

    for strategy_name in strategies.keys():
        print(f"\n[{strategy_name}]")
        print(f"{'기간':<10} {'수익률':>10} {'거래':>8} {'승률':>8} {'MDD':>8} {'PF':>8}")
        print("-" * 60)

        for days in periods:
            if days in all_results and strategy_name in all_results[days]:
                r = all_results[days][strategy_name]
                win_rate_str = f"{r['win_rate']:.1f}%" if r['trades'] > 0 else "N/A"
                pf_str = f"{r['pf']:.2f}" if r['pf'] > 0 else "N/A"

                print(f"{days}일{'':<6} {r['return']:>9.2f}% {r['trades']:>8} "
                      f"{win_rate_str:>8} {r['mdd']:>7.2f}% {pf_str:>8}")

    # 안정성 분석
    print("\n" + "=" * 80)
    print("안정성 분석 (기간별 수익률 일관성)")
    print("=" * 80)

    for strategy_name in strategies.keys():
        returns = []
        for days in periods:
            if days in all_results and strategy_name in all_results[days]:
                returns.append(all_results[days][strategy_name]['return'])

        if len(returns) >= 2:
            import numpy as np
            avg_return = np.mean(returns)
            std_return = np.std(returns)

            # 모든 기간에서 플러스인지 확인
            all_positive = all(r > 0 for r in returns)

            print(f"\n[{strategy_name}]")
            print(f"  평균 수익률: {avg_return:+.2f}%")
            print(f"  수익률 표준편차: {std_return:.2f}%")
            print(f"  모든 기간 플러스: {'YES' if all_positive else 'NO'}")

            if std_return < 1.0 and all_positive:
                print(f"  평가: [매우 안정적] ★★★")
            elif std_return < 2.0 and all_positive:
                print(f"  평가: [안정적] ★★")
            elif all_positive:
                print(f"  평가: [보통] ★")
            else:
                print(f"  평가: [불안정]")

    # 최종 추천
    print("\n" + "=" * 80)
    print("최종 분석")
    print("=" * 80)

    # 90일 기준으로 최고 성과 찾기
    if 90 in all_results:
        best_strategy = max(all_results[90].items(), key=lambda x: x[1]['return'])
        best_name = best_strategy[0]
        best_result = best_strategy[1]

        print(f"\n[90일 기준 최고 성과]: {best_name}")
        print(f"  수익률: {best_result['return']:+.2f}%")
        print(f"  거래수: {best_result['trades']}건")
        print(f"  승률: {best_result['win_rate']:.1f}%")

        # 샘플 충분한지 체크
        if best_result['trades'] >= 20:
            print(f"\n[GOOD] 거래 샘플 충분 ({best_result['trades']}건 >= 20건)")
            print(f"  통계적으로 신뢰 가능")
        elif best_result['trades'] >= 10:
            print(f"\n[OK] 거래 샘플 적당 ({best_result['trades']}건)")
            print(f"  어느 정도 신뢰 가능")
        else:
            print(f"\n[WARNING] 거래 샘플 부족 ({best_result['trades']}건 < 10건)")
            print(f"  통계적 신뢰도 낮음")

        # 모든 기간에서 플러스인지 확인
        all_positive = all(
            all_results[days][best_name]['return'] > 0
            for days in periods
            if days in all_results and best_name in all_results[days]
        )

        if all_positive:
            print(f"\n[EXCELLENT] 모든 기간(30/60/90일)에서 플러스 수익!")
            print(f"  전략의 안정성이 검증되었습니다.")
            print(f"\n추천: {best_name} 설정을 실전에 적용해도 좋습니다.")
        else:
            print(f"\n[CAUTION] 일부 기간에서 마이너스")
            print(f"  시장 상황에 따라 성과가 달라질 수 있습니다.")
            print(f"\n추천: 실전 테스트넷에서 1주일 더 관찰 후 결정")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_long_term()
