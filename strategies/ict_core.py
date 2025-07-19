from datetime import datetime, timedelta, time
from binance.client import Client
from utils.logger import logger
from core.config import config
import pandas as pd
import numpy as np

class ICTStrategy:
    def __init__(self):
        self.client = Client(api_key=config.BINANCE_API_KEY, api_secret=config.BINANCE_SECRET)
        self.symbol = None
        self.last_update = "2025-07-16"

        # ✅ RULE YANG LEBIH FLEKSIBEL UNTUK LEBIH BANYAK SINYAL
        self.ict_rules = {
            "ob_validation": {
                "min_size": 0.3,  # Dikurangi dari 0.5 ke 0.3
                "max_age": 72,    # Ditambah dari 48 ke 72 jam
                "clean_sweep": 0.65  # Dikurangi dari 0.8 ke 0.65
            },
            "bos_validation": {
                "min_strength": 55,  # Dikurangi dari 65 ke 55
                "confirmation": 2,   # Dikurangi dari 3 ke 2
                "clean_break": True
            },
            "mitigation": {
                "required": True,
                "max_depth": 0.85,   # Dinaikkan dari 0.786 ke 0.85
                "min_volume": 30     # Dikurangi dari 50 ke 30
            }
        }

    def get_ohlcv(self, symbol, interval="15m", limit=200):  # Ditambah limit dari 100 ke 200
        """Get OHLCV data from Binance"""
        try:
            klines = self.client.futures_klines(symbol=symbol, interval=interval, limit=limit)
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close',
                'volume', 'close_time', 'quote_asset_volume',
                'num_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # ✅ TAMBAH INDIKATOR UNTUK MENINGKATKAN DETEKSI
            df['atr'] = self.calculate_atr(df, period=14)
            df['ema_20'] = df['close'].ewm(span=20).mean()
            df['ema_50'] = df['close'].ewm(span=50).mean()
            
            return df
        except Exception as e:
            logger.error(f"Failed to get OHLCV for {symbol}: {e}")
            return pd.DataFrame()

    def calculate_atr(self, df, period=14):
        """Calculate Average True Range"""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            return true_range.rolling(window=period).mean()
        except:
            return pd.Series([0.001] * len(df))

    def find_fvg(self, df):
        """Temukan Fair Value Gaps dengan threshold yang lebih sensitif"""
        fvgs = []
        for i in range(2, len(df)):
            prev2 = df.iloc[i - 2]
            prev1 = df.iloc[i - 1]
            curr = df.iloc[i]
            
            # ✅ THRESHOLD YANG LEBIH KECIL UNTUK LEBIH BANYAK FVG
            gap_threshold = df['atr'].iloc[i] * 0.3  # Dikurangi threshold
            
            # FVG Bullish: gap up
            if prev2['low'] > curr['high'] and (prev2['low'] - curr['high']) >= gap_threshold:
                fvgs.append({
                    'type': 'bullish',
                    'start': curr['high'],
                    'end': prev2['low'],
                    'index': i,
                    'timestamp': curr['timestamp'],
                    'size': prev2['low'] - curr['high']
                })
            # FVG Bearish: gap down
            elif prev2['high'] < curr['low'] and (curr['low'] - prev2['high']) >= gap_threshold:
                fvgs.append({
                    'type': 'bearish',
                    'start': prev2['high'],
                    'end': curr['low'],
                    'index': i,
                    'timestamp': curr['timestamp'],
                    'size': curr['low'] - prev2['high']
                })
        return fvgs

    def ob_overlaps_fvg(self, ob, fvgs):
        """Check if Order Block overlaps with FVG - LEBIH FLEKSIBEL"""
        for fvg in fvgs:
            if ob['type'] == 'BULLISH' and fvg['type'] == 'bullish':
                # ✅ TOLERANSI YANG LEBIH BESAR
                tolerance = abs(ob['entry_price'] - fvg['start']) * 0.05
                if (fvg['start'] - tolerance) <= ob['entry_price'] <= (fvg['end'] + tolerance):
                    return True
            elif ob['type'] == 'BEARISH' and fvg['type'] == 'bearish':
                tolerance = abs(ob['entry_price'] - fvg['start']) * 0.05
                if (fvg['end'] - tolerance) <= ob['entry_price'] <= (fvg['start'] + tolerance):
                    return True
        return False

    def is_displacement_candle(self, candle):
        """Validasi displacement yang lebih fleksibel"""
        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']
        
        if total_range == 0:
            return False
            
        body_percentage = body / total_range
        return body_percentage >= 0.45  # Dikurangi dari 0.6 ke 0.45

    def detect_liquidity_sweep(self, df, index):
        """Detect liquidity sweep dengan lookback yang lebih pendek"""
        if index < 5:  # Dikurangi dari 10 ke 5
            return False
            
        recent_data = df.iloc[index-8:index]  # Dikurangi dari 10 ke 8
        current_candle = df.iloc[index]
        
        recent_high = recent_data['high'].max()
        recent_low = recent_data['low'].min()
        
        # ✅ THRESHOLD YANG LEBIH KECIL UNTUK SWEEP
        atr_value = df['atr'].iloc[index]
        sweep_threshold = atr_value * 0.3  # Tambah threshold minimum
        
        swept_high = current_candle['high'] > (recent_high + sweep_threshold)
        swept_low = current_candle['low'] < (recent_low - sweep_threshold)
        
        return swept_high or swept_low

    def calculate_sl_tp_levels(self, ob_candle, ob_type):
        """Calculate SL and TP levels dengan RR yang lebih konservatif"""
        try:
            if ob_type == 'BULLISH':
                entry = ob_candle['open']
                sl = ob_candle['low'] * 0.9985  # Sedikit lebih ketat
                risk = entry - sl
                tp1 = entry + (risk * 1.2)  # RR 1:1.2
                tp2 = entry + (risk * 2.0)  # RR 1:2
            else:  # BEARISH
                entry = ob_candle['open']
                sl = ob_candle['high'] * 1.0015  # Sedikit lebih ketat
                risk = sl - entry
                tp1 = entry - (risk * 1.2)  # RR 1:1.2
                tp2 = entry - (risk * 2.0)  # RR 1:2

            return {
                'entry': round(entry, 4),
                'sl': round(sl, 4),
                'tp1': round(tp1, 4),
                'tp2': round(tp2, 4)
            }
        except Exception as e:
            logger.error(f"Error calculating SL/TP: {e}")
            return None

    def find_order_blocks(self, symbol):
        """Find Order Blocks dengan kriteria yang lebih fleksibel"""
        try:
            self.symbol = symbol
            df = self.get_ohlcv(symbol)
            
            if df.empty:
                logger.warning(f"No data received for {symbol}")
                return []

            order_blocks = []
            fvgs = self.find_fvg(df)
            
            for i in range(5, len(df) - 1):  # Mulai dari index 5
                current = df.iloc[i]
                next_candle = df.iloc[i + 1]
                
                # ✅ SKIP DISPLACEMENT CHECK UNTUK LEBIH BANYAK OB
                # if not self.is_displacement_candle(current):
                #     continue
                
                # ✅ LIQUIDITY SWEEP OPSIONAL
                has_sweep = self.detect_liquidity_sweep(df, i)
                
                # ✅ TREND CONFIRMATION DENGAN EMA
                trend_bullish = current['close'] > df['ema_20'].iloc[i]
                trend_bearish = current['close'] < df['ema_20'].iloc[i]
                
                # BULLISH Order Block - Kriteria yang lebih fleksibel
                if (current['close'] > current['open'] and
                    (current['close'] - current['open']) > df['atr'].iloc[i] * 0.3 and
                    trend_bullish):  # Tambah trend confirmation
                    
                    levels = self.calculate_sl_tp_levels(current, 'BULLISH')
                    if not levels:
                        continue
                    
                    ob = {
                        'pair': symbol,
                        'type': 'BULLISH',
                        'entry_price': levels['entry'],
                        'sl_price': levels['sl'],
                        'tp1_price': levels['tp1'],
                        'tp2_price': levels['tp2'],
                        'created_at': current['timestamp'],
                        'size': current['high'] - current['low'],
                        'sweep_percentage': 0.75,  # Dikurangi threshold
                        'bos_strength': 65,
                        'mitigation_depth': 0.5,
                        'mitigation_volume': current['volume'],
                        'strength': 70 if has_sweep else 60,  # Berbeda berdasarkan sweep
                        'candle_data': current,
                        'has_sweep': has_sweep
                    }
                    
                    # ✅ TIDAK WAJIB OVERLAP FVG
                    if len(fvgs) == 0 or self.ob_overlaps_fvg(ob, fvgs) or not has_sweep:
                        order_blocks.append(ob)

                # BEARISH Order Block - Kriteria yang lebih fleksibel
                elif (current['close'] < current['open'] and
                      (current['open'] - current['close']) > df['atr'].iloc[i] * 0.3 and
                      trend_bearish):  # Tambah trend confirmation
                    
                    levels = self.calculate_sl_tp_levels(current, 'BEARISH')
                    if not levels:
                        continue
                    
                    ob = {
                        'pair': symbol,
                        'type': 'BEARISH',
                        'entry_price': levels['entry'],
                        'sl_price': levels['sl'],
                        'tp1_price': levels['tp1'],
                        'tp2_price': levels['tp2'],
                        'created_at': current['timestamp'],
                        'size': current['high'] - current['low'],
                        'sweep_percentage': 0.75,
                        'bos_strength': 65,
                        'mitigation_depth': 0.5,
                        'mitigation_volume': current['volume'],
                        'strength': 70 if has_sweep else 60,
                        'candle_data': current,
                        'has_sweep': has_sweep
                    }
                    
                    # ✅ TIDAK WAJIB OVERLAP FVG
                    if len(fvgs) == 0 or self.ob_overlaps_fvg(ob, fvgs) or not has_sweep:
                        order_blocks.append(ob)

            logger.info(f"Found {len(order_blocks)} valid order blocks for {symbol}")
            return order_blocks
            
        except Exception as e:
            logger.error(f"Order block finding error for {symbol}: {e}")
            return []

    def validate_order_blocks(self, obs):
        """Validate Order Blocks dengan rules yang lebih fleksibel"""
        valid_obs = []
        now = datetime.utcnow()
        
        for ob in obs:
            try:
                # Check age
                if isinstance(ob['created_at'], str):
                    ob_time = datetime.fromisoformat(ob['created_at'])
                else:
                    ob_time = ob['created_at']
                    
                age = (now - ob_time).total_seconds() / 3600
                
                # ✅ VALIDATION YANG LEBIH LONGGAR
                if ob['size'] < self.ict_rules['ob_validation']['min_size']:
                    continue
                if age > self.ict_rules['ob_validation']['max_age']:
                    continue
                if ob['sweep_percentage'] < self.ict_rules['ob_validation']['clean_sweep']:
                    continue
                    
                valid_obs.append(ob)
            except Exception as e:
                logger.error(f"Error validating order block: {e}")
                continue
                
        return valid_obs

    def validate_bos(self, ob):
        """Validate Break of Structure"""
        return ob['bos_strength'] >= self.ict_rules['bos_validation']['min_strength']

    def check_mitigation(self, ob):
        """Check mitigation requirements"""
        if not self.ict_rules['mitigation']['required']:
            return True
        if ob['mitigation_depth'] > self.ict_rules['mitigation']['max_depth']:
            return False
        if ob['mitigation_volume'] < self.ict_rules['mitigation']['min_volume']:
            return False
        return True

    def in_killzone(self):
        """Check if current time is in ICT killzone - DIPERPANJANG"""
        now = datetime.utcnow().time()
        # ✅ KILLZONE YANG LEBIH PANJANG
        london_kz = time(6, 0) <= now <= time(11, 0)  # 6:00-11:00 UTC
        ny_kz = time(12, 0) <= now <= time(17, 0)     # 12:00-17:00 UTC
        asian_kz = time(23, 0) <= now or now <= time(2, 0)  # 23:00-02:00 UTC
        
        return london_kz or ny_kz or asian_kz

    def get_multiple_timeframes(self, symbol):
        """Analisis multiple timeframes untuk konfirmasi"""
        timeframes = ['5m', '15m', '1h']
        signals_count = 0
        
        for tf in timeframes:
            df = self.get_ohlcv(symbol, interval=tf, limit=100)
            if not df.empty:
                obs = self.find_order_blocks(symbol)
                signals_count += len(obs)
        
        return signals_count > 0

    def find_signals(self, bias, symbol):
        """Main function untuk mencari trading signals - OPTIMIZED"""
        try:
            signals = []
            
            # ✅ TRADING SEPANJANG HARI DENGAN PRIORITY KILLZONE
            is_killzone = self.in_killzone()
            
            # Find and validate order blocks
            obs = self.find_order_blocks(symbol)
            valid_obs = self.validate_order_blocks(obs)
            
            # ✅ PRIORITAS BERDASARKAN KUALITAS
            priority_obs = []
            normal_obs = []
            
            for ob in valid_obs:
                if self.validate_bos(ob) and self.check_mitigation(ob):
                    if ob['has_sweep'] and is_killzone:
                        priority_obs.append(ob)  # High priority
                    else:
                        normal_obs.append(ob)    # Normal priority
            
            # Create signals dari priority obs dulu
            for ob in priority_obs:
                signal = self.create_signal(ob, bias)
                signal.priority = "HIGH"
                signals.append(signal)
                logger.info(f"HIGH PRIORITY Signal: {signal.direction} {signal.pair} @ {signal.entry}")
            
            # Tambah normal signals jika belum cukup
            if len(signals) < 3:
                for ob in normal_obs[:3-len(signals)]:
                    signal = self.create_signal(ob, bias)
                    signal.priority = "NORMAL"
                    signals.append(signal)
                    logger.info(f"NORMAL Signal: {signal.direction} {signal.pair} @ {signal.entry}")
            
            logger.info(f"Total signals generated: {len(signals)}")
            return signals
            
        except Exception as e:
            logger.error(f"Signal finding error for {symbol}: {e}")
            return []

    def create_signal(self, ob, bias):
        """Create trading signal from Order Block"""
        return Signal(
            pair=ob['pair'],
            direction="BUY" if ob['type'] == "BULLISH" else "SELL",
            entry=ob['entry_price'],
            sl=ob['sl_price'],
            tp1=ob['tp1_price'],
            tp2=ob['tp2_price'],
            strength=ob['strength'],
            bias=bias.get('strength', 70),
            regime=bias.get('regime_score', 0.5),
            volatility=bias.get('volatility', 0.3),
            has_sweep=ob.get('has_sweep', False)
        )


class Signal:
    def __init__(self, pair, direction, entry, sl, tp1, tp2,
                 strength, bias, regime, volatility, has_sweep=False):
        self.pair = pair
        self.direction = direction
        self.entry = entry
        self.sl = sl
        self.tp1 = tp1
        self.tp2 = tp2
        self.strength = strength
        self.bias = bias
        self.regime = regime
        self.volatility = volatility
        self.has_sweep = has_sweep
        self.priority = "NORMAL"  # Default priority
        self.created_at = datetime.utcnow()

    def __str__(self):
        return f"Signal({self.direction} {self.pair} @ {self.entry}, SL: {self.sl}, TP1: {self.tp1}, TP2: {self.tp2}, Priority: {self.priority})"

    def to_dict(self):
        return {
            'pair': self.pair,
            'direction': self.direction,
            'entry': self.entry,
            'sl': self.sl,
            'tp1': self.tp1,
            'tp2': self.tp2,
            'strength': self.strength,
            'bias': self.bias,
            'regime': self.regime,
            'volatility': self.volatility,
            'has_sweep': self.has_sweep,
            'priority': self.priority,
            'created_at': self.created_at.isoformat()
        }

    def validate_levels(self):
        """Validate that SL and TP levels make sense"""
        if self.direction == "BUY":
            return (self.sl < self.entry < self.tp1 < self.tp2)
        else:  # SELL
            return (self.sl > self.entry > self.tp1 > self.tp2)