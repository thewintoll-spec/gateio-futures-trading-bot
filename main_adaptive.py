"""
Gate.io Futures Trading Bot - Adaptive Multi-Regime Strategy
자동으로 시장 상황에 맞는 전략 선택

자본 관리 로직:
- 포지션 0개: 첫 신호에 50% 자본 사용
- 포지션 1개: 두번째 신호에 95% 사용 가능 자본 사용
- 포지션 2개: 대기 (포지션 청산 시까지)
"""
import time
from datetime import datetime
import config
from exchange import GateioFutures
from adaptive_strategy import AdaptiveStrategy
from adaptive_strategy_v2 import AdaptiveStrategyV2
from trade_logger import TradeLogger


class AdaptiveTradingBot:
    def __init__(self):
        """Initialize adaptive trading bot"""
        self.exchange = GateioFutures(testnet=config.TESTNET)

        # Symbols to trade
        self.symbols = ['BTC_USDT', 'ETH_USDT']

        # V1 Adaptive Strategy for both symbols
        self.strategies = {}
        for symbol in self.symbols:
            self.strategies[symbol] = AdaptiveStrategy(
                adx_threshold=25,
                allow_short_in_downtrend=True
            )

        self.leverage = 7  # 행운의 7배 (방송용)

        # Position tracking
        self.positions = {}
        self.position_entry_time = {}

        # Trade logger
        self.logger = TradeLogger()

        print("=" * 60)
        print("Gate.io Adaptive Strategy Trading Bot")
        print("Strategy: V1 Adaptive (ADX 25+)")
        print(f"Leverage: {self.leverage}x")
        print(f"Symbols: {', '.join(self.symbols)}")
        print(f"Environment: {'TESTNET' if config.TESTNET else 'MAINNET'}")
        print("=" * 60)

    def setup(self):
        """Setup trading environment"""
        print(f"\n[Setup] Setting leverage to {self.leverage}x for all symbols...")
        for symbol in self.symbols:
            self.exchange.set_leverage(symbol, self.leverage)

        print(f"[Setup] Checking account balance...")
        balance = self.exchange.get_account_balance()
        if balance:
            print(f"[Balance] Available: {balance['available']} USDT")
            print(f"[Balance] Total: {balance['total']} USDT")
        else:
            print("[Error] Failed to get account balance")
            return False

        print(f"\n[Setup] Trading Configuration:")
        print(f"  - Strategy: V1 Adaptive (Auto Grid/Trend)")
        print(f"  - ADX threshold: 25+")
        print(f"  - Symbols: {', '.join(self.symbols)}")
        print(f"  - Leverage: {self.leverage}x")
        print(f"  - Capital Allocation:")
        print(f"    * 0 positions: 50% of available USDT")
        print(f"    * 1 position: 95% of available USDT")
        print(f"    * 2 positions: Wait for exit")

        return True

    def check_positions(self):
        """Check current positions for all symbols"""
        self.positions = {}

        for symbol in self.symbols:
            position = self.exchange.get_position(symbol)
            if position and position['size'] != 0:
                side = 'long' if position['size'] > 0 else 'short'
                margin = position.get('margin', 0)

                pnl = position['unrealised_pnl']
                pnl_percent = (pnl / margin * 100) if margin > 0 else 0

                self.positions[symbol] = {
                    'side': side,
                    'margin': margin,
                    'entry_price': position['entry_price'],
                    'size': abs(position['size']),
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'tp': position.get('tp', 3.0),
                    'sl': position.get('sl', 2.0)
                }

                print(f"\n[Position] {symbol} | {side.upper()}")
                print(f"  Size: {abs(position['size'])} | Entry: {position['entry_price']:.2f}")
                print(f"  Margin: {margin:.2f} USDT")
                print(f"  PnL: {pnl:.4f} USDT ({pnl_percent:+.2f}%)")

    def check_stop_loss_take_profit(self, symbol, position_info):
        """Check if stop loss or take profit is hit"""
        if not position_info:
            return False

        pnl_percent = position_info['pnl_percent']
        tp = position_info.get('tp', 3.0)
        sl = position_info.get('sl', 2.0)

        reason = None

        # Check stop loss
        if pnl_percent <= -sl:
            print(f"\n[{symbol}] Stop Loss hit! PnL: {pnl_percent:.2f}% (Target: -{sl}%)")
            print(f"[{symbol}] Closing position...")
            reason = 'stop_loss'

        # Check take profit
        elif pnl_percent >= tp:
            print(f"\n[{symbol}] Take Profit hit! PnL: {pnl_percent:.2f}% (Target: +{tp}%)")
            print(f"[{symbol}] Closing position...")
            reason = 'take_profit'

        if reason:
            # Close position
            self.exchange.close_position(symbol)

            # Calculate holding time
            holding_time = 'N/A'
            if symbol in self.position_entry_time:
                entry_time = self.position_entry_time[symbol]
                holding_seconds = (datetime.now() - entry_time).total_seconds()
                hours = int(holding_seconds // 3600)
                minutes = int((holding_seconds % 3600) // 60)
                holding_time = f"{hours:02d}:{minutes:02d}:00"

            # Log exit
            self.logger.log_exit(
                symbol=symbol,
                reason=reason,
                position_data={
                    'side': position_info['side'],
                    'entry_price': position_info['entry_price'],
                    'exit_price': self.exchange.get_current_price(symbol),
                    'size': position_info['size'],
                    'holding_time': holding_time,
                },
                pnl_data={
                    'pnl_usdt': position_info['pnl'],
                    'pnl_percent': pnl_percent,
                    'roi': pnl_percent * self.leverage,
                }
            )

            # Remove from tracking
            if symbol in self.positions:
                del self.positions[symbol]
            if symbol in self.position_entry_time:
                del self.position_entry_time[symbol]

            time.sleep(2)
            return True

        return False

    def calculate_capital_allocation(self):
        """
        Calculate capital allocation based on current positions

        Returns:
            float: Percentage of available capital to use (0.5 or 0.95)
        """
        num_positions = len(self.positions)

        if num_positions == 0:
            # No positions: Use 50% of available
            return 0.50
        elif num_positions == 1:
            # One position: Use 95% of available
            return 0.95
        else:
            # Two positions: No new trades
            return 0.0

    def calculate_order_size(self, symbol, capital_pct):
        """Calculate order size for a symbol"""
        try:
            balance = self.exchange.get_account_balance()
            if not balance:
                print(f"[{symbol}] Warning: Could not get balance")
                return 1

            available_usdt = float(balance['available'])

            if capital_pct == 0:
                print(f"[{symbol}] Max positions reached, skipping")
                return 0

            price = self.exchange.get_current_price(symbol)
            if not price or price == 0:
                print(f"[{symbol}] Warning: Could not get price")
                return 1

            # Calculate USDT to use
            usdt_to_use = available_usdt * capital_pct

            # Calculate quantity with leverage
            asset = symbol.split('_')[0]

            if asset == 'BTC':
                contract_multiplier = 0.0001  # 1 contract = 0.0001 BTC
            else:  # ETH
                contract_multiplier = 0.01    # 1 contract = 0.01 ETH

            quantity_in_asset = (usdt_to_use * self.leverage) / price
            contract_size = int(quantity_in_asset / contract_multiplier)

            print(f"[{symbol}] Capital allocation: {capital_pct*100:.0f}% "
                  f"({usdt_to_use:.2f} USDT)")
            print(f"[{symbol}] Calculated size: {contract_size} contracts "
                  f"(~{quantity_in_asset:.6f} {asset})")

            return max(1, contract_size)

        except Exception as e:
            print(f"[{symbol}] Error calculating order size: {e}")
            return 1

    def execute_trade(self, symbol, signal, capital_pct):
        """Execute trade for a symbol"""
        if capital_pct == 0:
            print(f"[{symbol}] Max positions reached, cannot open new position")
            return

        # Parse signal
        if isinstance(signal, dict):
            side = signal['signal']
            tp = signal.get('take_profit', 3.0)
            sl = signal.get('stop_loss', 2.0)
            regime = signal.get('regime', 'unknown')
            print(f"\n[{symbol}] Signal: {side.upper()} | Regime: {regime} | TP: {tp}% | SL: {sl}%")
        else:
            side = signal
            tp = 3.0
            sl = 2.0
            regime = 'unknown'

        # Check if already in this position
        if symbol in self.positions:
            if self.positions[symbol]['side'] == side:
                print(f"[{symbol}] Already in {side} position, skipping")
                return
            else:
                # Close opposite position
                print(f"[{symbol}] Closing {self.positions[symbol]['side']} position...")
                self.exchange.close_position(symbol)
                time.sleep(2)

        # Calculate order size
        contract_size = self.calculate_order_size(symbol, capital_pct)
        if contract_size == 0:
            return

        # Execute order
        print(f"[{symbol}] Opening {side.upper()} position...")
        result = self.exchange.place_order(
            symbol=symbol,
            side=side,
            size=contract_size,
            order_type='market'
        )

        if result:
            print(f"[{symbol}] {side.upper()} order executed successfully!")

            # Record entry time
            self.position_entry_time[symbol] = datetime.now()

            # Get current price for logging
            current_price = self.exchange.get_current_price(symbol)

            # Get balance for margin calculation
            balance = self.exchange.get_account_balance()
            usdt_to_use = float(balance['available']) * capital_pct if balance else 0

            # Log entry
            self.logger.log_entry(
                symbol=symbol,
                signal_info={
                    'signal': side,
                    'regime': regime,
                    'take_profit': tp,
                    'stop_loss': sl,
                },
                market_data={
                    'price': current_price,
                    'size': contract_size,
                    'margin': usdt_to_use,
                    'leverage': self.leverage,
                }
            )
        else:
            print(f"[{symbol}] Failed to execute order")

    def run(self):
        """Main trading loop"""
        if not self.setup():
            print("[Error] Setup failed. Exiting...")
            return

        print("\n" + "=" * 60)
        print("Bot is running... Press Ctrl+C to stop")
        print("=" * 60)

        try:
            while True:
                print(f"\n{'=' * 60}")
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]")

                # Check all positions
                self.check_positions()

                # Check TP/SL for existing positions
                positions_to_check = list(self.positions.keys())
                for symbol in positions_to_check:
                    if symbol in self.positions:
                        self.check_stop_loss_take_profit(symbol, self.positions[symbol])

                # Determine capital allocation
                capital_pct = self.calculate_capital_allocation()

                num_positions = len(self.positions)
                print(f"\n[Status] Active positions: {num_positions}/2")
                print(f"[Status] Next trade capital: {capital_pct*100:.0f}% of available USDT")

                if capital_pct == 0:
                    print("[Status] Max positions reached. Waiting for exit signals...")
                    time.sleep(30)
                    continue

                # Check signals for each symbol
                signals = {}
                for symbol in self.symbols:
                    # Skip if already have position in this symbol
                    if symbol in self.positions:
                        print(f"\n[{symbol}] Already in position, skipping signal check")
                        continue

                    # Get current price
                    price = self.exchange.get_current_price(symbol)
                    if price:
                        print(f"\n[{symbol}] Price: ${price:.2f}")

                    # Get candles
                    candles = self.exchange.get_candlesticks(
                        symbol,
                        interval='5m',
                        limit=100
                    )

                    if not candles:
                        print(f"[{symbol}] Warning: Failed to get candlestick data")
                        continue

                    # Get signal from adaptive strategy
                    signal = self.strategies[symbol].analyze(candles)

                    if signal:
                        signals[symbol] = signal
                        print(f"\n[{symbol}] Signal detected!")

                # Execute first signal if any
                if signals:
                    # Take first available signal
                    first_symbol = list(signals.keys())[0]
                    first_signal = signals[first_symbol]

                    print(f"\n[Trade] Executing {first_symbol}...")
                    self.execute_trade(first_symbol, first_signal, capital_pct)
                else:
                    print("\n[Signal] No trading signals from any symbol")

                # Wait before next iteration
                print(f"\nWaiting 30 seconds...")
                time.sleep(30)

        except KeyboardInterrupt:
            print("\n\n[Stop] Bot stopped by user")
            print("[Info] Current positions will remain open")

            if self.positions:
                print("\n[Active Positions]")
                for symbol, pos in self.positions.items():
                    print(f"  - {symbol}: {pos['side'].upper()} "
                          f"(PnL: {pos['pnl_percent']:+.2f}%)")

        except Exception as e:
            print(f"\n[Error] Unexpected error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    bot = AdaptiveTradingBot()
    bot.run()
