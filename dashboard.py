# -*- coding: utf-8 -*-
"""
Gate.io 선물 트레이딩 봇 - 실시간 대시보드
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

        # 거래소
        self.exchange = GateioFutures(testnet=config.TESTNET)
        self.symbols = ['BTC_USDT', 'ETH_USDT']

        # 데이터
        self.balance_data = {}
        self.positions_data = {}
        self.prices = {}

        self.setup_ui()
        # tkinter의 after 메서드로 업데이트 루프 시작
        self.root.after(1000, self.update_loop)

    def setup_ui(self):
        """UI 컴포넌트 설정"""
        # 제목
        title = tk.Label(
            self.root,
            text="🤖 Gate.io Futures Bot",
            font=('Arial', 24, 'bold'),
            bg='#1e1e1e',
            fg='#00ff00'
        )
        title.pack(pady=20)

        # 잔고 프레임
        balance_frame = tk.Frame(self.root, bg='#2d2d2d', relief=tk.RAISED, borderwidth=2)
        balance_frame.pack(pady=10, padx=20, fill=tk.X)

        tk.Label(
            balance_frame,
            text="💰 계좌 잔고",
            font=('Arial', 16, 'bold'),
            bg='#2d2d2d',
            fg='#ffffff'
        ).pack(pady=5)

        self.balance_label = tk.Label(
            balance_frame,
            text="로딩 중...",
            font=('Arial', 14),
            bg='#2d2d2d',
            fg='#00ff00'
        )
        self.balance_label.pack(pady=5)

        self.available_label = tk.Label(
            balance_frame,
            text="사용 가능: 로딩 중...",
            font=('Arial', 12),
            bg='#2d2d2d',
            fg='#ffffff'
        )
        self.available_label.pack(pady=2)

        # 포지션 프레임
        positions_frame = tk.Frame(self.root, bg='#2d2d2d', relief=tk.RAISED, borderwidth=2)
        positions_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)

        tk.Label(
            positions_frame,
            text="📊 활성 포지션",
            font=('Arial', 16, 'bold'),
            bg='#2d2d2d',
            fg='#ffffff'
        ).pack(pady=5)

        # 포지션 목록
        self.positions_frame_inner = tk.Frame(positions_frame, bg='#2d2d2d')
        self.positions_frame_inner.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # 상태 바
        self.status_label = tk.Label(
            self.root,
            text="마지막 업데이트: N/A",
            font=('Arial', 10),
            bg='#1e1e1e',
            fg='#888888'
        )
        self.status_label.pack(side=tk.BOTTOM, pady=5)

    def update_balance(self):
        """잔고 표시 업데이트"""
        try:
            balance = self.exchange.get_account_balance()

            if balance:
                self.balance_data = balance

                total = float(balance['total'])
                available = float(balance['available'])

                self.balance_label.config(
                    text=f"총액: {total:.2f} USDT",
                    fg='#00ff00' if total > 1000 else '#ffaa00'
                )

                self.available_label.config(
                    text=f"사용 가능: {available:.2f} USDT | 사용 중: {total - available:.2f} USDT"
                )
            else:
                self.balance_label.config(text="오류: 잔고 데이터 없음", fg='#ff4444')
        except Exception as e:
            self.balance_label.config(text=f"오류: {str(e)}", fg='#ff4444')

    def update_positions(self):
        """포지션 표시 업데이트"""
        try:
            # 이전 포지션 제거
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

                    # 포지션 카드 생성
                    card = tk.Frame(
                        self.positions_frame_inner,
                        bg='#3d3d3d',
                        relief=tk.RAISED,
                        borderwidth=1
                    )
                    card.pack(pady=5, padx=5, fill=tk.X)

                    side = '롱' if position['size'] > 0 else '숏'
                    side_color = '#00ff00' if side == '롱' else '#ff4444'

                    pnl = position['unrealised_pnl']
                    margin = position.get('margin', 0)
                    pnl_percent = (pnl / margin * 100) if margin > 0 else 0
                    pnl_color = '#00ff00' if pnl > 0 else '#ff4444'

                    # 심볼, 방향, 레버리지
                    leverage = position.get('leverage', '?')  # API에서 실제 레버리지 사용
                    header = tk.Label(
                        card,
                        text=f"{symbol.replace('_', '/')} | {side} | {leverage}배",
                        font=('Arial', 14, 'bold'),
                        bg='#3d3d3d',
                        fg=side_color
                    )
                    header.pack(anchor=tk.W, padx=10, pady=5)

                    # 진입가
                    entry = tk.Label(
                        card,
                        text=f"진입: ${position['entry_price']:.2f} | 현재: ${price:.2f}",
                        font=('Arial', 11),
                        bg='#3d3d3d',
                        fg='#ffffff'
                    )
                    entry.pack(anchor=tk.W, padx=10)

                    # 사이즈 및 마진
                    # 계약 사이즈를 실제 코인 수량으로 변환
                    asset = symbol.split('_')[0]
                    contract_size = abs(position['size'])

                    if asset == 'BTC':
                        # BTC: 1 계약 = 0.0001 BTC
                        coin_amount = contract_size * 0.0001
                        size_display = f"{coin_amount:g} BTC"
                    elif asset == 'ETH':
                        # ETH: 1 계약 = 0.01 ETH
                        coin_amount = contract_size * 0.01
                        size_display = f"{coin_amount:g} ETH"
                    else:
                        size_display = f"{contract_size}"

                    size_info = tk.Label(
                        card,
                        text=f"수량: {size_display} ({contract_size} 계약) | 마진: {margin:.2f} USDT",
                        font=('Arial', 11),
                        bg='#3d3d3d',
                        fg='#cccccc'
                    )
                    size_info.pack(anchor=tk.W, padx=10)

                    # 손익
                    pnl_label = tk.Label(
                        card,
                        text=f"손익: {pnl:+.4f} USDT ({pnl_percent:+.2f}%)",
                        font=('Arial', 12, 'bold'),
                        bg='#3d3d3d',
                        fg=pnl_color
                    )
                    pnl_label.pack(anchor=tk.W, padx=10, pady=5)

            # 포지션이 없을 경우
            if active_positions == 0:
                no_pos = tk.Label(
                    self.positions_frame_inner,
                    text="활성 포지션 없음",
                    font=('Arial', 12),
                    bg='#2d2d2d',
                    fg='#888888'
                )
                no_pos.pack(pady=20)

        except Exception as e:
            print(f"포지션 업데이트 오류: {e}")

    def update_loop(self):
        """tkinter after를 사용한 업데이트 루프"""
        try:
            self.update_balance()
            self.update_positions()

            # 상태 업데이트
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.status_label.config(text=f"마지막 업데이트: {current_time}")

        except Exception as e:
            print(f"업데이트 루프 오류: {e}")

        # 5초 후 다음 업데이트 예약
        self.root.after(5000, self.update_loop)

    def run(self):
        """대시보드 실행"""
        self.root.mainloop()


if __name__ == "__main__":
    print("트레이딩 대시보드 시작 중...")
    dashboard = TradingDashboard()
    dashboard.run()
