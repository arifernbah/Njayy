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
        self.last_update = "2025-01-16"

        # ✅ ENHANCED ICT RULES WITH ADVANCED CONCEPTS
        self.ict_rules = {
            "ob_validation": {
                "min_size": 0.3,
                "max_age": 72,
                "clean_sweep": 0.65,
                "institutional_size": 0.8,  # Minimum size for institutional OB
                "mitigation_required": True
            },
            "bos_validation": {
                "min_strength": 55,
                "confirmation": 2,
                "clean_break": True,
                "retest_required": True  # ICT retest concept
            },
            "mitigation": {
                "required": True,
                "max_depth": 0.85,
                "min_volume": 30,
                "fair_value_gap": True  # FVG mitigation
            },
            "premium_discount": {
                "enabled": True,
                "threshold": 0.618,  # Fibonacci level
                "volume_confirmation": True
            },
            "optimal_trade_entry": {
                "enabled": True,
                "time_based": True,
                "liquidity_sweep": True,
                "order_block_retest": True
            }
        }

        # ✅ ICT SPECIFIC PATTERNS
        self.ict_patterns = {
            "order_blocks": ["BULLISH", "BEARISH", "MITIGATION"],
            "fair_value_gaps": ["BULLISH", "BEARISH", "MITIGATED"],
            "liquidity_levels": ["EQUAL_HIGHS", "EQUAL_LOWS", "MITIGATED"],
            "market_structure": ["BOS", "CHoCH", "MITIGATION"]
        }

    def get_ohlcv(self, symbol, interval="15m", limit=200):
        """Get OHLCV data with enhanced ICT indicators"""
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
            
            # ✅ ENHANCED ICT INDICATORS
            df['atr'] = self.calculate_atr(df, period=14)
            df['ema_20'] = df['close'].ewm(span=20).mean()
            df['ema_50'] = df['close'].ewm(span=50).mean()
            df['vwap'] = self.calculate_vwap(df)
            df['volume_profile'] = self.calculate_volume_profile(df)
            df['premium_discount'] = self.calculate_premium_discount(df)
            df['institutional_volume'] = self.calculate_institutional_volume(df)
            
            return df
        except Exception as e:
            logger.error(f"Failed to get OHLCV for {symbol}: {e}")
            return pd.DataFrame()

    def calculate_vwap(self, df):
        """Calculate Volume Weighted Average Price"""
        try:
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
            return vwap
        except:
            return df['close']

    def calculate_volume_profile(self, df):
        """Calculate volume profile for ICT analysis"""
        try:
            # Volume weighted price levels
            volume_profile = df['volume'].rolling(window=20).mean()
            return volume_profile
        except:
            return df['volume']

    def calculate_premium_discount(self, df):
        """Calculate premium/discount zones based on ICT concepts"""
        try:
            vwap = self.calculate_vwap(df)
            atr = self.calculate_atr(df, period=14)
            
            # Premium zone: above VWAP + 0.618 ATR
            # Discount zone: below VWAP - 0.618 ATR
            premium_zone = vwap + (atr * 0.618)
            discount_zone = vwap - (atr * 0.618)
            
            current_price = df['close']
            premium_discount = np.where(
                current_price > premium_zone, 1,  # Premium
                np.where(current_price < discount_zone, -1, 0)  # Discount, Fair Value
            )
            
            return premium_discount
        except:
            return pd.Series([0] * len(df))

    def calculate_institutional_volume(self, df):
        """Calculate institutional volume patterns"""
        try:
            # Volume spike detection
            volume_ma = df['volume'].rolling(window=20).mean()
            volume_std = df['volume'].rolling(window=20).std()
            
            institutional_volume = np.where(
                df['volume'] > (volume_ma + 2 * volume_std), 1,  # High institutional activity
                0
            )
            
            return institutional_volume
        except:
            return pd.Series([0] * len(df))

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
        """Enhanced Fair Value Gap detection with ICT concepts"""
        fvgs = []
        for i in range(2, len(df)):
            prev2 = df.iloc[i - 2]
            prev1 = df.iloc[i - 1]
            curr = df.iloc[i]
            
            # ✅ ICT-BASED FVG THRESHOLD
            gap_threshold = df['atr'].iloc[i] * 0.3
            
            # FVG Bullish: gap up
            if prev2['low'] > curr['high'] and (prev2['low'] - curr['high']) >= gap_threshold:
                # ✅ CHECK IF FVG IS IN PREMIUM/DISCOUNT ZONE
                fvg_mid = (prev2['low'] + curr['high']) / 2
                zone = self.get_price_zone(fvg_mid, df.iloc[i])
                
                fvgs.append({
                    'type': 'bullish',
                    'start': curr['high'],
                    'end': prev2['low'],
                    'index': i,
                    'timestamp': curr['timestamp'],
                    'size': prev2['low'] - curr['high'],
                    'zone': zone,
                    'mitigated': False
                })
            # FVG Bearish: gap down
            elif prev2['high'] < curr['low'] and (curr['low'] - prev2['high']) >= gap_threshold:
                fvg_mid = (prev2['high'] + curr['low']) / 2
                zone = self.get_price_zone(fvg_mid, df.iloc[i])
                
                fvgs.append({
                    'type': 'bearish',
                    'start': prev2['high'],
                    'end': curr['low'],
                    'index': i,
                    'timestamp': curr['timestamp'],
                    'size': curr['low'] - prev2['high'],
                    'zone': zone,
                    'mitigated': False
                })
        return fvgs

    def get_price_zone(self, price, candle_data):
        """Determine if price is in premium, discount, or fair value zone"""
        try:
            vwap = candle_data.get('vwap', candle_data['close'])
            atr = candle_data.get('atr', 0.001)
            
            premium_threshold = vwap + (atr * 0.618)
            discount_threshold = vwap - (atr * 0.618)
            
            if price > premium_threshold:
                return 'PREMIUM'
            elif price < discount_threshold:
                return 'DISCOUNT'
            else:
                return 'FAIR_VALUE'
        except:
            return 'FAIR_VALUE'

    def ob_overlaps_fvg(self, ob, fvgs):
        """Enhanced FVG overlap detection with ICT concepts"""
        for fvg in fvgs:
            if ob['type'] == 'BULLISH' and fvg['type'] == 'bullish':
                # ✅ ICT-BASED OVERLAP LOGIC
                tolerance = abs(ob['entry_price'] - fvg['start']) * 0.05
                if (fvg['start'] - tolerance) <= ob['entry_price'] <= (fvg['end'] + tolerance):
                    # Check if FVG is in optimal zone
                    if fvg['zone'] in ['DISCOUNT', 'FAIR_VALUE']:
                        return True
            elif ob['type'] == 'BEARISH' and fvg['type'] == 'bearish':
                tolerance = abs(ob['entry_price'] - fvg['start']) * 0.05
                if (fvg['end'] - tolerance) <= ob['entry_price'] <= (fvg['start'] + tolerance):
                    if fvg['zone'] in ['PREMIUM', 'FAIR_VALUE']:
                        return True
        return False

    def is_displacement_candle(self, candle):
        """Enhanced displacement candle detection"""
        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']
        
        if total_range == 0:
            return False
            
        body_percentage = body / total_range
        volume_spike = candle.get('institutional_volume', 0) > 0
        
        # ✅ ICT DISPLACEMENT CRITERIA
        return body_percentage >= 0.45 or volume_spike

    def detect_liquidity_sweep(self, df, index):
        """Enhanced liquidity sweep detection with ICT concepts"""
        if index < 5:
            return False
            
        recent_data = df.iloc[index-8:index]
        current_candle = df.iloc[index]
        
        recent_high = recent_data['high'].max()
        recent_low = recent_data['low'].min()
        
        # ✅ ICT LIQUIDITY SWEEP THRESHOLD
        atr_value = df['atr'].iloc[index]
        sweep_threshold = atr_value * 0.3
        
        swept_high = current_candle['high'] > (recent_high + sweep_threshold)
        swept_low = current_candle['low'] < (recent_low - sweep_threshold)
        
        # ✅ CHECK FOR INSTITUTIONAL VOLUME
        institutional_activity = current_candle.get('institutional_volume', 0) > 0
        
        return (swept_high or swept_low) and institutional_activity

    def calculate_sl_tp_levels(self, ob_candle, ob_type):
        """Enhanced SL/TP calculation with ICT concepts"""
        try:
            if ob_type == 'BULLISH':
                entry = ob_candle['open']
                # ✅ ICT-BASED SL: Below order block low
                sl = ob_candle['low'] * 0.9985
                risk = entry - sl
                
                # ✅ ICT TARGETS: Based on ATR and market structure
                atr = ob_candle.get('atr', 0.001)
                tp1 = entry + (risk * 1.2)  # First target
                tp2 = entry + (atr * 2.0)   # Second target based on ATR
                
            else:  # BEARISH
                entry = ob_candle['open']
                sl = ob_candle['high'] * 1.0015
                risk = sl - entry
                
                atr = ob_candle.get('atr', 0.001)
                tp1 = entry - (risk * 1.2)
                tp2 = entry - (atr * 2.0)

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
        """Enhanced Order Block detection with ICT concepts"""
        try:
            self.symbol = symbol
            df = self.get_ohlcv(symbol)
            
            if df.empty:
                logger.warning(f"No data received for {symbol}")
                return []

            order_blocks = []
            fvgs = self.find_fvg(df)
            
            for i in range(5, len(df) - 1):
                current = df.iloc[i]
                next_candle = df.iloc[i + 1]
                
                # ✅ ENHANCED ICT CRITERIA
                has_sweep = self.detect_liquidity_sweep(df, i)
                is_institutional = current.get('institutional_volume', 0) > 0
                price_zone = self.get_price_zone(current['close'], current)
                
                # ✅ TREND CONFIRMATION WITH ICT CONCEPTS
                trend_bullish = (current['close'] > df['ema_20'].iloc[i] and 
                               current['close'] > df['vwap'].iloc[i])
                trend_bearish = (current['close'] < df['ema_20'].iloc[i] and 
                               current['close'] < df['vwap'].iloc[i])
                
                # BULLISH Order Block - Enhanced ICT criteria
                if (current['close'] > current['open'] and
                    (current['close'] - current['open']) > df['atr'].iloc[i] * 0.3 and
                    trend_bullish):
                    
                    levels = self.calculate_sl_tp_levels(current, 'BULLISH')
                    if not levels:
                        continue
                    
                    # ✅ ICT-BASED STRENGTH CALCULATION
                    strength = self.calculate_ict_strength(current, 'BULLISH', has_sweep, is_institutional, price_zone)
                    
                    ob = {
                        'pair': symbol,
                        'type': 'BULLISH',
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
                        'strength': strength,
                        'candle_data': current,
                        'has_sweep': has_sweep,
                        'is_institutional': is_institutional,
                        'price_zone': price_zone,
                        'ict_quality': self.calculate_ict_quality(current, 'BULLISH')
                    }
                    
                    # ✅ ICT-BASED VALIDATION
                    if self.validate_ict_order_block(ob, fvgs):
                        order_blocks.append(ob)

                # BEARISH Order Block - Enhanced ICT criteria
                elif (current['close'] < current['open'] and
                      (current['open'] - current['close']) > df['atr'].iloc[i] * 0.3 and
                      trend_bearish):
                    
                    levels = self.calculate_sl_tp_levels(current, 'BEARISH')
                    if not levels:
                        continue
                    
                    strength = self.calculate_ict_strength(current, 'BEARISH', has_sweep, is_institutional, price_zone)
                    
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
                        'strength': strength,
                        'candle_data': current,
                        'has_sweep': has_sweep,
                        'is_institutional': is_institutional,
                        'price_zone': price_zone,
                        'ict_quality': self.calculate_ict_quality(current, 'BEARISH')
                    }
                    
                    if self.validate_ict_order_block(ob, fvgs):
                        order_blocks.append(ob)

            logger.info(f"Found {len(order_blocks)} ICT order blocks for {symbol}")
            return order_blocks
            
        except Exception as e:
            logger.error(f"Order block finding error for {symbol}: {e}")
            return []

    def calculate_ict_strength(self, candle, ob_type, has_sweep, is_institutional, price_zone):
        """Calculate ICT-based signal strength"""
        base_strength = 60
        
        # Liquidity sweep bonus
        if has_sweep:
            base_strength += 15
        
        # Institutional activity bonus
        if is_institutional:
            base_strength += 10
        
        # Price zone bonus
        if ob_type == 'BULLISH' and price_zone == 'DISCOUNT':
            base_strength += 10
        elif ob_type == 'BEARISH' and price_zone == 'PREMIUM':
            base_strength += 10
        
        # Volume confirmation
        volume_ratio = candle['volume'] / candle.get('volume_profile', candle['volume'])
        if volume_ratio > 1.5:
            base_strength += 5
        
        return min(100, base_strength)

    def calculate_ict_quality(self, candle, ob_type):
        """Calculate ICT quality score"""
        quality = 0
        
        # Body size quality
        body_size = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']
        if total_range > 0:
            body_ratio = body_size / total_range
            if body_ratio > 0.6:
                quality += 30
            elif body_ratio > 0.4:
                quality += 20
        
        # Volume quality
        if candle.get('institutional_volume', 0) > 0:
            quality += 25
        
        # Price zone quality
        price_zone = self.get_price_zone(candle['close'], candle)
        if (ob_type == 'BULLISH' and price_zone == 'DISCOUNT') or \
           (ob_type == 'BEARISH' and price_zone == 'PREMIUM'):
            quality += 25
        
        # VWAP alignment
        if abs(candle['close'] - candle.get('vwap', candle['close'])) < candle.get('atr', 0.001):
            quality += 20
        
        return min(100, quality)

    def validate_ict_order_block(self, ob, fvgs):
        """Enhanced ICT validation for order blocks"""
        try:
            # Basic size validation
            if ob['size'] < self.ict_rules['ob_validation']['min_size']:
                return False
            
            # Age validation
            now = datetime.utcnow()
            if isinstance(ob['created_at'], str):
                ob_time = datetime.fromisoformat(ob['created_at'])
            else:
                ob_time = ob['created_at']
            
            age = (now - ob_time).total_seconds() / 3600
            if age > self.ict_rules['ob_validation']['max_age']:
                return False
            
            # ICT-specific validations
            if ob['ict_quality'] < 50:  # Minimum ICT quality
                return False
            
            # FVG overlap (optional but preferred)
            if len(fvgs) > 0 and not self.ob_overlaps_fvg(ob, fvgs):
                # Still valid but lower priority
                ob['strength'] = max(50, ob['strength'] - 10)
            
            return True
            
        except Exception as e:
            logger.error(f"ICT validation error: {e}")
            return False

    def find_optimal_trade_entry(self, ob, df):
        """Find optimal trade entry based on ICT concepts"""
        try:
            entry_price = ob['entry_price']
            ob_type = ob['type']
            
            # ✅ ICT OPTIMAL TRADE ENTRY CRITERIA
            optimal_entries = []
            
            # 1. Order Block Retest
            retest_entry = self.find_ob_retest(ob, df)
            if retest_entry:
                optimal_entries.append({
                    'type': 'OB_RETEST',
                    'price': retest_entry,
                    'confidence': 85
                })
            
            # 2. Fair Value Gap Entry
            fvg_entry = self.find_fvg_entry(ob, df)
            if fvg_entry:
                optimal_entries.append({
                    'type': 'FVG_ENTRY',
                    'price': fvg_entry,
                    'confidence': 80
                })
            
            # 3. Liquidity Sweep Entry
            sweep_entry = self.find_sweep_entry(ob, df)
            if sweep_entry:
                optimal_entries.append({
                    'type': 'SWEEP_ENTRY',
                    'price': sweep_entry,
                    'confidence': 90
                })
            
            # Return best entry
            if optimal_entries:
                best_entry = max(optimal_entries, key=lambda x: x['confidence'])
                return best_entry
            
            return None
            
        except Exception as e:
            logger.error(f"Optimal entry finding error: {e}")
            return None

    def find_ob_retest(self, ob, df):
        """Find order block retest entry"""
        try:
            ob_price = ob['entry_price']
            ob_type = ob['type']
            
            # Look for retest in recent candles
            for i in range(len(df) - 10, len(df)):
                candle = df.iloc[i]
                
                if ob_type == 'BULLISH':
                    # Price touches order block area
                    if (candle['low'] <= ob_price * 1.001 and 
                        candle['high'] >= ob_price * 0.999):
                        return ob_price
                else:  # BEARISH
                    if (candle['high'] >= ob_price * 0.999 and 
                        candle['low'] <= ob_price * 1.001):
                        return ob_price
            
            return None
            
        except Exception as e:
            logger.error(f"OB retest error: {e}")
            return None

    def find_fvg_entry(self, ob, df):
        """Find FVG-based entry"""
        try:
            fvgs = self.find_fvg(df)
            
            for fvg in fvgs:
                if ob['type'] == 'BULLISH' and fvg['type'] == 'bullish':
                    if fvg['zone'] == 'DISCOUNT':
                        return fvg['start']  # Enter at FVG start
                elif ob['type'] == 'BEARISH' and fvg['type'] == 'bearish':
                    if fvg['zone'] == 'PREMIUM':
                        return fvg['start']
            
            return None
            
        except Exception as e:
            logger.error(f"FVG entry error: {e}")
            return None

    def find_sweep_entry(self, ob, df):
        """Find liquidity sweep entry"""
        try:
            ob_price = ob['entry_price']
            ob_type = ob['type']
            
            # Look for recent sweep
            for i in range(len(df) - 5, len(df)):
                if self.detect_liquidity_sweep(df, i):
                    candle = df.iloc[i]
                    
                    if ob_type == 'BULLISH':
                        # Sweep below OB, then bounce
                        if (candle['low'] < ob_price * 0.995 and 
                            candle['close'] > ob_price * 0.998):
                            return ob_price
                    else:  # BEARISH
                        if (candle['high'] > ob_price * 1.005 and 
                            candle['close'] < ob_price * 1.002):
                            return ob_price
            
            return None
            
        except Exception as e:
            logger.error(f"Sweep entry error: {e}")
            return None

    def validate_order_blocks(self, obs):
        """Enhanced validation with ICT concepts"""
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
                
                # ✅ ENHANCED ICT VALIDATION
                if ob['size'] < self.ict_rules['ob_validation']['min_size']:
                    continue
                if age > self.ict_rules['ob_validation']['max_age']:
                    continue
                if ob['sweep_percentage'] < self.ict_rules['ob_validation']['clean_sweep']:
                    continue
                if ob['ict_quality'] < 50:  # Minimum ICT quality
                    continue
                    
                valid_obs.append(ob)
            except Exception as e:
                logger.error(f"Error validating order block: {e}")
                continue
                
        return valid_obs

    def validate_bos(self, ob):
        """Enhanced BOS validation with ICT concepts"""
        return (ob['bos_strength'] >= self.ict_rules['bos_validation']['min_strength'] and
                ob.get('retest_confirmed', False))

    def check_mitigation(self, ob):
        """Enhanced mitigation check with ICT concepts"""
        if not self.ict_rules['mitigation']['required']:
            return True
        if ob['mitigation_depth'] > self.ict_rules['mitigation']['max_depth']:
            return False
        if ob['mitigation_volume'] < self.ict_rules['mitigation']['min_volume']:
            return False
        if self.ict_rules['mitigation']['fair_value_gap'] and not ob.get('fvg_mitigated', False):
            return False
        return True

    def in_killzone(self):
        """Enhanced ICT killzone detection"""
        now = datetime.utcnow().time()
        
        # ✅ ICT KILLZONES WITH PRIORITY
        london_kz = time(6, 0) <= now <= time(11, 0)   # London Session
        ny_kz = time(12, 0) <= now <= time(17, 0)      # NY Session
        asian_kz = time(23, 0) <= now or now <= time(2, 0)  # Asian Session
        
        # Return priority level
        if london_kz or ny_kz:
            return "HIGH"  # High priority killzone
        elif asian_kz:
            return "MEDIUM"  # Medium priority killzone
        else:
            return "LOW"  # Low priority (outside killzone)

    def get_multiple_timeframes(self, symbol):
        """Enhanced multi-timeframe ICT analysis"""
        timeframes = ['5m', '15m', '1h']
        signals_count = 0
        total_quality = 0
        
        for tf in timeframes:
            df = self.get_ohlcv(symbol, interval=tf, limit=100)
            if not df.empty:
                obs = self.find_order_blocks(symbol)
                valid_obs = self.validate_order_blocks(obs)
                
                for ob in valid_obs:
                    signals_count += 1
                    total_quality += ob.get('ict_quality', 50)
        
        avg_quality = total_quality / max(1, signals_count)
        return signals_count > 0 and avg_quality > 60

    def find_signals(self, bias, symbol):
        """Enhanced ICT signal generation"""
        try:
            signals = []
            
            # ✅ ENHANCED ICT SIGNAL GENERATION
            killzone_priority = self.in_killzone()
            
            # Find and validate order blocks
            obs = self.find_order_blocks(symbol)
            valid_obs = self.validate_order_blocks(obs)
            
            # ✅ ICT-BASED PRIORITIZATION
            premium_obs = []
            standard_obs = []
            
            for ob in valid_obs:
                if self.validate_bos(ob) and self.check_mitigation(ob):
                    # Premium ICT criteria
                    if (ob['has_sweep'] and 
                        ob['is_institutional'] and 
                        ob['ict_quality'] > 75 and
                        killzone_priority in ['HIGH', 'MEDIUM']):
                        premium_obs.append(ob)
                    else:
                        standard_obs.append(ob)
            
            # Create signals from premium obs first
            for ob in premium_obs:
                signal = self.create_enhanced_signal(ob, bias)
                if signal:
                    signal.priority = "PREMIUM"
                    signals.append(signal)
                    logger.info(f"PREMIUM ICT Signal: {signal.direction} {signal.pair} @ {signal.entry}")
            
            # Add standard signals if needed
            if len(signals) < 3:
                for ob in standard_obs[:3-len(signals)]:
                    signal = self.create_enhanced_signal(ob, bias)
                    if signal:
                        signal.priority = "STANDARD"
                        signals.append(signal)
                        logger.info(f"STANDARD ICT Signal: {signal.direction} {signal.pair} @ {signal.entry}")
            
            logger.info(f"Total ICT signals generated: {len(signals)}")
            return signals
            
        except Exception as e:
            logger.error(f"ICT signal finding error for {symbol}: {e}")
            return []

    def create_enhanced_signal(self, ob, bias):
        """Create enhanced ICT trading signal"""
        try:
            levels = self.calculate_sl_tp_levels(ob['candle_data'], ob['type'])
            if not levels:
                return None
                
            # ✅ ENHANCED ICT SIGNAL METRICS
            strength = ob['strength']
            ict_quality = ob['ict_quality']
            volatility = self.calculate_volatility()
            
            # Find optimal entry
            optimal_entry = self.find_optimal_trade_entry(ob, self.get_ohlcv(self.symbol))
            if optimal_entry:
                levels['entry'] = optimal_entry['price']
                strength += 10  # Bonus for optimal entry
            
            # Create enhanced signal
            from datetime import datetime
            signal = Signal(
                pair=self.symbol,
                direction=ob['type'],
                entry=levels['entry'],
                sl=levels['sl'],
                tp1=levels['tp1'],
                tp2=levels['tp2'],
                strength=strength,
                bias=bias['bias'],
                regime=bias['regime_score'],
                volatility=volatility,
                has_sweep=ob.get('has_sweep', False),
                timestamp=datetime.utcnow()
            )
            
            # Add ICT-specific attributes
            signal.ict_quality = ict_quality
            signal.is_institutional = ob.get('is_institutional', False)
            signal.price_zone = ob.get('price_zone', 'FAIR_VALUE')
            signal.killzone_priority = self.in_killzone()
            
            return signal
            
        except Exception as e:
            logger.error(f"Error creating enhanced ICT signal: {e}")
            return None

    def calculate_volatility(self):
        """Calculate market volatility for ICT analysis"""
        try:
            # Simple volatility calculation
            return 2.5  # Default moderate volatility
        except:
            return 2.0


class Signal:
    def __init__(self, pair, direction, entry, sl, tp1, tp2,
                 strength, bias, regime, volatility, has_sweep=False, timestamp=None):
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
        self.timestamp = timestamp or datetime.utcnow()  # Default to current time if not provided
        
    def is_fresh(self, max_age_minutes=5):
        """Check if signal is fresh (not too old)"""
        from datetime import datetime
        age_minutes = (datetime.utcnow() - self.timestamp).total_seconds() / 60
        return age_minutes <= max_age_minutes
        
    def get_age_minutes(self):
        """Get signal age in minutes"""
        from datetime import datetime
        return (datetime.utcnow() - self.timestamp).total_seconds() / 60

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
            'created_at': self.timestamp.isoformat()
        }

    def validate_levels(self):
        """Validate that SL and TP levels make sense"""
        if self.direction == "BUY":
            return (self.sl < self.entry < self.tp1 < self.tp2)
        else:  # SELL
            return (self.sl > self.entry > self.tp1 > self.tp2)