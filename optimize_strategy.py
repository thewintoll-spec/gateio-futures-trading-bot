"""
전략 파라미터 최적화 시스템
Grid Search로 최적 조합 찾기
"""
from backtest.data_loader import DataLoader
from backtest.backtest import BacktestEngine
from scalping_strategy import (
    ScalpingRSIStrategy,
    VolumeBreakoutStrategy,
    EMAScalpingStrategy,
    MomentumScalpingStrategy,
    StochasticScalpingStrategy
)
import config
import itertools
from datetime import datetime


def optimize_risk_params(strategy, strategy_name, data, leverage_options,
                        stop_loss_options, take_profit_options, capital_pct_options):
    """
    리스크 관리 파라미터 최적화

    Args:
        strategy: 전략 인스턴스
        strategy_name: 전략 이름
        data: 가격 데이터
        leverage_options: 레버리지 옵션들
        stop_loss_options: 손절 옵션들
        take_profit_options: 익절 옵션들
        capital_pct_options: 자본 사용 비율 옵션들
    """
    print(f"\n{'='*80}")
    print(f"최적화: {strategy_name}")
    print(f"{'='*80}")

    results = []
    total_combinations = (len(leverage_options) * len(stop_loss_options) *
                         len(take_profit_options) * len(capital_pct_options))

    print(f"테스트할 조합 수: {total_combinations}")

    counter = 0
    for leverage, stop_loss, take_profit, capital_pct in itertools.product(
        leverage_options, stop_loss_options, take_profit_options, capital_pct_options
    ):
        counter += 1

        # 손익비 체크 (익절이 손절보다 커야 함)
        if take_profit <= stop_loss:
            continue

        # 백테스트 실행
        engine = BacktestEngine(
            initial_capital=10000,
            leverage=leverage,
            maker_fee=0.0002,
            taker_fee=0.0005
        )

        # 손절/익절 래핑
        original_check = engine._check_stop_loss_take_profit
        def wrapped_check(price, time):
            return original_check(price, time, stop_loss_pct=stop_loss, take_profit_pct=take_profit)
        engine._check_stop_loss_take_profit = wrapped_check

        try:
            result = engine.run(data, strategy, capital_pct=capital_pct)

            # 결과 저장
            if result['total_trades'] > 0:  # 거래가 있는 경우만
                results.append({
                    'leverage': leverage,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'capital_pct': capital_pct,
                    'profit_ratio': take_profit / stop_loss,
                    'total_return': result['total_return'],
                    'total_trades': result['total_trades'],
                    'win_rate': result.get('win_rate', 0),
                    'max_drawdown': result.get('max_drawdown', 0),
                    'avg_win': result.get('avg_win', 0),
                    'avg_loss': result.get('avg_loss', 0),
                    'total_fees': result.get('total_fees', 0),
                    'sharpe_ratio': calculate_sharpe(result)
                })

            if counter % 10 == 0:
                print(f"진행: {counter}/{total_combinations} ({counter/total_combinations*100:.1f}%)")

        except Exception as e:
            print(f"에러 발생 (Lev:{leverage}, SL:{stop_loss}, TP:{take_profit}): {e}")
            continue

    return results


def calculate_sharpe(result):
    """샤프 비율 계산 (간이 버전)"""
    if result['total_trades'] == 0:
        return 0

    total_return = result['total_return']
    max_dd = abs(result.get('max_drawdown', 0))

    if max_dd == 0:
        return 0

    # 간단히: 수익률 / 낙폭
    sharpe = total_return / max_dd if max_dd > 0 else 0
    return sharpe


def optimize_strategy_params(strategy_class, strategy_name, data, param_grid):
    """
    전략 고유 파라미터 최적화

    Args:
        strategy_class: 전략 클래스
        strategy_name: 전략 이름
        data: 가격 데이터
        param_grid: 파라미터 그리드
    """
    print(f"\n{'='*80}")
    print(f"전략 파라미터 최적화: {strategy_name}")
    print(f"{'='*80}")

    results = []

    # 파라미터 조합 생성
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())

    total_combinations = 1
    for values in param_values:
        total_combinations *= len(values)

    print(f"테스트할 조합 수: {total_combinations}")

    counter = 0
    for param_combo in itertools.product(*param_values):
        counter += 1

        # 파라미터 딕셔너리 생성
        params = dict(zip(param_names, param_combo))

        # 전략 인스턴스 생성
        try:
            strategy = strategy_class(**params)
        except Exception as e:
            print(f"전략 생성 실패: {params} - {e}")
            continue

        # 고정된 리스크 파라미터로 백테스트
        engine = BacktestEngine(
            initial_capital=10000,
            leverage=10,
            maker_fee=0.0002,
            taker_fee=0.0005
        )

        original_check = engine._check_stop_loss_take_profit
        def wrapped_check(price, time):
            return original_check(price, time, stop_loss_pct=2.0, take_profit_pct=3.0)
        engine._check_stop_loss_take_profit = wrapped_check

        try:
            result = engine.run(data, strategy, capital_pct=0.8)

            if result['total_trades'] > 0:
                results.append({
                    'params': params,
                    'total_return': result['total_return'],
                    'total_trades': result['total_trades'],
                    'win_rate': result.get('win_rate', 0),
                    'max_drawdown': result.get('max_drawdown', 0),
                    'sharpe_ratio': calculate_sharpe(result)
                })

            if counter % 10 == 0:
                print(f"진행: {counter}/{total_combinations} ({counter/total_combinations*100:.1f}%)")

        except Exception as e:
            print(f"백테스트 실패: {params} - {e}")
            continue

    return results


def print_top_results(results, top_n=10, sort_by='total_return'):
    """상위 결과 출력"""
    if not results:
        print("결과 없음!")
        return

    # 정렬
    sorted_results = sorted(results, key=lambda x: x[sort_by], reverse=True)

    print(f"\n{'='*100}")
    print(f"TOP {top_n} 결과 (정렬 기준: {sort_by})")
    print(f"{'='*100}")

    # 헤더
    if 'leverage' in sorted_results[0]:
        # 리스크 파라미터 최적화 결과
        print(f"{'순위':<5} {'레버리지':<8} {'손절%':<8} {'익절%':<8} {'자본%':<8} "
              f"{'손익비':<8} {'수익률%':<10} {'거래수':<8} {'승률%':<8} {'MDD%':<10} {'샤프':<8}")
        print("-" * 100)

        for i, r in enumerate(sorted_results[:top_n], 1):
            print(f"{i:<5} {r['leverage']:<8} {r['stop_loss']:<8.1f} {r['take_profit']:<8.1f} "
                  f"{r['capital_pct']:<8.1f} {r['profit_ratio']:<8.2f} "
                  f"{r['total_return']:<10.2f} {r['total_trades']:<8} "
                  f"{r['win_rate']:<8.1f} {r['max_drawdown']:<10.2f} {r['sharpe_ratio']:<8.2f}")
    else:
        # 전략 파라미터 최적화 결과
        print(f"{'순위':<5} {'파라미터':<40} {'수익률%':<10} {'거래수':<8} "
              f"{'승률%':<8} {'MDD%':<10} {'샤프':<8}")
        print("-" * 100)

        for i, r in enumerate(sorted_results[:top_n], 1):
            params_str = str(r['params'])[:38]
            print(f"{i:<5} {params_str:<40} {r['total_return']:<10.2f} "
                  f"{r['total_trades']:<8} {r['win_rate']:<8.1f} "
                  f"{r['max_drawdown']:<10.2f} {r['sharpe_ratio']:<8.2f}")

    print("=" * 100)


def main():
    """메인 최적화 실행"""
    print("=" * 80)
    print("Gate.io Futures 전략 최적화 시스템")
    print("=" * 80)

    # 데이터 로드
    print("\n데이터 로딩...")
    loader = DataLoader(config.SYMBOL, testnet=config.TESTNET)
    df = loader.fetch_historical_data(interval='5m', days=30)  # 30일로 변경

    if df is None or len(df) == 0:
        print("데이터 로드 실패!")
        return

    print(f"데이터 로드 완료: {len(df)} 캔들")

    # ========================================
    # 1. 리스크 파라미터 최적화
    # ========================================
    print("\n\n[PHASE 1] 리스크 관리 파라미터 최적화")

    # 테스트할 파라미터 범위
    leverage_options = [5, 10, 15, 20]
    stop_loss_options = [1.0, 1.5, 2.0, 2.5, 3.0]
    take_profit_options = [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
    capital_pct_options = [0.6, 0.8, 1.0]

    # Scalping RSI (7) - 현재 최고 성능
    strategy = ScalpingRSIStrategy(period=7, oversold=35, overbought=65)
    risk_results = optimize_risk_params(
        strategy,
        "Scalping RSI (7)",
        df,
        leverage_options,
        stop_loss_options,
        take_profit_options,
        capital_pct_options
    )

    print(f"\n총 {len(risk_results)}개 유효한 조합 발견")

    # 상위 결과 출력
    print_top_results(risk_results, top_n=15, sort_by='total_return')
    print_top_results(risk_results, top_n=10, sort_by='sharpe_ratio')

    # ========================================
    # 2. 전략 파라미터 최적화
    # ========================================
    print("\n\n[PHASE 2] 전략 고유 파라미터 최적화")

    # RSI 전략 파라미터 그리드
    rsi_param_grid = {
        'period': [5, 7, 9, 11, 14],
        'oversold': [25, 30, 35, 40],
        'overbought': [60, 65, 70, 75]
    }

    rsi_strategy_results = optimize_strategy_params(
        ScalpingRSIStrategy,
        "Scalping RSI",
        df,
        rsi_param_grid
    )

    print(f"\n총 {len(rsi_strategy_results)}개 유효한 조합 발견")
    print_top_results(rsi_strategy_results, top_n=10, sort_by='total_return')

    # EMA Cross 전략 파라미터 그리드
    print("\n" + "="*80)
    ema_param_grid = {
        'fast_period': [5, 8, 10, 13],
        'slow_period': [15, 20, 21, 25, 30]
    }

    ema_strategy_results = optimize_strategy_params(
        EMAScalpingStrategy,
        "EMA Cross",
        df,
        ema_param_grid
    )

    print(f"\n총 {len(ema_strategy_results)}개 유효한 조합 발견")
    print_top_results(ema_strategy_results, top_n=10, sort_by='total_return')

    # ========================================
    # 3. 최종 최적 조합
    # ========================================
    print("\n\n" + "="*80)
    print("최종 추천")
    print("="*80)

    if risk_results:
        best_risk = max(risk_results, key=lambda x: x['sharpe_ratio'])
        print("\n[최적 리스크 파라미터]")
        print(f"레버리지: {best_risk['leverage']}배")
        print(f"손절: {best_risk['stop_loss']}%")
        print(f"익절: {best_risk['take_profit']}%")
        print(f"자본 사용: {best_risk['capital_pct']*100:.0f}%")
        print(f"예상 수익률: {best_risk['total_return']:.2f}%")
        print(f"샤프 비율: {best_risk['sharpe_ratio']:.2f}")

    if rsi_strategy_results:
        best_rsi = max(rsi_strategy_results, key=lambda x: x['sharpe_ratio'])
        print("\n[최적 RSI 파라미터]")
        print(f"파라미터: {best_rsi['params']}")
        print(f"수익률: {best_rsi['total_return']:.2f}%")
        print(f"샤프 비율: {best_rsi['sharpe_ratio']:.2f}")


if __name__ == "__main__":
    main()
