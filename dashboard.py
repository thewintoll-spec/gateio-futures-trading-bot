# -*- coding: utf-8 -*-
"""
Gate.io Futures Trading Bot - Live Dashboard
방송용 실시간 포지션 및 잔액 표시
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import config
from exchange import GateioFutures


class TradingDashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gate.io Futures Bot - Live Dashboard")
        self.root.geometry("800x600")
        self.root.configure(bg='#1e1e1e')

        # Exchange
        self.exchange = GateioFutures(testnet=config.TESTNET)
        self.symbols = ['BTC_USDT', 'ETH_USDT']

        # Data
        self.balance_data = {}
        self.positions_data = {}
        self.prices = {}

        self.setup_ui()
        # Start update loop using tkinter's after method
        self.root.after(1000, self.update_loop)

    def setup_ui(self):
        """Setup UI components"""
        # Title
        title = tk.Label(
            self.root,
            text="🤖 Gate.io Futures Bot",
            font=('Arial', 24, 'bold'),
            bg='#1e1e1e',
            fg='#00ff00'
        )
        title.pack(pady=20)

        # Balance Frame
        balance_frame = tk.Frame(self.root, bg='#2d2d2d', relief=tk.RAISED, borderwidth=2)
        balance_frame.pack(pady=10, padx=20, fill=tk.X)

        tk.Label(
            balance_frame,
            text="💰 Account Balance",
            font=('Arial', 16, 'bold'),
            bg='#2d2d2d',
            fg='#ffffff'
        ).pack(pady=5)

        self.balance_label = tk.Label(
            balance_frame,
            text="Loading...",
            font=('Arial', 14),
            bg='#2d2d2d',
            fg='#00ff00'
        )
        self.balance_label.pack(pady=5)

        self.available_label = tk.Label(
            balance_frame,
            text="Available: Loading...",
            font=('Arial', 12),
            bg='#2d2d2d',
            fg='#ffffff'
        )
        self.available_label.pack(pady=2)

        # Positions Frame
        positions_frame = tk.Frame(self.root, bg='#2d2d2d', relief=tk.RAISED, borderwidth=2)
        positions_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)

        tk.Label(
            positions_frame,
            text="📊 Active Positions",
            font=('Arial', 16, 'bold'),
            bg='#2d2d2d',
            fg='#ffffff'
        ).pack(pady=5)

        # Positions list
        self.positions_frame_inner = tk.Frame(positions_frame, bg='#2d2d2d')
        self.positions_frame_inner.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Status bar
        self.status_label = tk.Label(
            self.root,
            text="Last Update: N/A",
            font=('Arial', 10),
            bg='#1e1e1e',
            fg='#888888'
        )
        self.status_label.pack(side=tk.BOTTOM, pady=5)

    def update_balance(self):
        """Update balance display"""
        try:
            balance = self.exchange.get_account_balance()

            if balance:
                self.balance_data = balance

                total = float(balance['total'])
                available = float(balance['available'])

                self.balance_label.config(
                    text=f"Total: {total:.2f} USDT",
                    fg='#00ff00' if total > 1000 else '#ffaa00'
                )

                self.available_label.config(
                    text=f"Available: {available:.2f} USDT | In Use: {total - available:.2f} USDT"
                )
            else:
                self.balance_label.config(text="Error: No balance data", fg='#ff4444')
        except Exception as e:
            self.balance_label.config(text=f"Error: {str(e)}", fg='#ff4444')

    def update_positions(self):
        """Update positions display"""
        try:
            # Clear previous positions
            for widget in self.positions_frame_inner.winfo_children():
                widget.destroy()

            self.positions_data = {}
            active_positions = 0

            for symbol in self.symbols:
                position = self.exchange.get_position(symbol)
                price = self.exchange.get_current_price(symbol)

                if price:
                    self.prices[symbol] = price

                if position and position['size'] != 0:
                    active_positions += 1
                    self.positions_data[symbol] = position

                    # Create position card
                    card = tk.Frame(
                        self.positions_frame_inner,
                        bg='#3d3d3d',
                        relief=tk.RAISED,
                        borderwidth=1
                    )
                    card.pack(pady=5, padx=5, fill=tk.X)

                    side = 'LONG' if position['size'] > 0 else 'SHORT'
                    side_color = '#00ff00' if side == 'LONG' else '#ff4444'

                    pnl = position['unrealised_pnl']
                    margin = position.get('margin', 0)
                    pnl_percent = (pnl / margin * 100) if margin > 0 else 0
                    pnl_color = '#00ff00' if pnl > 0 else '#ff4444'

                    # Symbol, Side, and Leverage
                    leverage = position.get('leverage', '?')  # Use actual leverage from API
                    header = tk.Label(
                        card,
                        text=f"{symbol.replace('_', '/')} | {side} | {leverage}x",
                        font=('Arial', 14, 'bold'),
                        bg='#3d3d3d',
                        fg=side_color
                    )
                    header.pack(anchor=tk.W, padx=10, pady=5)

                    # Entry Price
                    entry = tk.Label(
                        card,
                        text=f"Entry: ${position['entry_price']:.2f} | Current: ${price:.2f}",
                        font=('Arial', 11),
                        bg='#3d3d3d',
                        fg='#ffffff'
                    )
                    entry.pack(anchor=tk.W, padx=10)

                    # Size and Margin
                    # Convert contract size to actual coin amount
                    asset = symbol.split('_')[0]
                    contract_size = abs(position['size'])

                    if asset == 'BTC':
                        # BTC: 1 contract = 0.0001 BTC
                        coin_amount = contract_size * 0.0001
                        size_display = f"{coin_amount:g} BTC"
                    elif asset == 'ETH':
                        # ETH: 1 contract = 0.01 ETH
                        coin_amount = contract_size * 0.01
                        size_display = f"{coin_amount:g} ETH"
                    else:
                        size_display = f"{contract_size}"

                    size_info = tk.Label(
                        card,
                        text=f"Size: {size_display} ({contract_size} contracts) | Margin: {margin:.2f} USDT",
                        font=('Arial', 11),
                        bg='#3d3d3d',
                        fg='#cccccc'
                    )
                    size_info.pack(anchor=tk.W, padx=10)

                    # PnL
                    pnl_label = tk.Label(
                        card,
                        text=f"PnL: {pnl:+.4f} USDT ({pnl_percent:+.2f}%)",
                        font=('Arial', 12, 'bold'),
                        bg='#3d3d3d',
                        fg=pnl_color
                    )
                    pnl_label.pack(anchor=tk.W, padx=10, pady=5)

            # If no positions
            if active_positions == 0:
                no_pos = tk.Label(
                    self.positions_frame_inner,
                    text="No active positions",
                    font=('Arial', 12),
                    bg='#2d2d2d',
                    fg='#888888'
                )
                no_pos.pack(pady=20)

        except Exception as e:
            print(f"Error updating positions: {e}")

    def update_loop(self):
        """Update loop using tkinter after"""
        try:
            self.update_balance()
            self.update_positions()

            # Update status
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.status_label.config(text=f"Last Update: {current_time}")

        except Exception as e:
            print(f"Error in update loop: {e}")

        # Schedule next update after 5 seconds
        self.root.after(5000, self.update_loop)

    def run(self):
        """Run the dashboard"""
        self.root.mainloop()


if __name__ == "__main__":
    print("Starting Trading Dashboard...")
    dashboard = TradingDashboard()
    dashboard.run()
