"""
Gate.io 선물 거래소 API 래퍼
"""
import gate_api
from gate_api.exceptions import ApiException, GateApiException
import config


class GateioFutures:
    def __init__(self, testnet=False):
        """Gate.io 선물 API 클라이언트 초기화"""
        # 환경에 따라 호스트 설정
        if testnet:
            host = "https://api-testnet.gateapi.io/api/v4"
        else:
            host = "https://api.gateio.ws/api/v4"

        configuration = gate_api.Configuration(host=host)
        configuration.key = config.API_KEY
        configuration.secret = config.API_SECRET

        # API 클라이언트 및 선물 API 인스턴스 생성
        api_client = gate_api.ApiClient(configuration)
        self.futures_api = gate_api.FuturesApi(api_client)
        self.settle = 'usdt'  # USDT 정산 선물
        self.testnet = testnet

    def get_account_balance(self):
        """계좌 잔고 조회"""
        try:
            account = self.futures_api.list_futures_accounts(self.settle)
            return {
                'total': account.total,
                'available': account.available,
                'position_margin': account.position_margin,
                'order_margin': account.order_margin
            }
        except GateApiException as e:
            print(f"잔고 조회 오류: {e}")
            return None

    def get_current_price(self, symbol):
        """심볼의 현재가 조회"""
        try:
            contract = symbol  # 언더스코어 유지: ETH_USDT
            tickers = self.futures_api.list_futures_tickers(self.settle, contract=contract)
            if tickers:
                return float(tickers[0].last)
            return None
        except GateApiException as e:
            print(f"가격 조회 오류: {e}")
            return None

    def get_position(self, symbol):
        """심볼의 현재 포지션 조회"""
        try:
            contract = symbol
            # list_positions는 모든 포지션 반환, 계약으로 필터링
            positions = self.futures_api.list_positions(self.settle)
            # 특정 계약만 필터링
            positions = [p for p in positions if p.contract == contract]
            if positions:
                pos = positions[0]
                return {
                    'size': int(pos.size),
                    'entry_price': float(pos.entry_price) if pos.entry_price else 0,
                    'leverage': int(pos.leverage),
                    'margin': float(pos.margin) if pos.margin else 0,
                    'unrealised_pnl': float(pos.unrealised_pnl) if pos.unrealised_pnl else 0,
                    'pnl_pnl': float(pos.pnl_pnl) if pos.pnl_pnl else 0,
                    'pnl_fee': float(pos.pnl_fee) if pos.pnl_fee else 0,
                    'pnl_fund': float(pos.pnl_fund) if pos.pnl_fund else 0,
                    'realised_pnl': float(pos.realised_pnl) if pos.realised_pnl else 0
                }
            return None
        except GateApiException as e:
            print(f"포지션 조회 오류: {e}")
            return None

    def set_leverage(self, symbol, leverage):
        """심볼의 레버리지 설정"""
        try:
            contract = symbol
            self.futures_api.update_position_leverage(
                self.settle,
                contract,
                str(leverage)
            )
            print(f"{symbol} 레버리지 {leverage}배 설정 완료")
            return True
        except GateApiException as e:
            print(f"레버리지 설정 오류: {e}")
            return False

    def place_order(self, symbol, side, size, price=None, order_type='market'):
        """
        주문 실행

        Args:
            symbol: 거래쌍 (예: 'BTC_USDT')
            side: 'long' 또는 'short'
            size: 주문 크기 (계약 수)
            price: 지정가 (지정가 주문 시)
            order_type: 'market' 또는 'limit'
        """
        try:
            contract = symbol

            # 주문 준비
            order = gate_api.FuturesOrder(
                contract=contract,
                size=size if side == 'long' else -size,  # 숏은 음수
                tif='ioc' if order_type == 'market' else 'gtc',
                price=str(price) if price else '0'
            )

            result = self.futures_api.create_futures_order(self.settle, order)
            print(f"주문 실행: {side} {abs(size)} 계약 ({order_type})")
            return result

        except GateApiException as e:
            print(f"주문 실행 오류: {e}")
            return None

    def close_position(self, symbol):
        """심볼의 모든 포지션 청산"""
        try:
            position = self.get_position(symbol)
            if position and position['size'] != 0:
                size = position['size']
                side = 'short' if size > 0 else 'long'  # 반대 방향으로 청산
                self.place_order(symbol, side, abs(size), order_type='market')
                print(f"{symbol} 포지션 청산 완료")
                return True
            else:
                print(f"{symbol}에 열린 포지션 없음")
                return False
        except Exception as e:
            print(f"포지션 청산 오류: {e}")
            return False

    def get_candlesticks(self, symbol, interval='1m', limit=100):
        """
        캔들스틱 데이터 조회

        Args:
            symbol: 거래쌍
            interval: 시간프레임 (1m, 5m, 15m, 1h, 4h, 1d)
            limit: 캔들 개수
        """
        try:
            contract = symbol
            candles = self.futures_api.list_futures_candlesticks(
                self.settle,
                contract=contract,
                interval=interval,
                limit=limit
            )

            return [{
                'timestamp': c.t,
                'open': float(c.o),
                'high': float(c.h),
                'low': float(c.l),
                'close': float(c.c),
                'volume': float(c.v)
            } for c in candles]

        except GateApiException as e:
            print(f"캔들스틱 조회 오류: {e}")
            return None

    def get_position_history(self, limit=20):
        """
        청산된 포지션 내역 조회

        Args:
            limit: 조회할 개수 (기본 20)
        """
        try:
            positions = self.futures_api.list_position_close(
                self.settle,
                limit=limit
            )

            result = []
            for pos in positions:
                # PositionClose 객체의 실제 속성들
                result.append({
                    'time': pos.time,
                    'contract': pos.contract,
                    'side': pos.side,
                    'pnl': float(pos.pnl)
                })

            return result

        except GateApiException as e:
            print(f"포지션 내역 조회 오류: {e}")
            return None

    def get_order_history(self, status='finished', limit=20):
        """
        주문 내역 조회

        Args:
            status: 'open', 'finished' (기본)
            limit: 조회할 개수
        """
        try:
            orders = self.futures_api.list_futures_orders(
                self.settle,
                status=status,
                limit=limit
            )

            result = []
            for order in orders:
                result.append({
                    'id': order.id,
                    'contract': order.contract,
                    'size': int(order.size),
                    'price': float(order.price) if order.price else 0,
                    'fill_price': float(order.fill_price) if order.fill_price else 0,
                    'status': order.status,
                    'side': 'long' if int(order.size) > 0 else 'short',
                    'create_time': order.create_time,
                    'finish_time': order.finish_time if hasattr(order, 'finish_time') else None
                })

            return result

        except GateApiException as e:
            print(f"주문 내역 조회 오류: {e}")
            return None

    def get_trade_history(self, limit=20):
        """
        체결 내역 조회 (실제 거래 내역)

        Args:
            limit: 조회할 개수
        """
        try:
            trades = self.futures_api.list_my_trades(
                self.settle,
                limit=limit
            )

            result = []
            for trade in trades:
                result.append({
                    'id': trade.id,
                    'create_time': trade.create_time,
                    'contract': trade.contract,
                    'order_id': trade.order_id,
                    'size': int(trade.size),
                    'price': float(trade.price),
                    'role': trade.role,  # 'taker' or 'maker'
                    'side': 'long' if int(trade.size) > 0 else 'short'
                })

            return result

        except GateApiException as e:
            print(f"체결 내역 조회 오류: {e}")
            return None
