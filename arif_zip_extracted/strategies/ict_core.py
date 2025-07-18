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

        # ✅ NEW: ICT ENHANCED FEATURES
        self.vwap_periods = [20, 50, 200]  # Multiple VWAP timeframes
        self.premium_discount_zones = {
            'premium_threshold': 0.618,  # Fibonacci 0.618
            'discount_threshold': 0.382,  # Fibonacci 0.382
            'atr_multiplier': 0.618      # ATR multiplier for zones
        }
        self.institutional_volume = {
            'std_multiplier': 2.0,       # 2x standard deviation
            'min_volume_threshold': 1000  # Minimum volume threshold
        }
        self.ict_quality_scores = {
            'premium_signal': 85,        # Premium signal threshold
            'standard_signal': 70,       # Standard signal threshold
            'min_quality': 60           # Minimum quality score
        }

        self.ohlcv_data = {}  # Simpan data OHLCV per symbol

    def calculate_vwap(self, df, period=20):
        """Calculate Volume Weighted Average Price"""
        try:
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            vwap = (typical_price * df['volume']).rolling(window=period).sum() / df['volume'].rolling(window=period).sum()
            return vwap
        except Exception as e:
            logger.error(f"VWAP calculation error: {e}")
            return pd.Series([df['close'].mean()] * len(df))

    def calculate_premium_discount_zones(self, df):
        """Calculate Premium/Discount zones based on VWAP and ATR"""
        try:
            vwap = self.calculate_vwap(df, 20)
            atr = self.calculate_atr(df, 14)
            
            premium_zone_high = vwap + (atr * self.premium_discount_zones['premium_threshold'])
            premium_zone_low = vwap + (atr * self.premium_discount_zones['discount_threshold'])
            discount_zone_high = vwap - (atr * self.premium_discount_zones['discount_threshold'])
            discount_zone_low = vwap - (atr * self.premium_discount_zones['premium_threshold'])
            
            return {
                'vwap': vwap,
                'premium_zone': {'high': premium_zone_high, 'low': premium_zone_low},
                'discount_zone': {'high': discount_zone_high, 'low': discount_zone_low},
                'atr': atr
            }
        except Exception as e:
            logger.error(f"Premium/Discount zones calculation error: {e}")
            return None

    def detect_institutional_volume(self, df):
        """Detect institutional volume activity"""
        try:
            # Calculate volume moving average and standard deviation
            volume_ma = df['volume'].rolling(window=20).mean()
            volume_std = df['volume'].rolling(window=20).std()
            
            # Detect institutional volume (2x standard deviation)
            institutional_threshold = volume_ma + (volume_std * self.institutional_volume['std_multiplier'])
            
            # Find institutional volume spikes
            institutional_spikes = df['volume'] > institutional_threshold
            
            # Calculate institutional volume strength
            volume_strength = (df['volume'] - volume_ma) / volume_std
            
            return {
                'institutional_spikes': institutional_spikes,
                'volume_strength': volume_strength,
                'institutional_threshold': institutional_threshold,
                'volume_ma': volume_ma
            }
        except Exception as e:
            logger.error(f"Institutional volume detection error: {e}")
            return None

    def calculate_ict_quality_score(self, signal_data, zones_data, volume_data):
        """Calculate ICT Quality Score (0-100)"""
        try:
            score = 0
            
            # 1. Zone Quality (25 points)
            if zones_data:
                current_price = signal_data.get('entry_price', 0)
                vwap = zones_data['vwap'].iloc[-1] if not zones_data['vwap'].empty else 0
                
                if current_price > 0 and vwap > 0:
                    price_vs_vwap = abs(current_price - vwap) / vwap
                    if price_vs_vwap < 0.01:  # Very close to VWAP
                        score += 25
                    elif price_vs_vwap < 0.02:  # Close to VWAP
                        score += 20
                    elif price_vs_vwap < 0.05:  # Reasonable distance
                        score += 15
                    else:
                        score += 10
            
            # 2. Volume Quality (25 points)
            if volume_data:
                volume_strength = volume_data['volume_strength'].iloc[-1] if not volume_data['volume_strength'].empty else 0
                if volume_strength > 2.0:  # Strong institutional volume
                    score += 25
                elif volume_strength > 1.5:  # Good institutional volume
                    score += 20
                elif volume_strength > 1.0:  # Moderate institutional volume
                    score += 15
                else:
                    score += 10
            
            # 3. Signal Strength (25 points)
            signal_strength = signal_data.get('strength', 0)
            if signal_strength >= 85:
                score += 25
            elif signal_strength >= 75:
                score += 20
            elif signal_strength >= 65:
                score += 15
            else:
                score += 10
            
            # 4. Market Structure Quality (25 points)
            structure_quality = signal_data.get('structure_quality', 0)
            if structure_quality >= 85:
                score += 25
            elif structure_quality >= 75:
                score += 20
            elif structure_quality >= 65:
                score += 15
            else:
                score += 10
            
            return min(score, 100)  # Cap at 100
            
        except Exception as e:
            logger.error(f"ICT Quality Score calculation error: {e}")
            return 50  # Default score

    def classify_signal_quality(self, quality_score):
        """Classify signal based on quality score"""
        if quality_score >= self.ict_quality_scores['premium_signal']:
            return 'PREMIUM'
        elif quality_score >= self.ict_quality_scores['standard_signal']:
            return 'STANDARD'
        elif quality_score >= self.ict_quality_scores['min_quality']:
            return 'BASIC'
        else:
            return 'LOW_QUALITY'

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
            
            # ✅ NEW: ENHANCED ICT INDICATORS
            zones_data = self.calculate_premium_discount_zones(df)
            if zones_data:
                df['vwap'] = zones_data['vwap']
                df['premium_zone_high'] = zones_data['premium_zone']['high']
                df['premium_zone_low'] = zones_data['premium_zone']['low']
                df['discount_zone_high'] = zones_data['discount_zone']['high']
                df['discount_zone_low'] = zones_data['discount_zone']['low']
            
            volume_data = self.detect_institutional_volume(df)
            if volume_data:
                df['institutional_spikes'] = volume_data['institutional_spikes']
                df['volume_strength'] = volume_data['volume_strength']
                df['institutional_threshold'] = volume_data['institutional_threshold']
            
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
        """Main function untuk mencari trading signals - ENHANCED WITH ICT QUALITY"""
        try:
            signals = []
            
            # ✅ TRADING SEPANJANG HARI DENGAN PRIORITY KILLZONE
            is_killzone = self.in_killzone()
            
            # Get enhanced data with VWAP and zones
            df = self.get_ohlcv(symbol)
            if df.empty:
                return []
            
            # Calculate zones and volume data
            zones_data = self.calculate_premium_discount_zones(df)
            volume_data = self.detect_institutional_volume(df)
            
            # Find and validate order blocks
            obs = self.find_order_blocks(symbol)
            valid_obs = self.validate_order_blocks(obs)
            
            # ✅ ENHANCED PRIORITY SYSTEM WITH ICT QUALITY
            premium_signals = []
            standard_signals = []
            basic_signals = []
            
            for ob in valid_obs:
                if self.validate_bos(ob) and self.check_mitigation(ob):
                    # Calculate ICT Quality Score
                    signal_data = {
                        'entry_price': ob['entry_price'],
                        'strength': ob['strength'],
                        'structure_quality': ob.get('bos_strength', 70)
                    }
                    
                    quality_score = self.calculate_ict_quality_score(signal_data, zones_data, volume_data)
                    quality_class = self.classify_signal_quality(quality_score)
                    
                    # Enhanced signal creation with quality data
                    signal = self.create_signal(ob, bias)
                    signal.quality_score = quality_score
                    signal.quality_class = quality_class
                    signal.zones_data = zones_data
                    signal.volume_data = volume_data
                    
                    # Classify based on quality and killzone
                    if quality_class == 'PREMIUM' and is_killzone:
                        signal.priority = "PREMIUM"
                        premium_signals.append(signal)
                    elif quality_class in ['PREMIUM', 'STANDARD'] and is_killzone:
                        signal.priority = "HIGH"
                        standard_signals.append(signal)
                    else:
                        signal.priority = "NORMAL"
                        basic_signals.append(signal)
            
            # ✅ PRIORITY-BASED SIGNAL SELECTION
            # Add premium signals first
            for signal in premium_signals[:2]:  # Max 2 premium signals
                signals.append(signal)
                logger.info(f"PREMIUM Signal: {signal.direction} {signal.pair} @ {signal.entry} (Quality: {signal.quality_score})")
            
            # Add high priority signals
            for signal in standard_signals[:3-len(signals)]:
                signals.append(signal)
                logger.info(f"HIGH Signal: {signal.direction} {signal.pair} @ {signal.entry} (Quality: {signal.quality_score})")
            
            # Add normal signals if needed
            if len(signals) < 3:
                for signal in basic_signals[:3-len(signals)]:
                    signals.append(signal)
                    logger.info(f"NORMAL Signal: {signal.direction} {signal.pair} @ {signal.entry} (Quality: {signal.quality_score})")
            
            logger.info(f"Total signals generated: {len(signals)} (Premium: {len(premium_signals)}, Standard: {len(standard_signals)}, Basic: {len(basic_signals)})")
            return signals
            
        except Exception as e:
            logger.error(f"Signal finding error: {e}")
            return []

    def create_signal(self, ob, bias):
        """Create enhanced signal with ICT quality analysis"""
        try:
            # Calculate volatility
            volatility = ob['size'] / ob['entry_price'] * 100
            
            # Enhanced signal creation
            signal = Signal(
                pair=ob['pair'],
                direction=ob['type'],
                entry=ob['entry_price'],
                sl=ob['sl_price'],
                tp1=ob['tp1_price'],
                tp2=ob['tp2_price'],
                strength=ob['strength'],
                bias=bias['strength'],
                regime=bias['regime'],
                volatility=volatility,
                has_sweep=ob['has_sweep']
            )
            
            # Add enhanced ICT data
            signal.ob_data = ob
            signal.created_at = ob['created_at']
            signal.bos_strength = ob.get('bos_strength', 70)
            signal.mitigation_depth = ob.get('mitigation_depth', 0.5)
            
            return signal
            
        except Exception as e:
            logger.error(f"Signal creation error: {e}")
            return None

    def on_new_candle(self, symbol, candle):
        """Handler untuk candle baru dari websocket. Akan dipanggil setiap ada candle close baru."""
        import pandas as pd
        # Update rolling DataFrame OHLCV
        if symbol not in self.ohlcv_data:
            self.ohlcv_data[symbol] = pd.DataFrame(columns=['timestamp','open','high','low','close','volume','close_time'])
        df = self.ohlcv_data[symbol]
        new_row = pd.DataFrame([candle])
        df = pd.concat([df, new_row], ignore_index=True)
        # Jaga rolling window (misal 200 bar)
        if len(df) > 200:
            df = df.iloc[-200:]
        self.ohlcv_data[symbol] = df
        # Jalankan analisis sinyal jika cukup data
        if len(df) >= 50:
            # Gunakan df terbaru untuk analisis
            # (Bisa panggil find_signals atau logika lain sesuai strategi)
            # Contoh:
            bias = None  # Bias bisa diambil dari analyzer jika perlu
            signals = self.find_signals(bias, symbol)
            # Eksekusi sinyal jika ada
            if signals:
                for signal in signals:
                    # Validasi dan eksekusi (bisa diintegrasikan ke bot/trader)
                    pass  # TODO: Integrasi ke eksekusi order


class Signal:
    def __init__(self, pair, direction, entry, sl, tp1, tp2,
                 strength, bias, regime, volatility, has_sweep=False):
        self.pair = pair
        self.direction = "BUY" if direction == "BULLISH" else "SELL"
        self.entry = entry
        self.sl = sl
        self.tp1 = tp1
        self.tp2 = tp2
        self.strength = strength
        self.bias = bias
        self.regime = regime
        self.volatility = volatility
        self.has_sweep = has_sweep
        
        # ✅ NEW: ICT ENHANCED ATTRIBUTES
        self.quality_score = 0
        self.quality_class = "BASIC"
        self.priority = "NORMAL"
        self.zones_data = None
        self.volume_data = None
        self.ob_data = None
        self.created_at = None
        self.bos_strength = 70
        self.mitigation_depth = 0.5
        
        # ✅ NEW: PREMIUM/DISCOUNT ZONE INFO
        self.zone_position = "NEUTRAL"  # PREMIUM, DISCOUNT, NEUTRAL
        self.vwap_distance = 0.0
        self.institutional_volume_strength = 0.0
        
        # ✅ NEW: ICT QUALITY METRICS
        self.ict_metrics = {
            'zone_quality': 0,
            'volume_quality': 0,
            'signal_quality': 0,
            'structure_quality': 0
        }

    def __str__(self):
        return f"{self.direction} {self.pair} @ {self.entry} (Quality: {self.quality_score}, Class: {self.quality_class})"

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
            # ✅ NEW: ICT ENHANCED DATA
            'quality_score': self.quality_score,
            'quality_class': self.quality_class,
            'priority': self.priority,
            'zone_position': self.zone_position,
            'vwap_distance': self.vwap_distance,
            'institutional_volume_strength': self.institutional_volume_strength,
            'ict_metrics': self.ict_metrics
        }

    def validate_levels(self):
        """Enhanced validation with ICT quality checks"""
        try:
            # Basic validation
            if self.entry <= 0 or self.sl <= 0 or self.tp1 <= 0 or self.tp2 <= 0:
                return False
            
            # Direction-based validation
            if self.direction == "BUY":
                if not (self.sl < self.entry < self.tp1 < self.tp2):
                    return False
            else:  # SELL
                if not (self.tp2 < self.tp1 < self.entry < self.sl):
                    return False
            
            # ✅ NEW: ICT QUALITY VALIDATION
            if self.quality_score < 60:
                logger.warning(f"Low quality signal: {self.quality_score}")
                return False
            
            # Zone validation
            if self.zone_position == "NEUTRAL" and self.quality_class == "PREMIUM":
                logger.warning("Premium signal should have zone position")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Signal validation error: {e}")
            return False

    def update_zone_info(self, zones_data, volume_data):
        """Update signal with zone and volume information"""
        try:
            if zones_data and volume_data:
                current_price = self.entry
                vwap = zones_data['vwap'].iloc[-1] if not zones_data['vwap'].empty else 0
                
                # Calculate VWAP distance
                if vwap > 0:
                    self.vwap_distance = abs(current_price - vwap) / vwap
                
                # Determine zone position
                if not zones_data['premium_zone']['high'].empty and not zones_data['premium_zone']['low'].empty:
                    premium_high = zones_data['premium_zone']['high'].iloc[-1]
                    premium_low = zones_data['premium_zone']['low'].iloc[-1]
                    
                    if premium_low <= current_price <= premium_high:
                        self.zone_position = "PREMIUM"
                    elif not zones_data['discount_zone']['high'].empty and not zones_data['discount_zone']['low'].empty:
                        discount_high = zones_data['discount_zone']['high'].iloc[-1]
                        discount_low = zones_data['discount_zone']['low'].iloc[-1]
                        
                        if discount_low <= current_price <= discount_high:
                            self.zone_position = "DISCOUNT"
                        else:
                            self.zone_position = "NEUTRAL"
                
                # Update institutional volume strength
                if not volume_data['volume_strength'].empty:
                    self.institutional_volume_strength = volume_data['volume_strength'].iloc[-1]
                
        except Exception as e:
            logger.error(f"Zone info update error: {e}")

    def get_ict_summary(self):
        """Get ICT analysis summary"""
        return {
            'quality_score': self.quality_score,
            'quality_class': self.quality_class,
            'priority': self.priority,
            'zone_position': self.zone_position,
            'vwap_distance': f"{self.vwap_distance:.2%}",
            'institutional_volume': f"{self.institutional_volume_strength:.2f}",
            'ict_metrics': self.ict_metrics
        }