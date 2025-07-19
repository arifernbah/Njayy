import os
from dotenv import load_dotenv
import requests

class Config:
    def __init__(self):
        load_dotenv()
        self.DEFAULT_INTERVAL = os.getenv('DEFAULT_INTERVAL', '15m')
        
        # API Credentials
        self.BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
        self.BINANCE_SECRET = os.getenv('BINANCE_SECRET')
        self.BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', os.getenv('BINANCE_SECRET'))
        
        # Telegram Config
        self.TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
        
        # Bluechip/major coin list (bukan shitcoin)
        self.BLUECHIP_BASE_ASSETS = [
            'BTC','ETH','BNB','SOL','ADA','XRP','DOGE','LINK','AVAX','MATIC','DOT','LTC','TRX','OP','ARB','BCH','UNI','ETC','FIL','APT','ATOM','NEAR','XLM','SUI','INJ','RNDR','PEPE','TIA','SEI','JTO','WIF','STX','DYDX','BLUR','APE','GRT','AAVE','SNX','SAND','MKR','RUNE','LDO','IMX','FTM','FLOW','GMT','COMP','CRV','ALGO','EOS','CRO','XTZ','ZIL','ENJ','KAVA','1INCH','BAND','BAT','CHZ','CVC','DASH','DGB','ICX','IOST','KNC','MANA','NKN','OCEAN','ONT','QTUM','SC','SKL','SRM','STMX','STPT','SXP','TOMO','VET','VTHO','WAVES','XEM','XMR','ZEC','ZEN','ZRX'
        ]
        
        # ✅ Trading Pairs - default fallback
        self.TRADING_PAIRS = os.getenv('TRADING_PAIRS', 'BTCUSDT,ETHUSDT,ADAUSDT,BNBUSDT,SOLUSDT,XRPUSDT').split(',')
        
        # ✅ Top Volume Configuration (configurable via .env)
        self.USE_TOP_VOLUME_PAIRS = os.getenv('USE_TOP_VOLUME_PAIRS', 'True').lower() == 'true'
        self.TOP_VOLUME_COUNT = int(os.getenv('TOP_VOLUME_COUNT', 10))
        self.VOLUME_TIMEFRAME = os.getenv('VOLUME_TIMEFRAME', '24h')
        
        if self.USE_TOP_VOLUME_PAIRS:
            try:
                url = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
                resp = requests.get(url, timeout=10)
                data = resp.json()
                # Filter USDT pairs only
                usdt_pairs = [d for d in data if isinstance(d, dict) and 'symbol' in d and d['symbol'].endswith('USDT')]
                # Filter bluechip/major only
                bluechip_pairs = [d for d in usdt_pairs if d['symbol'][:-4] in self.BLUECHIP_BASE_ASSETS]
                # Sort by quoteVolume (USDT volume) descending
                bluechip_pairs = [d for d in bluechip_pairs if 'quoteVolume' in d]
                bluechip_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
                # Ambil 10 teratas
                self.TRADING_PAIRS = [d['symbol'] for d in bluechip_pairs[:self.TOP_VOLUME_COUNT] if 'symbol' in d]
            except Exception as e:
                print(f"[Config] Gagal fetch top volume pairs: {e}")
        
        # Trading Parameters
        self.MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', 6))
        self.MAX_OPEN_POSITIONS = int(os.getenv('MAX_OPEN_POSITIONS', 2))
        self.MAX_DRAWDOWN = float(os.getenv('MAX_DRAWDOWN', 10.0))
        # ✅ FIXED: Use proper risk defaults that match .env.template
        self.DEFAULT_RISK = float(os.getenv('DEFAULT_RISK', 1.0))  # 1.0% default
        self.MIN_BALANCE = float(os.getenv('MIN_BALANCE', 5.0))  # Minimum balance for trading
        
        # Additional Trading Settings
        # ✅ FIXED: Use proper risk defaults that match .env.template
        self.REDUCED_RISK = float(os.getenv('REDUCED_RISK', 0.5))  # 0.5% reduced
        self.MINIMUM_RISK = float(os.getenv('MINIMUM_RISK', 0.25))  # 0.25% minimum
        self.MAX_CONCURRENT_TRADES = int(os.getenv('MAX_CONCURRENT_TRADES', 2))
        
        # Signal Filters
        self.MIN_SIGNAL_STRENGTH = int(os.getenv('MIN_SIGNAL_STRENGTH', 70))
        self.MIN_BIAS_STRENGTH = int(os.getenv('MIN_BIAS_STRENGTH', 35))
        self.MIN_REGIME_SCORE = int(os.getenv('MIN_REGIME_SCORE', 55))
        self.MIN_QUALITY_SCORE = int(os.getenv('MIN_QUALITY_SCORE', 70))
        
        # ✅ Price Deviation Validation Settings
        try:
            self.SIGNAL_MAX_ENTRY_DEVIATION = float(os.getenv('SIGNAL_MAX_ENTRY_DEVIATION', 0.05))  # 5% max entry deviation
            self.SIGNAL_MAX_SL_DEVIATION = float(os.getenv('SIGNAL_MAX_SL_DEVIATION', 0.10))        # 10% max SL deviation
            self.SIGNAL_MAX_TP_DEVIATION = float(os.getenv('SIGNAL_MAX_TP_DEVIATION', 0.15))        # 15% max TP deviation
            self.SIGNAL_EXECUTION_DEVIATION = float(os.getenv('SIGNAL_EXECUTION_DEVIATION', 0.03))  # 3% max for execution
        except (ValueError, TypeError) as e:
            print(f"❌ Error loading price deviation settings: {e}")
            print("Using default values...")
            self.SIGNAL_MAX_ENTRY_DEVIATION = 0.05
            self.SIGNAL_MAX_SL_DEVIATION = 0.10
            self.SIGNAL_MAX_TP_DEVIATION = 0.15
            self.SIGNAL_EXECUTION_DEVIATION = 0.03
        
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
        
        # Killzone Settings (from .env.template)
        self.KILLZONE_ASIA_LONDON_START = os.getenv('KILLZONE_ASIA_LONDON_START', '08:00')
        self.KILLZONE_ASIA_LONDON_END = os.getenv('KILLZONE_ASIA_LONDON_END', '18:00')
        self.KILLZONE_NY_START = os.getenv('KILLZONE_NY_START', '19:00')
        self.KILLZONE_NY_END = os.getenv('KILLZONE_NY_END', '22:00')
        
        # Session Minimum Scores
        self.LONDON_MIN_SCORE = int(os.getenv('LONDON_MIN_SCORE', 70))
        self.NY_MIN_SCORE = int(os.getenv('NY_MIN_SCORE', 70))
        self.ASIAN_MIN_SCORE = int(os.getenv('ASIAN_MIN_SCORE', 80))
        
        # Bot Settings
        self.LOOP_INTERVAL = int(os.getenv('LOOP_INTERVAL', 60))  # seconds
        self.ENABLE_TELEGRAM = os.getenv('ENABLE_TELEGRAM', 'True').lower() == 'true'
        self.TELEGRAM_COOLDOWN = int(os.getenv('TELEGRAM_COOLDOWN', 300))  # 5 minutes default
        
        # Leverage Settings (from .env.template)
        self.LEVERAGE = int(os.getenv('LEVERAGE', 5))
        
        # Logging Settings (from .env.template)
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        
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
        """Enhanced configuration validation with comprehensive checks"""
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
        
        # ✅ Enhanced numeric range validation
        if self.DEFAULT_RISK > 10:
            raise ValueError("DEFAULT_RISK should not exceed 10%")
        
        if self.MAX_DRAWDOWN > 50:
            raise ValueError("MAX_DRAWDOWN should not exceed 50%")
        
        if self.MIN_SIGNAL_STRENGTH < 0 or self.MIN_SIGNAL_STRENGTH > 100:
            raise ValueError("MIN_SIGNAL_STRENGTH should be between 0 and 100")
        
        if self.MIN_BIAS_STRENGTH < 0 or self.MIN_BIAS_STRENGTH > 100:
            raise ValueError("MIN_BIAS_STRENGTH should be between 0 and 100")
        
        if self.MIN_REGIME_SCORE < 0 or self.MIN_REGIME_SCORE > 100:
            raise ValueError("MIN_REGIME_SCORE should be between 0 and 100")
        
        if self.MIN_QUALITY_SCORE < 0 or self.MIN_QUALITY_SCORE > 100:
            raise ValueError("MIN_QUALITY_SCORE should be between 0 and 100")
        
        # ✅ Price deviation validation
        if self.SIGNAL_MAX_ENTRY_DEVIATION <= 0 or self.SIGNAL_MAX_ENTRY_DEVIATION > 0.20:
            raise ValueError("SIGNAL_MAX_ENTRY_DEVIATION should be between 0 and 20%")
        
        if self.SIGNAL_MAX_SL_DEVIATION <= 0 or self.SIGNAL_MAX_SL_DEVIATION > 0.30:
            raise ValueError("SIGNAL_MAX_SL_DEVIATION should be between 0 and 30%")
        
        if self.SIGNAL_MAX_TP_DEVIATION <= 0 or self.SIGNAL_MAX_TP_DEVIATION > 0.50:
            raise ValueError("SIGNAL_MAX_TP_DEVIATION should be between 0 and 50%")
        
        if self.SIGNAL_EXECUTION_DEVIATION <= 0 or self.SIGNAL_EXECUTION_DEVIATION > 0.10:
            raise ValueError("SIGNAL_EXECUTION_DEVIATION should be between 0 and 10%")
        
        # ✅ Trading pair validation
        if not self.TRADING_PAIRS or len(self.TRADING_PAIRS) == 0:
            raise ValueError("At least one trading pair must be configured")
        
        # ✅ Validate pair format
        for pair in self.TRADING_PAIRS:
            if not pair.endswith('USDT'):
                raise ValueError(f"Invalid trading pair format: {pair}. Must end with USDT")
        
        # ✅ Top volume settings validation
        if self.USE_TOP_VOLUME_PAIRS and self.TOP_VOLUME_COUNT <= 0:
            raise ValueError("TOP_VOLUME_COUNT must be greater than 0")
        
        if self.USE_TOP_VOLUME_PAIRS and self.TOP_VOLUME_COUNT > 50:
            raise ValueError("TOP_VOLUME_COUNT should not exceed 50 for performance reasons")
        
        # ✅ Leverage validation
        if self.LEVERAGE < 1 or self.LEVERAGE > 125:
            raise ValueError("LEVERAGE should be between 1 and 125")
        
        # ✅ Timeframe validation
        valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
        if self.DEFAULT_INTERVAL not in valid_timeframes:
            raise ValueError(f"Invalid DEFAULT_INTERVAL: {self.DEFAULT_INTERVAL}. Must be one of {valid_timeframes}")
        
        # ✅ Session time validation
        try:
            from datetime import datetime
            datetime.strptime(self.LONDON_START, '%H:%M')
            datetime.strptime(self.LONDON_END, '%H:%M')
            datetime.strptime(self.NY_START, '%H:%M')
            datetime.strptime(self.NY_END, '%H:%M')
            datetime.strptime(self.ASIAN_START, '%H:%M')
            datetime.strptime(self.ASIAN_END, '%H:%M')
        except ValueError as e:
            raise ValueError(f"Invalid session time format: {e}. Use HH:MM format")
        
        # ✅ Log level validation
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            raise ValueError(f"Invalid LOG_LEVEL: {self.LOG_LEVEL}. Must be one of {valid_log_levels}")
        
        # ✅ Performance target validation
        if self.TARGET_WIN_RATE < 0 or self.TARGET_WIN_RATE > 100:
            raise ValueError("TARGET_WIN_RATE should be between 0 and 100")
        
        if self.SIGNAL_TARGET_MIN < 0 or self.SIGNAL_TARGET_MAX < self.SIGNAL_TARGET_MIN:
            raise ValueError("Invalid signal target range")
        
        # ✅ Risk management validation
        if self.MAX_DAILY_TRADES < 1 or self.MAX_DAILY_TRADES > 50:
            raise ValueError("MAX_DAILY_TRADES should be between 1 and 50")
        
        if self.MAX_OPEN_POSITIONS < 1 or self.MAX_OPEN_POSITIONS > 10:
            raise ValueError("MAX_OPEN_POSITIONS should be between 1 and 10")
        
        if self.MAX_CONCURRENT_TRADES < 1 or self.MAX_CONCURRENT_TRADES > 5:
            raise ValueError("MAX_CONCURRENT_TRADES should be between 1 and 5")
        
        print("✅ Configuration validation passed successfully")
    
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
            'min_quality_score': self.MIN_QUALITY_SCORE,
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
    
    # ✅ Added method to get killzone settings
    def get_killzone_settings(self):
        """Get killzone configuration settings"""
        return {
            'asia_london_start': self.KILLZONE_ASIA_LONDON_START,
            'asia_london_end': self.KILLZONE_ASIA_LONDON_END,
            'ny_start': self.KILLZONE_NY_START,
            'ny_end': self.KILLZONE_NY_END
        }
    
    # ✅ Added method to get leverage settings
    def get_leverage_settings(self):
        """Get leverage configuration"""
        return {
            'leverage': self.LEVERAGE
        }
    
    def get_price_deviation_settings(self):
        """Get price deviation validation settings"""
        return {
            'max_entry_deviation': self.SIGNAL_MAX_ENTRY_DEVIATION,
            'max_sl_deviation': self.SIGNAL_MAX_SL_DEVIATION,
            'max_tp_deviation': self.SIGNAL_MAX_TP_DEVIATION,
            'execution_deviation': self.SIGNAL_EXECUTION_DEVIATION
        }

# Create global config instance
config = Config()