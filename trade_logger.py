"""
Trade Decision Logger

진입/청산 근거를 로그로 저장:
- 어떤 신호로 진입했는지
- 어떤 이유로 청산했는지
- 당시 시장 상황
"""
import json
import os
from datetime import datetime


class TradeLogger:
    def __init__(self, log_dir='logs'):
        """Initialize trade logger"""
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 날짜별 로그 파일
        today = datetime.now().strftime('%Y-%m-%d')
        self.log_file = os.path.join(log_dir, f'trades_{today}.jsonl')

    def log_entry(self, symbol, signal_info, market_data):
        """
        Log trade entry

        Args:
            symbol: 거래 심볼 (BTC_USDT, ETH_USDT)
            signal_info: 신호 정보 dict
            market_data: 시장 데이터 dict
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': 'ENTRY',
            'symbol': symbol,
            'side': signal_info.get('signal'),
            'entry_price': market_data.get('price'),
            'signal': {
                'type': 'grid',
                'grid_level': signal_info.get('grid_level'),
                'take_profit': signal_info.get('take_profit'),
                'stop_loss': signal_info.get('stop_loss'),
            },
            'market': {
                'price': market_data.get('price'),
                'atr': market_data.get('atr'),
                'trend': market_data.get('trend'),
                'volatility': market_data.get('volatility'),
            },
            'position_info': {
                'size': market_data.get('size'),
                'margin': market_data.get('margin'),
                'leverage': market_data.get('leverage'),
            }
        }

        self._write_log(log_entry)
        self._print_log(log_entry)

    def log_exit(self, symbol, reason, position_data, pnl_data):
        """
        Log trade exit

        Args:
            symbol: 거래 심볼
            reason: 청산 이유 ('take_profit', 'stop_loss', 'signal_reversal')
            position_data: 포지션 데이터 dict
            pnl_data: 수익 데이터 dict
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': 'EXIT',
            'symbol': symbol,
            'side': position_data.get('side'),
            'exit_price': position_data.get('exit_price'),
            'reason': reason,
            'pnl': {
                'usdt': pnl_data.get('pnl_usdt'),
                'percent': pnl_data.get('pnl_percent'),
                'roi': pnl_data.get('roi'),
            },
            'position_summary': {
                'entry_price': position_data.get('entry_price'),
                'exit_price': position_data.get('exit_price'),
                'holding_time': position_data.get('holding_time'),
                'size': position_data.get('size'),
            }
        }

        self._write_log(log_entry)
        self._print_log(log_entry)

    def log_signal_skip(self, symbol, reason, signal_info):
        """
        Log skipped signal

        Args:
            symbol: 거래 심볼
            reason: 스킵 이유
            signal_info: 신호 정보
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': 'SKIP',
            'symbol': symbol,
            'reason': reason,
            'signal': signal_info,
        }

        self._write_log(log_entry)
        # 스킵은 콘솔 출력 안 함 (너무 많아짐)

    def _write_log(self, log_entry):
        """Write log entry to file"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def _print_log(self, log_entry):
        """Print log entry to console"""
        action = log_entry['action']
        symbol = log_entry['symbol']
        timestamp = datetime.fromisoformat(log_entry['timestamp']).strftime('%H:%M:%S')

        if action == 'ENTRY':
            side = log_entry['side'].upper()
            price = log_entry['entry_price']
            tp = log_entry['signal']['take_profit']
            sl = log_entry['signal']['stop_loss']
            trend = log_entry['market'].get('trend', 'N/A')

            print(f"\n{'='*60}")
            print(f"[{timestamp}] 📝 ENTRY LOG - {symbol}")
            print(f"{'='*60}")
            print(f"  방향: {side}")
            print(f"  진입가: {price:.2f}")
            print(f"  목표: TP {tp:.2f}% | SL {sl:.2f}%")
            print(f"  시장: Trend {trend}")
            print(f"{'='*60}")

        elif action == 'EXIT':
            side = log_entry['side'].upper()
            reason = log_entry['reason']
            pnl_usdt = log_entry['pnl']['usdt']
            pnl_pct = log_entry['pnl']['percent']
            entry = log_entry['position_summary']['entry_price']
            exit_price = log_entry['position_summary']['exit_price']

            reason_kr = {
                'take_profit': 'TP 도달',
                'stop_loss': 'SL 손절',
                'signal_reversal': '반전 신호'
            }.get(reason, reason)

            print(f"\n{'='*60}")
            print(f"[{timestamp}] 📝 EXIT LOG - {symbol}")
            print(f"{'='*60}")
            print(f"  방향: {side}")
            print(f"  이유: {reason_kr}")
            print(f"  진입: {entry:.2f} → 청산: {exit_price:.2f}")
            print(f"  수익: {pnl_usdt:+.2f} USDT ({pnl_pct:+.2f}%)")
            print(f"{'='*60}")


def get_trade_history_from_api(exchange, symbol):
    """
    API에서 거래 내역 조회 (심볼별)

    Args:
        exchange: GateioFutures 인스턴스
        symbol: 조회할 심볼

    Returns:
        list: 거래 내역
    """
    try:
        # Gate.io API로 거래 내역 조회
        trades = exchange.get_my_trades(symbol, limit=100)
        return trades
    except Exception as e:
        print(f"[Error] Failed to get trade history for {symbol}: {e}")
        return []


def get_position_history_from_api(exchange, symbol):
    """
    API에서 포지션 히스토리 조회 (심볼별)

    Args:
        exchange: GateioFutures 인스턴스
        symbol: 조회할 심볼

    Returns:
        list: 포지션 히스토리
    """
    try:
        # Gate.io API로 포지션 히스토리 조회
        positions = exchange.get_position_history(symbol, limit=100)
        return positions
    except Exception as e:
        print(f"[Error] Failed to get position history for {symbol}: {e}")
        return []


def analyze_symbol_performance(log_dir='logs', symbol=None):
    """
    로그 파일 분석: 심볼별 성과 분석

    Args:
        log_dir: 로그 디렉토리
        symbol: 특정 심볼만 분석 (None이면 전체)
    """
    import glob

    log_files = glob.glob(os.path.join(log_dir, 'trades_*.jsonl'))

    if not log_files:
        print("No log files found")
        return

    # 심볼별 통계
    stats = {}

    for log_file in log_files:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                entry = json.loads(line)

                sym = entry['symbol']
                if symbol and sym != symbol:
                    continue

                if sym not in stats:
                    stats[sym] = {
                        'entries': 0,
                        'exits': 0,
                        'total_pnl': 0,
                        'wins': 0,
                        'losses': 0,
                        'tp_exits': 0,
                        'sl_exits': 0,
                    }

                if entry['action'] == 'ENTRY':
                    stats[sym]['entries'] += 1

                elif entry['action'] == 'EXIT':
                    stats[sym]['exits'] += 1
                    pnl = entry['pnl']['usdt']
                    stats[sym]['total_pnl'] += pnl

                    if pnl > 0:
                        stats[sym]['wins'] += 1
                    else:
                        stats[sym]['losses'] += 1

                    if entry['reason'] == 'take_profit':
                        stats[sym]['tp_exits'] += 1
                    elif entry['reason'] == 'stop_loss':
                        stats[sym]['sl_exits'] += 1

    # 결과 출력
    print("\n" + "="*80)
    print("심볼별 성과 분석 (로그 기반)")
    print("="*80)

    for sym, data in stats.items():
        print(f"\n[{sym}]")
        print(f"  진입: {data['entries']}회")
        print(f"  청산: {data['exits']}회")
        print(f"  총 수익: {data['total_pnl']:+.2f} USDT")

        if data['exits'] > 0:
            win_rate = data['wins'] / data['exits'] * 100
            avg_pnl = data['total_pnl'] / data['exits']
            print(f"  승률: {win_rate:.1f}%")
            print(f"  평균 수익: {avg_pnl:+.2f} USDT")
            print(f"  TP: {data['tp_exits']}회 | SL: {data['sl_exits']}회")

    print("\n" + "="*80)


if __name__ == "__main__":
    # 테스트
    logger = TradeLogger()

    # 진입 로그 예시
    logger.log_entry(
        symbol='BTC_USDT',
        signal_info={
            'signal': 'long',
            'grid_level': 5,
            'take_profit': 0.5,
            'stop_loss': 1.5,
        },
        market_data={
            'price': 45000,
            'atr': 2.5,
            'trend': 'neutral',
            'volatility': 0.8,
            'size': 100,
            'margin': 500,
            'leverage': 2,
        }
    )

    # 청산 로그 예시
    logger.log_exit(
        symbol='BTC_USDT',
        reason='take_profit',
        position_data={
            'side': 'long',
            'entry_price': 45000,
            'exit_price': 45225,
            'size': 100,
            'holding_time': '00:15:30',
        },
        pnl_data={
            'pnl_usdt': 10.5,
            'pnl_percent': 0.5,
            'roi': 2.1,
        }
    )

    # 분석
    analyze_symbol_performance()
