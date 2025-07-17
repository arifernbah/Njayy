import os
from dotenv import load_dotenv
import requests

class Config:
    def __init__(self):
        load_dotenv()
        
        # API Credentials
        self.BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
        self.BINANCE_SECRET = os.getenv('BINANCE_SECRET')
        
        # Telegram Config
        self.TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
        
        # Bluechip/major coin list (bukan shitcoin)
        self.BLUECHIP_BASE_ASSETS = [
            'BTC','ETH','BNB','SOL','ADA','XRP','DOGE','LINK','AVAX','MATIC','DOT','LTC','TRX','OP','ARB','BCH','UNI','ETC','FIL','APT','ATOM','NEAR','XLM','SUI','INJ','RNDR','PEPE','TIA','SEI','JTO','WIF','STX','DYDX','BLUR','APE','GRT','AAVE','SNX','SAND','MKR','RUNE','LDO','IMX','FTM','FLOW','GMT','COMP','CRV','ALGO','EOS','CRO','XTZ','ZIL','ENJ','KAVA','1INCH','BAND','BAT','CHZ','CVC','DASH','DGB','ICX','IOST','KNC','MANA','NKN','OCEAN','ONT','QTUM','SC','SKL','SRM','STMX','STPT','SXP','TOMO','VET','VTHO','WAVES','XEM','XMR','ZEC','ZEN','ZRX'
        ]
        
        # ✅ Trading Pairs - default fallback
        self.TRADING_PAIRS = os.getenv('TRADING_PAIRS', 'BTCUSDT,ETHUSDT,ADAUSDT,BNBUSDT,SOLUSDT,XRPUSDT').split(',')
        
        # ✅ Top Volume Configuration (hardcoded, no .env needed)
        self.USE_TOP_VOLUME_PAIRS = True  # Set to True to use top volume pairs
        self.TOP_VOLUME_COUNT = 10        # Number of top volume pairs to use
        self.VOLUME_TIMEFRAME = '24h'     # Volume timeframe (24h, 1h, etc.)
        
        if self.USE_TOP_VOLUME_PAIRS:
            try:
                url = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
                resp = requests.get(url, timeout=10)
                data = resp.json()
                # Filter USDT pairs only
                usdt_pairs = [d for d in data if d['symbol'].endswith('USDT')]
                # Filter bluechip/major only
                bluechip_pairs = [d for d in usdt_pairs if d['symbol'][:-4] in self.BLUECHIP_BASE_ASSETS]
                # Sort by quoteVolume (USDT volume) descending
                bluechip_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
                # Ambil 10 teratas
                self.TRADING_PAIRS = [d['symbol'] for d in bluechip_pairs[:self.TOP_VOLUME_COUNT]]
            except Exception as e:
                print(f"[Config] Gagal fetch top volume pairs: {e}")
        
        # Trading Parameters
        self.MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', 6))
        self.MAX_DRAWDOWN = float(os.getenv('MAX_DRAWDOWN', 15.0))
        self.DEFAULT_RISK = float(os.getenv('DEFAULT_RISK', 2.0))
        
        # Additional Trading Settings
        self.REDUCED_RISK = float(os.getenv('REDUCED_RISK', 1.0))
        self.MINIMUM_RISK = float(os.getenv('MINIMUM_RISK', 0.5))
        self.MAX_CONCURRENT_TRADES = int(os.getenv('MAX_CONCURRENT_TRADES', 2))
        
        # Signal Filters
        self.MIN_SIGNAL_STRENGTH = int(os.getenv('MIN_SIGNAL_STRENGTH', 70))
        self.MIN_BIAS_STRENGTH = int(os.getenv('MIN_BIAS_STRENGTH', 35))
        self.MIN_REGIME_SCORE = int(os.getenv('MIN_REGIME_SCORE', 55))
        
        # Volatility Range
        self.VOL_RANGE_MIN = float(os.getenv('VOL_RANGE_MIN', 0.4))
        self.VOL_RANGE_MAX = float(os.getenv('VOL_RANGE_MAX', 1.8))
        
        # Session Settings
        self.LONDON_START = os.getenv('LONDON_START', '07:00')
        self.LONDON_END = os.getenv('LONDON_END', '16:00')
        self.NY_START = os.getenv('NY_START', '14:00')
        self.NY_END = os.getenv('NY_END', '23:00')
        self.ASIAN_START = os.getenv('ASIAN_START', '00:00')
        self.ASIAN_END = os.getenv('ASIAN_END', '09:00')
        
        # Session Minimum Scores
        self.LONDON_MIN_SCORE = int(os.getenv('LONDON_MIN_SCORE', 70))
        self.NY_MIN_SCORE = int(os.getenv('NY_MIN_SCORE', 70))
        self.ASIAN_MIN_SCORE = int(os.getenv('ASIAN_MIN_SCORE', 80))
        
        # Bot Settings
        self.LOOP_INTERVAL = int(os.getenv('LOOP_INTERVAL', 60))  # seconds
        self.ENABLE_TELEGRAM = os.getenv('ENABLE_TELEGRAM', 'True').lower() == 'true'
        
        # Performance Targets
        self.TARGET_WIN_RATE = float(os.getenv('TARGET_WIN_RATE', 60.0))
        self.SIGNAL_TARGET_MIN = int(os.getenv('SIGNAL_TARGET_MIN', 3))
        self.SIGNAL_TARGET_MAX = int(os.getenv('SIGNAL_TARGET_MAX', 6))
        
        # Timeframes
        self.HTF1 = os.getenv('HTF1', 'Daily')
        self.HTF2 = os.getenv('HTF2', '4H')
        self.ENTRY_TF = os.getenv('ENTRY_TF', '15M')
        
        # Retry config for Binance API
        self.BINANCE_MAX_RETRIES = int(os.getenv('BINANCE_MAX_RETRIES', 5))
        self.BINANCE_RETRY_DELAY = float(os.getenv('BINANCE_RETRY_DELAY', 2.0))
        
        # Validate critical settings
        self._validate_config()
    
    def _validate_config(self):
        """Validate critical configuration settings"""
        critical_settings = [
            ('BINANCE_API_KEY', self.BINANCE_API_KEY),
            ('BINANCE_SECRET', self.BINANCE_SECRET),
            ('TELEGRAM_TOKEN', self.TELEGRAM_TOKEN),
            ('TELEGRAM_CHAT_ID', self.TELEGRAM_CHAT_ID)
        ]
        
        missing_settings = []
        for setting_name, setting_value in critical_settings:
            if not setting_value:
                missing_settings.append(setting_name)
        
        if missing_settings:
            raise ValueError(f"Missing critical environment variables: {', '.join(missing_settings)}")
        
        # Validate numeric ranges
        if self.DEFAULT_RISK > 10:
            raise ValueError("DEFAULT_RISK should not exceed 10%")
        
        if self.MAX_DRAWDOWN > 50:
            raise ValueError("MAX_DRAWDOWN should not exceed 50%")
        
        if self.MIN_SIGNAL_STRENGTH < 0 or self.MIN_SIGNAL_STRENGTH > 100:
            raise ValueError("MIN_SIGNAL_STRENGTH should be between 0 and 100")
        
        # ✅ Validate trading pairs
        if not self.TRADING_PAIRS or len(self.TRADING_PAIRS) == 0:
            raise ValueError("At least one trading pair must be configured")
        
        # ✅ Validate top volume settings
        if self.USE_TOP_VOLUME_PAIRS and self.TOP_VOLUME_COUNT <= 0:
            raise ValueError("TOP_VOLUME_COUNT must be greater than 0")
    
    def get_risk_settings(self):
        """Get risk management settings as dict"""
        return {
            'default_risk': self.DEFAULT_RISK / 100,  # Convert to decimal
            'reduced_risk': self.REDUCED_RISK / 100,
            'minimum_risk': self.MINIMUM_RISK / 100,
            'max_trades': self.MAX_DAILY_TRADES,
            'max_concurrent': self.MAX_CONCURRENT_TRADES
        }
    
    def get_session_settings(self):
        """Get trading session settings as dict"""
        return {
            "London": {
                "start": self.LONDON_START,
                "end": self.LONDON_END,
                "min_score": self.LONDON_MIN_SCORE
            },
            "New York": {
                "start": self.NY_START,
                "end": self.NY_END,
                "min_score": self.NY_MIN_SCORE
            },
            "Asian": {
                "start": self.ASIAN_START,
                "end": self.ASIAN_END,
                "min_score": self.ASIAN_MIN_SCORE
            }
        }
    
    def get_filter_settings(self):
        """Get signal filter settings as dict"""
        return {
            'signal_strength': self.MIN_SIGNAL_STRENGTH,
            'bias_strength': self.MIN_BIAS_STRENGTH,
            'regime_score': self.MIN_REGIME_SCORE,
            'vol_range': [self.VOL_RANGE_MIN, self.VOL_RANGE_MAX]
        }
    
    def get_timeframe_settings(self):
        """Get timeframe settings as dict"""
        return {
            "HTF1": self.HTF1,
            "HTF2": self.HTF2,
            "Entry": self.ENTRY_TF
        }
    
    # ✅ Added method to get trading pairs
    def get_trading_pairs(self):
        """Get list of trading pairs"""
        return self.TRADING_PAIRS
    
    # ✅ Added method to get top volume settings
    def get_top_volume_settings(self):
        """Get top volume configuration settings"""
        return {
            'use_top_volume': self.USE_TOP_VOLUME_PAIRS,
            'count': self.TOP_VOLUME_COUNT,
            'timeframe': self.VOLUME_TIMEFRAME
        }

# Create global config instance
config = Config()