"""
Check actual PnL from Gate.io API
"""
import config
from exchange import GateioFutures
from datetime import datetime

def check_real_pnl():
    """Check real PnL from API"""
    exchange = GateioFutures(testnet=config.TESTNET)

    print("=" * 80)
    print("Gate.io Testnet - Actual Trading Results")
    print("=" * 80)

    # Get account balance
    print("\n[Account Balance]")
    balance = exchange.get_account_balance()
    if balance:
        print(f"Total: {balance['total']} USDT")
        print(f"Available: {balance['available']} USDT")
        print(f"Position Margin: {balance['position_margin']} USDT")

    # Get position history (closed positions)
    print("\n" + "=" * 80)
    print("[Closed Position History]")
    print("=" * 80)

    history = exchange.get_position_history(limit=50)

    if history:
        total_pnl = 0
        eth_pnl = 0
        btc_pnl = 0
        eth_count = 0
        btc_count = 0

        print(f"\n{'Time':<20} {'Symbol':<12} {'Side':<6} {'PnL (USDT)':>15}")
        print("-" * 80)

        for pos in history:
            time_str = datetime.fromtimestamp(pos['time']).strftime('%Y-%m-%d %H:%M:%S')
            symbol = pos['contract']
            side = pos['side']
            pnl = pos['pnl']

            total_pnl += pnl

            if 'ETH' in symbol:
                eth_pnl += pnl
                eth_count += 1
            elif 'BTC' in symbol:
                btc_pnl += pnl
                btc_count += 1

            status = "[+]" if pnl > 0 else "[-]"
            print(f"{time_str:<20} {symbol:<12} {side:<6} {status} {pnl:>12.4f}")

        print("-" * 80)
        print(f"\n[Summary]")
        print(f"Total Trades: {len(history)}")
        print(f"Total PnL: {total_pnl:.4f} USDT")
        print(f"\n[By Symbol]")
        print(f"ETH: {eth_count} trades, PnL: {eth_pnl:.4f} USDT")
        print(f"BTC: {btc_count} trades, PnL: {btc_pnl:.4f} USDT")

        # Win rate
        wins = sum(1 for pos in history if pos['pnl'] > 0)
        losses = sum(1 for pos in history if pos['pnl'] < 0)
        win_rate = (wins / len(history) * 100) if len(history) > 0 else 0

        print(f"\n[Performance]")
        print(f"Wins: {wins} | Losses: {losses}")
        print(f"Win Rate: {win_rate:.1f}%")

        if wins > 0 and losses > 0:
            avg_win = sum(pos['pnl'] for pos in history if pos['pnl'] > 0) / wins
            avg_loss = sum(pos['pnl'] for pos in history if pos['pnl'] < 0) / losses
            profit_factor = abs(avg_win * wins / (avg_loss * losses))

            print(f"Average Win: {avg_win:.4f} USDT")
            print(f"Average Loss: {avg_loss:.4f} USDT")
            print(f"Profit Factor: {profit_factor:.2f}")

    else:
        print("No position history found")

    # Get current open positions
    print("\n" + "=" * 80)
    print("[Current Open Positions]")
    print("=" * 80)

    for symbol in ['BTC_USDT', 'ETH_USDT']:
        pos = exchange.get_position(symbol)
        if pos and pos['size'] != 0:
            side = 'LONG' if pos['size'] > 0 else 'SHORT'
            pnl_pct = (pos['unrealised_pnl'] / pos['margin'] * 100) if pos['margin'] > 0 else 0

            print(f"\n{symbol}:")
            print(f"  Side: {side}")
            print(f"  Size: {abs(pos['size'])} contracts")
            print(f"  Entry Price: {pos['entry_price']:.2f}")
            print(f"  Unrealized PnL: {pos['unrealised_pnl']:.4f} USDT ({pnl_pct:+.2f}%)")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_real_pnl()
