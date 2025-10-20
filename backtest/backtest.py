"""
Backtest Engine for Trading Strategies
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime


class BacktestEngine:
    """백테스트 엔진"""

    def __init__(self, initial_capital=10000, leverage=10, maker_fee=0.0002, taker_fee=0.0005):
        """
        Initialize backtest engine

        Args:
            initial_capital: 초기 자금 (USDT)
            leverage: 레버리지
            maker_fee: Maker 수수료 (0.02%)
            taker_fee: Taker 수수료 (0.05%)
        """
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee

        # Trading state
        self.capital = initial_capital
        self.position = None  # {'side': 'long/short', 'entry_price': float, 'size': float, 'margin': float}
        self.trades = []  # List of completed trades
        self.equity_curve = []  # Track capital over time

    def run(self, df, strategy, capital_pct=0.8, allow_reversal=False):
        """
        Run backtest on historical data

        Args:
            df: DataFrame with OHLCV data
            strategy: Strategy instance with analyze() method
            capital_pct: Percentage of capital to use per trade (0.8 = 80%)
            allow_reversal: Allow position reversal (default False)

        Returns:
            dict with backtest results
        """
        print(f"Starting backtest with {len(df)} candles...")
        print(f"Initial capital: {self.initial_capital} USDT")
        print(f"Leverage: {self.leverage}x")
        print(f"Capital usage: {capital_pct * 100}%")
        print(f"Position reversal: {'Enabled' if allow_reversal else 'Disabled (TP/SL only)'}")

        for i in range(len(df)):
            row = df.iloc[i]
            current_time = row['datetime']
            current_price = row['close']

            # Get historical data up to current point
            hist_data = df.iloc[max(0, i-100):i+1]
            candles = hist_data[['timestamp', 'open', 'high', 'low', 'close', 'volume']].to_dict('records')

            # Analyze with strategy
            signal = strategy.analyze(candles) if len(candles) > strategy.period else None

            # Execute signal
            if signal and not self.position:
                # Open new position
                self._open_position(signal, current_price, current_time, capital_pct)

            elif signal and self.position and allow_reversal:
                # Get signal side (handle both string and dict)
                signal_side = signal if isinstance(signal, str) else signal.get('signal')
                if signal_side != self.position['side']:
                    # Close and reverse (only if allowed)
                    self._close_position(current_price, current_time, reason='reverse')
                    self._open_position(signal, current_price, current_time, capital_pct)

            # Check TP/SL (always check if position exists)
            if self.position:
                tp = self.position.get('take_profit', 5.0)
                sl = self.position.get('stop_loss', 1.5)
                self._check_stop_loss_take_profit(current_price, current_time,
                                                   stop_loss_pct=sl, take_profit_pct=tp)

            # Track equity
            equity = self._calculate_equity(current_price)
            self.equity_curve.append({
                'datetime': current_time,
                'equity': equity,
                'price': current_price
            })

        # Close any remaining position
        if self.position:
            final_price = df.iloc[-1]['close']
            final_time = df.iloc[-1]['datetime']
            self._close_position(final_price, final_time, reason='backtest_end')

        return self._generate_results()

    def _open_position(self, signal_data, price, time, capital_pct):
        """Open a new position

        Args:
            signal_data: Can be string ('long'/'short') or dict with 'signal', 'take_profit', 'stop_loss'
        """
        # Handle both old (string) and new (dict) signal format
        if isinstance(signal_data, str):
            side = signal_data
            take_profit = 5.0
            stop_loss = 1.5
        elif isinstance(signal_data, dict):
            side = signal_data['signal']
            take_profit = signal_data.get('take_profit', 5.0)
            stop_loss = signal_data.get('stop_loss', 1.5)
        else:
            return

        # Calculate position size
        usdt_to_use = self.capital * capital_pct
        margin = usdt_to_use / self.leverage
        position_value = usdt_to_use
        size = position_value / price  # Size in base asset (ETH)

        # Pay entry fee (taker)
        entry_fee = position_value * self.taker_fee
        self.capital -= entry_fee

        self.position = {
            'side': side,
            'entry_price': price,
            'entry_time': time,
            'size': size,
            'margin': margin,
            'entry_fee': entry_fee,
            'position_value': position_value,
            'take_profit': take_profit,
            'stop_loss': stop_loss
        }

    def _close_position(self, price, time, reason='signal'):
        """Close current position"""
        if not self.position:
            return

        side = self.position['side']
        entry_price = self.position['entry_price']
        size = self.position['size']
        position_value = self.position['position_value']

        # Calculate PnL
        if side == 'long':
            pnl = (price - entry_price) * size
        else:  # short
            pnl = (entry_price - price) * size

        # Pay exit fee (taker)
        exit_value = size * price
        exit_fee = exit_value * self.taker_fee
        self.capital -= exit_fee

        # Update capital
        net_pnl = pnl - self.position['entry_fee'] - exit_fee
        self.capital += net_pnl

        # Record trade
        trade = {
            'entry_time': self.position['entry_time'],
            'exit_time': time,
            'side': side,
            'entry_price': entry_price,
            'exit_price': price,
            'size': size,
            'pnl': net_pnl,
            'pnl_percent': (net_pnl / self.position['margin']) * 100,
            'fees': self.position['entry_fee'] + exit_fee,
            'reason': reason
        }
        self.trades.append(trade)

        self.position = None

    def _check_stop_loss_take_profit(self, current_price, current_time, stop_loss_pct=3.0, take_profit_pct=5.0):
        """Check if stop loss or take profit is hit"""
        if not self.position:
            return

        side = self.position['side']
        entry_price = self.position['entry_price']
        size = self.position['size']

        # Calculate current PnL
        if side == 'long':
            pnl = (current_price - entry_price) * size
        else:
            pnl = (entry_price - current_price) * size

        pnl_percent = (pnl / self.position['margin']) * 100

        # Check stop loss
        if pnl_percent <= -stop_loss_pct:
            self._close_position(current_price, current_time, reason='stop_loss')
            return

        # Check take profit
        if pnl_percent >= take_profit_pct:
            self._close_position(current_price, current_time, reason='take_profit')
            return

    def _calculate_equity(self, current_price):
        """Calculate current total equity"""
        equity = self.capital

        if self.position:
            side = self.position['side']
            entry_price = self.position['entry_price']
            size = self.position['size']

            # Add unrealized PnL
            if side == 'long':
                pnl = (current_price - entry_price) * size
            else:
                pnl = (entry_price - current_price) * size

            equity += pnl

        return equity

    def _generate_results(self):
        """Generate backtest results summary"""
        df_trades = pd.DataFrame(self.trades) if self.trades else pd.DataFrame()
        df_equity = pd.DataFrame(self.equity_curve)

        results = {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_return': ((self.capital - self.initial_capital) / self.initial_capital) * 100,
            'total_trades': len(self.trades),
            'trades': df_trades,
            'equity_curve': df_equity
        }

        if len(self.trades) > 0:
            winning_trades = df_trades[df_trades['pnl'] > 0]
            losing_trades = df_trades[df_trades['pnl'] <= 0]

            results.update({
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': (len(winning_trades) / len(self.trades)) * 100,
                'avg_win': winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0,
                'avg_loss': losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0,
                'largest_win': df_trades['pnl'].max(),
                'largest_loss': df_trades['pnl'].min(),
                'avg_trade_pnl': df_trades['pnl'].mean(),
                'total_fees': df_trades['fees'].sum()
            })

            # Calculate max drawdown
            equity_series = df_equity['equity']
            running_max = equity_series.cummax()
            drawdown = (equity_series - running_max) / running_max * 100
            results['max_drawdown'] = drawdown.min()

        return results


if __name__ == "__main__":
    print("Backtest engine ready")
