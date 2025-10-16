# Gate.io API Configuration
# Copy this file to config.py and fill in your actual API keys

API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"

# Environment
TESTNET = True  # Set to True for testnet, False for mainnet

# Trading Configuration
SYMBOL = "ETH_USDT"  # Trading pair
LEVERAGE = 10  # Leverage for futures trading
ORDER_SIZE = 0.01  # Order size in ETH

# Risk Management
MAX_POSITION_SIZE = 0.01  # Maximum position size
STOP_LOSS_PERCENT = 2.0  # Stop loss percentage
TAKE_PROFIT_PERCENT = 5.0  # Take profit percentage

# Strategy Settings
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
