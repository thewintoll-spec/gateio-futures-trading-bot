"""
Gate.io Futures Exchange API Wrapper
"""
import gate_api
from gate_api.exceptions import ApiException, GateApiException
import config


class GateioFutures:
    def __init__(self, testnet=False):
        """Initialize Gate.io Futures API client"""
        # Configure host based on environment
        if testnet:
            host = "https://api-testnet.gateapi.io/api/v4"
        else:
            host = "https://api.gateio.ws/api/v4"

        configuration = gate_api.Configuration(host=host)
        configuration.key = config.API_KEY
        configuration.secret = config.API_SECRET

        # Create API client and futures API instance
        api_client = gate_api.ApiClient(configuration)
        self.futures_api = gate_api.FuturesApi(api_client)
        self.settle = 'usdt'  # USDT settled futures
        self.testnet = testnet

    def get_account_balance(self):
        """Get account balance"""
        try:
            account = self.futures_api.list_futures_accounts(self.settle)
            return {
                'total': account.total,
                'available': account.available,
                'position_margin': account.position_margin,
                'order_margin': account.order_margin
            }
        except GateApiException as e:
            print(f"Error getting account balance: {e}")
            return None

    def get_current_price(self, symbol):
        """Get current price for a symbol"""
        try:
            contract = symbol  # Keep underscore: ETH_USDT
            tickers = self.futures_api.list_futures_tickers(self.settle, contract=contract)
            if tickers:
                return float(tickers[0].last)
            return None
        except GateApiException as e:
            print(f"Error getting price: {e}")
            return None

    def get_position(self, symbol):
        """Get current position for a symbol"""
        try:
            contract = symbol
            # list_positions returns all positions, filter by contract
            positions = self.futures_api.list_positions(self.settle)
            # Filter for the specific contract
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
            print(f"Error getting position: {e}")
            return None

    def set_leverage(self, symbol, leverage):
        """Set leverage for a symbol"""
        try:
            contract = symbol
            self.futures_api.update_position_leverage(
                self.settle,
                contract,
                str(leverage)
            )
            print(f"Leverage set to {leverage}x for {symbol}")
            return True
        except GateApiException as e:
            print(f"Error setting leverage: {e}")
            return False

    def place_order(self, symbol, side, size, price=None, order_type='market'):
        """
        Place an order

        Args:
            symbol: Trading pair (e.g., 'BTC_USDT')
            side: 'long' or 'short'
            size: Order size (number of contracts)
            price: Limit price (for limit orders)
            order_type: 'market' or 'limit'
        """
        try:
            contract = symbol

            # Prepare order
            order = gate_api.FuturesOrder(
                contract=contract,
                size=size if side == 'long' else -size,  # Negative for short
                tif='ioc' if order_type == 'market' else 'gtc',
                price=str(price) if price else '0'
            )

            result = self.futures_api.create_futures_order(self.settle, order)
            print(f"Order placed: {side} {abs(size)} contracts at {order_type}")
            return result

        except GateApiException as e:
            print(f"Error placing order: {e}")
            return None

    def close_position(self, symbol):
        """Close all positions for a symbol"""
        try:
            position = self.get_position(symbol)
            if position and position['size'] != 0:
                size = position['size']
                side = 'short' if size > 0 else 'long'  # Opposite side to close
                self.place_order(symbol, side, abs(size), order_type='market')
                print(f"Position closed for {symbol}")
                return True
            else:
                print(f"No open position for {symbol}")
                return False
        except Exception as e:
            print(f"Error closing position: {e}")
            return False

    def get_candlesticks(self, symbol, interval='1m', limit=100):
        """
        Get candlestick data

        Args:
            symbol: Trading pair
            interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles
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
            print(f"Error getting candlesticks: {e}")
            return None
