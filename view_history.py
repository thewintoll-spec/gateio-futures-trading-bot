"""
거래 내역 확인 스크립트
"""
from exchange import GateioFutures
import config
from datetime import datetime


def format_time(timestamp):
    """Unix timestamp를 읽기 쉬운 형식으로"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def main():
    exchange = GateioFutures(testnet=config.TESTNET)

    print("=" * 100)
    print("거래 내역 확인")
    print("=" * 100)

    # 1. 계좌 정보
    balance = exchange.get_account_balance()
    if balance:
        print(f"\n[계좌 정보]")
        print(f"  총 자본: {float(balance['total']):.2f} USDT")
        print(f"  사용 가능: {float(balance['available']):.2f} USDT")

        # 초기 자본 1000 USDT 기준
        initial = 1000
        current = float(balance['total'])
        pnl = current - initial
        pnl_pct = (pnl / initial) * 100
        print(f"  총 손익: {pnl:+.2f} USDT ({pnl_pct:+.2f}%)")

    # 2. 현재 포지션
    position = exchange.get_position(config.SYMBOL)
    if position and position.get('size', 0) != 0:
        print(f"\n[현재 포지션]")
        print(f"  {position['size'] > 0 and 'LONG' or 'SHORT'} {abs(position['size'])} contracts")
        print(f"  진입가: {position['entry_price']:.2f}")
        print(f"  미실현 PnL: {position['unrealised_pnl']:+.4f} USDT")
    else:
        print(f"\n[현재 포지션] 없음")

    # 3. 청산된 포지션 내역
    print(f"\n[청산된 포지션 내역]")
    positions = exchange.get_position_history(limit=50)  # 50개로 증가

    if positions:
        print(f"\n총 {len(positions)}개:")
        print(f"{'번호':<4} {'시간':<20} {'방향':<6} {'PnL':>12}")
        print("-" * 100)

        total_pnl = 0
        wins = 0
        losses = 0
        long_count = 0
        short_count = 0
        long_pnl = 0
        short_pnl = 0

        for i, pos in enumerate(positions, 1):
            time_str = format_time(pos['time'])
            pnl = pos['pnl']
            total_pnl += pnl

            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1

            if pos['side'] == 'long':
                long_count += 1
                long_pnl += pnl
            else:
                short_count += 1
                short_pnl += pnl

            print(f"{i:<4} {time_str:<20} {pos['side']:<6} {pnl:>+12.4f}")

        print("-" * 100)
        print(f"\n[통계]")
        print(f"  총 거래: {len(positions)}개 (승: {wins}, 패: {losses})")
        if len(positions) > 0:
            win_rate = wins / len(positions) * 100
            print(f"  승률: {win_rate:.1f}%")
        print(f"  총 PnL: {total_pnl:+.4f} USDT")

        print(f"\n  롱 거래: {long_count}개, PnL: {long_pnl:+.4f} USDT")
        print(f"  숏 거래: {short_count}개, PnL: {short_pnl:+.4f} USDT")

    else:
        print("  내역 없음")

    # 4. 최근 주문 내역
    print(f"\n[최근 주문 내역]")
    orders = exchange.get_order_history(limit=10)

    if orders:
        print(f"\n총 {len(orders)}개:")
        print(f"{'ID':<15} {'시간':<20} {'방향':<6} {'크기':>8} {'상태':<10}")
        print("-" * 100)

        for order in orders[:10]:
            time_str = format_time(order['create_time'])
            print(f"{order['id']:<15} {time_str:<20} {order['side']:<6} "
                  f"{abs(order['size']):>8} {order['status']:<10}")
    else:
        print("  내역 없음")

    # 5. 최근 체결 내역 (API 에러로 주석 처리)
    # print(f"\n[최근 체결 내역]")
    # trades = exchange.get_trade_history(limit=10)

    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
