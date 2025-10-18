"""
실시간 거래 성과 확인
"""
from exchange import GateioFutures
import config
import pandas as pd
from datetime import datetime, timedelta


def check_recent_trades():
    """최근 거래 내역 확인"""

    exchange = GateioFutures(testnet=config.TESTNET)

    print("=" * 80)
    print("최근 거래 성과 확인")
    print("=" * 80)

    # 계좌 잔고
    balance = exchange.get_account_balance()
    if balance:
        print(f"\n[현재 계좌]")
        print(f"  총 자본: {float(balance['total']):.2f} USDT")
        print(f"  사용 가능: {float(balance['available']):.2f} USDT")
        print(f"  포지션 마진: {float(balance.get('position_margin', 0)):.2f} USDT")
        print(f"  주문 마진: {float(balance.get('order_margin', 0)):.2f} USDT")

    # 현재 포지션
    position = exchange.get_position(config.SYMBOL)
    if position and position.get('size', 0) != 0:
        print(f"\n[현재 포지션]")
        print(f"  방향: {'LONG' if position['size'] > 0 else 'SHORT'}")
        print(f"  크기: {abs(position['size'])} contracts")
        print(f"  진입가: {position['entry_price']:.2f}")
        print(f"  마진: {position.get('margin', 0):.2f} USDT")
        pnl = position.get('unrealised_pnl', 0)
        print(f"  미실현 PnL: {pnl:+.4f} USDT")
    else:
        print(f"\n[현재 포지션] 없음")

    # 거래 내역
    print(f"\n[최근 거래 내역]")

    # Gate.io API로 최근 거래 가져오기
    try:
        from gate_api import ApiClient, Configuration, FuturesApi

        config_obj = Configuration(host="https://fx-api-testnet.gateio.ws/api/v4")
        config_obj.key = config.API_KEY
        config_obj.secret = config.API_SECRET

        api_client = ApiClient(config_obj)
        futures_api = FuturesApi(api_client)

        # 결제된 포지션 내역
        settle = 'usdt'
        trades = futures_api.list_position_close(
            settle=settle,
            limit=10  # 최근 10개
        )

        if trades:
            print(f"\n청산된 포지션 {len(trades)}개:")
            print(f"{'번호':<4} {'시간':<20} {'방향':<6} {'진입가':<10} {'청산가':<10} {'PnL':>12} {'수익률%':>10}")
            print("-" * 80)

            total_pnl = 0
            wins = 0
            losses = 0

            for i, trade in enumerate(trades[:10], 1):
                side = trade.side
                pnl = float(trade.pnl)
                total_pnl += pnl

                if pnl > 0:
                    wins += 1
                elif pnl < 0:
                    losses += 1

                # 시간 변환
                time_str = datetime.fromtimestamp(trade.time).strftime('%Y-%m-%d %H:%M:%S')

                # 수익률 계산 (마진 기준)
                margin = abs(float(trade.entry_price) * float(trade.size) * 0.01 / config.LEVERAGE)
                pnl_pct = (pnl / margin * 100) if margin > 0 else 0

                print(f"{i:<4} {time_str:<20} {side:<6} {float(trade.entry_price):<10.2f} "
                      f"{float(trade.close_price):<10.2f} {pnl:>+12.4f} {pnl_pct:>+9.2f}%")

            print("-" * 80)
            print(f"\n[통계]")
            print(f"  총 거래: {len(trades)}개")
            print(f"  승: {wins}개 | 패: {losses}개")
            if len(trades) > 0:
                win_rate = wins / len(trades) * 100
                print(f"  승률: {win_rate:.1f}%")
            print(f"  총 PnL: {total_pnl:+.4f} USDT")

            # 초기 자본 대비 수익률 (10000 USDT 기준)
            if balance:
                initial = 10000
                current = float(balance['total'])
                total_return = (current - initial) / initial * 100
                print(f"  총 수익률: {total_return:+.2f}% (초기 {initial} USDT 기준)")
        else:
            print("  거래 내역 없음")

    except Exception as e:
        print(f"  거래 내역 조회 실패: {e}")
        print(f"  수동으로 확인: https://testnet.gateio.io")


if __name__ == "__main__":
    check_recent_trades()
