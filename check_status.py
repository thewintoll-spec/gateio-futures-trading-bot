"""현재 Gate.io 계정 상태 확인"""
from exchange import GateioFutures
import config

ex = GateioFutures(testnet=config.TESTNET)

print("=" * 60)
print("Gate.io 계정 상태")
print("=" * 60)

# 잔액 확인
bal = ex.get_account_balance()
if bal:
    print(f"\n[잔액]")
    print(f"  Total: {bal['total']} USDT")
    print(f"  Available: {bal['available']} USDT")
else:
    print("\n[잔액] 조회 실패")

# 포지션 확인
print(f"\n[포지션]")
for symbol in ['BTC_USDT', 'ETH_USDT']:
    pos = ex.get_position(symbol)
    if pos and pos['size'] != 0:
        side = 'LONG' if pos['size'] > 0 else 'SHORT'
        print(f"  {symbol}: {side} (size: {pos['size']})")
    else:
        print(f"  {symbol}: 포지션 없음")

print("=" * 60)
