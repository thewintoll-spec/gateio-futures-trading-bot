"""
Gate.io Futures Trading Bot - Main Entry Point
"""
import time
import config
from exchange import GateioFutures
from strategy import RSIStrategy


class TradingBot:
    def __init__(self):
        """Initialize trading bot"""
        self.exchange = GateioFutures(testnet=config.TESTNET)
        self.strategy = RSIStrategy(
            period=config.RSI_PERIOD,
            oversold=config.RSI_OVERSOLD,
            overbought=config.RSI_OVERBOUGHT
        )
        self.symbol = config.SYMBOL
        self.leverage = config.LEVERAGE
        self.order_size = config.ORDER_SIZE
        self.in_position = False
        self.current_side = None

        print("=" * 50)
        print("Gate.io Futures Trading Bot Started")
        print(f"Environment: {'TESTNET' if config.TESTNET else 'MAINNET'}")
        print("=" * 50)

    def setup(self):
        """Setup trading environment"""
        print(f"\n[Setup] Setting leverage to {self.leverage}x...")
        self.exchange.set_leverage(self.symbol, self.leverage)

        print(f"[Setup] Checking account balance...")
        balance = self.exchange.get_account_balance()
        if balance:
            print(f"[Balance] Available: {balance['available']} USDT")
        else:
            print("[Error] Failed to get account balance")
            return False

        print(f"[Setup] Trading pair: {self.symbol}")
        print(f"[Setup] Order size: {self.order_size}")
        print(f"[Setup] Strategy: RSI ({config.RSI_PERIOD})")
        print(f"[Setup] RSI Oversold: {config.RSI_OVERSOLD}")
        print(f"[Setup] RSI Overbought: {config.RSI_OVERBOUGHT}")

        return True

    def check_position(self):
        """Check current position status"""
        position = self.exchange.get_position(self.symbol)
        if position and position['size'] != 0:
            self.in_position = True
            self.current_side = 'long' if position['size'] > 0 else 'short'
            print(f"\n[Position] {self.current_side.upper()} | Size: {abs(position['size'])} | "
                  f"Entry: {position['entry_price']:.2f} | "
                  f"PnL: {position['unrealised_pnl']:.4f} USDT")
            return position
        else:
            self.in_position = False
            self.current_side = None
            return None

    def execute_trade(self, signal):
        """Execute trade based on signal"""
        if signal == self.current_side:
            print(f"[Trade] Already in {signal} position, skipping...")
            return

        # Close existing position if any
        if self.in_position:
            print(f"[Trade] Closing {self.current_side} position...")
            self.exchange.close_position(self.symbol)
            time.sleep(2)  # Wait for position to close

        # Open new position
        print(f"[Trade] Opening {signal.upper()} position...")

        # Calculate contract size
        # For Gate.io, size is in number of contracts
        # 1 BTC contract = 0.0001 BTC typically
        contract_size = int(self.order_size * 10000)  # Convert to contracts

        result = self.exchange.place_order(
            symbol=self.symbol,
            side=signal,
            size=contract_size,
            order_type='market'
        )

        if result:
            print(f"[Trade] {signal.upper()} order executed successfully!")
            self.in_position = True
            self.current_side = signal
        else:
            print(f"[Trade] Failed to execute {signal} order")

    def run(self):
        """Main trading loop"""
        if not self.setup():
            print("[Error] Setup failed. Exiting...")
            return

        print("\n" + "=" * 50)
        print("Bot is running... Press Ctrl+C to stop")
        print("=" * 50)

        try:
            while True:
                print(f"\n{'=' * 50}")
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]")

                # Get current price
                price = self.exchange.get_current_price(self.symbol)
                if price:
                    print(f"[Price] {self.symbol}: ${price:.2f}")

                # Check current position
                self.check_position()

                # Get market data
                candles = self.exchange.get_candlesticks(
                    self.symbol,
                    interval='5m',  # 5-minute candles
                    limit=100
                )

                if not candles:
                    print("[Warning] Failed to get candlestick data")
                    time.sleep(60)
                    continue

                # Analyze and get signal
                signal = self.strategy.analyze(candles)

                if signal:
                    print(f"\n[Signal] {signal.upper()} signal detected!")
                    self.execute_trade(signal)
                else:
                    print("[Signal] No trading signal")

                # Wait before next iteration
                print(f"\nWaiting 60 seconds...")
                time.sleep(60)

        except KeyboardInterrupt:
            print("\n\n[Stop] Bot stopped by user")
            print("[Info] Current positions will remain open")
            print("[Info] Use exchange.close_position() to close manually if needed")

        except Exception as e:
            print(f"\n[Error] Unexpected error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
