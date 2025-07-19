from datetime import datetime
from utils.logger import logger
from binance.client import Client
from core.config import config  # ✅ Fixed import path
import pandas as pd
import numpy as np

def safe_get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d

class BiasAnalyzer:
    def __init__(self):
        self.author = "arifernbah1"
        self.last_update = "2025-07-16"

        self.htf_weights = {
            "Daily": 0.5,
            "4h": 0.3,
            "1h": 0.2
        }

        self.bias_factors = {
            "trend_strength": 0.4,
            "structure": 0.3,
            "volume": 0.2,
            "momentum": 0.1
        }

        # ✅ NEW: ICT ENHANCED FEATURES
        self.ict_enhancements = {
            'vwap_analysis': True,
            'institutional_volume': True,
            'premium_discount_zones': True,
            'enhanced_structure': True
        }
        
        self.vwap_periods = [20, 50, 200]
        self.institutional_threshold = 2.0  # 2x standard deviation

        self.client = Client(api_key=config.BINANCE_API_KEY, api_secret=config.BINANCE_SECRET)

    def calculate_vwap(self, df, period=20):
        """Calculate Volume Weighted Average Price"""
        try:
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            vwap = (typical_price * df['volume']).rolling(window=period).sum() / df['volume'].rolling(window=period).sum()
            return vwap
        except Exception as e:
            logger.error(f"VWAP calculation error: {e}")
            return pd.Series([df['close'].mean()] * len(df))

    def detect_institutional_volume(self, df):
        """Detect institutional volume activity"""
        try:
            volume_ma = df['volume'].rolling(window=20).mean()
            volume_std = df['volume'].rolling(window=20).std()
            institutional_threshold = volume_ma + (volume_std * self.institutional_threshold)
            
            institutional_spikes = df['volume'] > institutional_threshold
            volume_strength = (df['volume'] - volume_ma) / volume_std
            
            return {
                'institutional_spikes': institutional_spikes,
                'volume_strength': volume_strength,
                'institutional_threshold': institutional_threshold
            }
        except Exception as e:
            logger.error(f"Institutional volume detection error: {e}")
            return None

    def analyze_premium_discount_zones(self, df):
        """Analyze premium/discount zones based on VWAP"""
        try:
            vwap = self.calculate_vwap(df, 20)
            atr = self.calculate_atr(df, 14)
            
            premium_zone_high = vwap + (atr * 0.618)
            premium_zone_low = vwap + (atr * 0.382)
            discount_zone_high = vwap - (atr * 0.382)
            discount_zone_low = vwap - (atr * 0.618)
            
            current_price = df['close'].iloc[-1]
            
            # Determine zone position
            if premium_zone_low.iloc[-1] <= current_price <= premium_zone_high.iloc[-1]:
                zone_position = "PREMIUM"
                zone_score = 80  # Higher score for premium zone
            elif discount_zone_low.iloc[-1] <= current_price <= discount_zone_high.iloc[-1]:
                zone_position = "DISCOUNT"
                zone_score = 70  # Good score for discount zone
            else:
                zone_position = "NEUTRAL"
                zone_score = 50  # Neutral score
            
            return {
                'zone_position': zone_position,
                'zone_score': zone_score,
                'vwap': vwap.iloc[-1],
                'distance_from_vwap': abs(current_price - vwap.iloc[-1]) / vwap.iloc[-1]
            }
        except Exception as e:
            logger.error(f"Premium/Discount zones analysis error: {e}")
            return {'zone_position': 'NEUTRAL', 'zone_score': 50, 'vwap': 0, 'distance_from_vwap': 0}

    def calculate_atr(self, df, period=14):
        """Calculate Average True Range"""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            return true_range.rolling(window=period).mean()
        except Exception as e:
            logger.error(f"ATR calculation error: {e}")
            return pd.Series([0.001] * len(df))

    def analyze_enhanced_structure(self, df):
        """Enhanced market structure analysis with ICT concepts"""
        try:
            if len(df) < 10:
                return 50
            
            # Basic structure analysis
            bullish_candles = (df['close'] > df['open']).sum()
            total_candles = len(df)
            bullish_percentage = (bullish_candles / total_candles) * 100
            
            # Enhanced structure with VWAP
            vwap = self.calculate_vwap(df, 20)
            price_vs_vwap = df['close'].iloc[-1] > vwap.iloc[-1]
            
            # Higher highs and higher lows analysis
            highs = df['high'].rolling(window=3).max()
            lows = df['low'].rolling(window=3).min()
            
            higher_highs = (highs.diff() > 0).sum()
            higher_lows = (lows.diff() > 0).sum()
            
            structure_score = ((higher_highs + higher_lows) / len(highs.dropna())) * 100
            
            # VWAP-based structure bonus
            vwap_bonus = 10 if price_vs_vwap else -10
            
            enhanced_score = (bullish_percentage * 0.4 + structure_score * 0.4 + vwap_bonus * 0.2)
            return min(100, max(0, enhanced_score))
            
        except Exception as e:
            logger.error(f"Enhanced structure analysis error: {e}")
            return 50

    def get_market_data(self, interval, symbol):
        """Fetch historical OHLCV data from Binance Futures"""
        try:
            interval_map = {
                "Daily": Client.KLINE_INTERVAL_1DAY,
                "4h": Client.KLINE_INTERVAL_4HOUR,
                "1h": Client.KLINE_INTERVAL_1HOUR
            }
            
            # ✅ Fixed: Remove duplicate symbol parameter
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval_map[interval],
                limit=100
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close',
                'volume', 'close_time', 'quote_asset_volume',
                'num_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            
            # ✅ Convert data types properly
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # ✅ NEW: Add ICT indicators
            if self.ict_enhancements['vwap_analysis']:
                df['vwap'] = self.calculate_vwap(df, 20)
            
            if self.ict_enhancements['institutional_volume']:
                volume_data = self.detect_institutional_volume(df)
                if volume_data:
                    df['institutional_spikes'] = volume_data['institutional_spikes']
                    df['volume_strength'] = volume_data['volume_strength']
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch market data for {symbol}: {e}")
            return pd.DataFrame()

    def analyze_bias(self, symbol):
        """Analyze overall bias across timeframes with ICT enhancements"""
        try:
            # ✅ Fixed: Pass symbol parameter to get_market_data
            daily_data = self.get_market_data("Daily", symbol)
            h4_data = self.get_market_data("4h", symbol)
            h1_data = self.get_market_data("1h", symbol)

            if daily_data.empty or h4_data.empty or h1_data.empty:
                logger.warning(f"Insufficient data for bias analysis: {symbol}")
                return {"valid": False, "symbol": symbol}

            # ✅ ENHANCED ANALYSIS WITH ICT FEATURES
            daily_score = self.analyze_timeframe_enhanced(daily_data)
            h4_score = self.analyze_timeframe_enhanced(h4_data)
            h1_score = self.analyze_timeframe_enhanced(h1_data)

            # ✅ Calculate weighted overall bias
            overall_bias = (
                daily_score * self.htf_weights["Daily"] +
                h4_score * self.htf_weights["4h"] +
                h1_score * self.htf_weights["1h"]
            )

            regime = self.analyze_regime(daily_data)
            volatility = self.calculate_volatility(h1_data)
            
            # ✅ NEW: ICT ENHANCED FEATURES
            zones_analysis = self.analyze_premium_discount_zones(daily_data)
            institutional_volume = self.detect_institutional_volume(daily_data)

            # ✅ Determine bias direction
            direction = "BULLISH" if overall_bias > 50 else "BEARISH"
            
            return {
                'symbol': symbol,
                'bias': overall_bias,
                'direction': direction,
                'valid': overall_bias > 35,
                'strength': overall_bias,
                'regime': regime,
                'regime_score': safe_get(regime, 'score', default=50),
                'volatility': volatility,
                'timeframe_scores': {
                    'daily': daily_score,
                    '4h': h4_score,
                    '1h': h1_score
                },
                # ✅ NEW: ICT ENHANCED DATA
                'zones_analysis': zones_analysis,
                'institutional_volume': institutional_volume,
                'ict_enhanced': True
            }

        except Exception as e:
            logger.error(f"Bias analysis error for {symbol}: {e}")
            return {"valid": False, "symbol": symbol}

    def analyze_timeframe(self, df):
        """Analyze bias for specific timeframe"""
        try:
            if df.empty or len(df) < 20:
                return 0
                
            trend = self.analyze_trend(df)
            structure = self.analyze_structure(df)
            volume = self.analyze_volume(df)
            momentum = self.analyze_momentum(df)

            score = (
                trend * self.bias_factors['trend_strength'] +
                structure * self.bias_factors['structure'] +
                volume * self.bias_factors['volume'] +
                momentum * self.bias_factors['momentum']
            )
            
            return min(100, max(0, score))  # ✅ Ensure score is between 0-100
            
        except Exception as e:
            logger.error(f"Timeframe analysis error: {e}")
            return 0

    def analyze_trend(self, df):
        """Analyze trend strength using moving averages"""
        try:
            if len(df) < 20:
                return 50
                
            close = df['close']
            sma_5 = close.rolling(window=5).mean()
            sma_20 = close.rolling(window=20).mean()
            
            if pd.isna(sma_5.iloc[-1]) or pd.isna(sma_20.iloc[-1]):
                return 50
                
            # ✅ More nuanced trend analysis
            current_price = close.iloc[-1]
            sma5_current = sma_5.iloc[-1]
            sma20_current = sma_20.iloc[-1]
            
            if sma5_current > sma20_current:
                # Bullish trend
                strength = min(100, ((sma5_current - sma20_current) / sma20_current) * 1000 + 60)
            else:
                # Bearish trend
                strength = max(0, 40 - ((sma20_current - sma5_current) / sma20_current) * 1000)
            
            return strength
            
        except Exception as e:
            logger.error(f"Trend analysis error: {e}")
            return 50

    def analyze_structure(self, df):
        """Analyze market structure (higher highs/lower lows)"""
        try:
            if len(df) < 10:
                return 50
                
            # ✅ Count bullish vs bearish candles
            bullish_candles = (df['close'] > df['open']).sum()
            total_candles = len(df)
            
            # ✅ Check for higher highs and higher lows (bullish structure)
            highs = df['high'].rolling(window=3).max()
            lows = df['low'].rolling(window=3).min()
            
            higher_highs = (highs.diff() > 0).sum()
            higher_lows = (lows.diff() > 0).sum()
            
            # Combine metrics
            bullish_percentage = (bullish_candles / total_candles) * 100
            structure_score = ((higher_highs + higher_lows) / len(highs.dropna())) * 100
            
            return (bullish_percentage * 0.6 + structure_score * 0.4)
            
        except Exception as e:
            logger.error(f"Structure analysis error: {e}")
            return 50

    def analyze_volume(self, df):
        """Analyze volume trends"""
        try:
            if len(df) < 20:
                return 50
                
            vol = df['volume']
            if vol.empty:
                return 50
                
            recent_volume = vol.iloc[-5:].mean()  # ✅ Use last 5 candles average
            avg_volume = vol.rolling(window=20).mean().iloc[-1]
            
            if pd.isna(recent_volume) or pd.isna(avg_volume) or avg_volume == 0:
                return 50
                
            volume_ratio = recent_volume / avg_volume
            
            # ✅ Convert to 0-100 scale
            if volume_ratio > 1.5:
                return 100
            elif volume_ratio > 1.2:
                return 80
            elif volume_ratio > 1.0:
                return 60
            elif volume_ratio > 0.8:
                return 40
            else:
                return 20
                
        except Exception as e:
            logger.error(f"Volume analysis error: {e}")
            return 50

    def analyze_momentum(self, df):
        """Analyze price momentum"""
        try:
            if len(df) < 5:
                return 50
                
            close = df['close']
            
            # ✅ Calculate momentum using multiple periods
            momentum_1 = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
            momentum_3 = (close.iloc[-1] - close.iloc[-4]) / close.iloc[-4] * 100
            momentum_5 = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] * 100 if len(close) >= 6 else 0
            
            # ✅ Weighted momentum score
            momentum_score = (momentum_1 * 0.5 + momentum_3 * 0.3 + momentum_5 * 0.2)
            
            # ✅ Convert to 0-100 scale
            if momentum_score > 2:
                return 100
            elif momentum_score > 1:
                return 80
            elif momentum_score > 0:
                return 60
            elif momentum_score > -1:
                return 40
            elif momentum_score > -2:
                return 20
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Momentum analysis error: {e}")
            return 50

    def analyze_regime(self, df):
        """Analyze market regime (trending vs ranging)"""
        try:
            if len(df) < 20:
                return {"type": "UNKNOWN", "score": 50, "confidence": "LOW"}
                
            # ✅ Fixed syntax error: remove '=' assignment
            high_5 = df['high'].rolling(window=5).max()
            low_5 = df['low'].rolling(window=5).min()
            range_val = high_5 - low_5
            
            if range_val.empty:
                return {"type": "UNKNOWN", "score": 50, "confidence": "LOW"}
                
            avg_range = range_val.mean()
            current_range = range_val.iloc[-1]
            
            # ✅ Calculate volatility properly
            price_changes = df['close'].pct_change().dropna()
            volatility = price_changes.std() if not price_changes.empty else 0
            
            # ✅ Determine regime
            if pd.isna(avg_range) or pd.isna(current_range):
                return {"type": "UNKNOWN", "score": 50, "confidence": "LOW"}
                
            # ✅ Trending if current volatility is high
            trending = volatility > 0.02  # 2% daily volatility threshold
            
            if trending:
                confidence = "HIGH" if volatility > 0.03 else "MEDIUM"
                score = min(100, max(60, volatility * 2000))  # Scale volatility to score
            else:
                confidence = "MEDIUM"
                score = 40
                
            return {
                "type": "TRENDING" if trending else "RANGING",
                "score": score,
                "confidence": confidence,
                "volatility": volatility
            }
            
        except Exception as e:
            logger.error(f"Regime analysis error: {e}")
            return {"type": "UNKNOWN", "score": 50, "confidence": "LOW"}

    def calculate_volatility(self, df):
        """Calculate price volatility"""
        try:
            if df.empty or len(df) < 2:
                return 0
                
            returns = df['close'].pct_change().dropna()
            if returns.empty:
                return 0
                
            volatility = returns.std() * 100  # Convert to percentage
            return round(volatility, 2)
            
        except Exception as e:
            logger.error(f"Volatility calculation error: {e}")
            return 0

    def analyze_volume_enhanced(self, df):
        """Enhanced volume analysis with institutional detection"""
        try:
            if len(df) < 20:
                return 50
                
            vol = df['volume']
            if vol.empty:
                return 50
                
            # Basic volume analysis
            recent_volume = vol.iloc[-5:].mean()
            avg_volume = vol.rolling(window=20).mean().iloc[-1]
            
            if pd.isna(recent_volume) or pd.isna(avg_volume) or avg_volume == 0:
                return 50
                
            volume_ratio = recent_volume / avg_volume
            
            # ✅ ENHANCED: Institutional volume detection
            institutional_bonus = 0
            if 'volume_strength' in df.columns:
                current_volume_strength = df['volume_strength'].iloc[-1]
                if current_volume_strength > 2.0:  # Strong institutional activity
                    institutional_bonus = 20
                elif current_volume_strength > 1.5:  # Moderate institutional activity
                    institutional_bonus = 10
            
            # ✅ ENHANCED: VWAP-based volume analysis
            vwap_bonus = 0
            if 'vwap' in df.columns:
                current_price = df['close'].iloc[-1]
                vwap = df['vwap'].iloc[-1]
                if abs(current_price - vwap) / vwap < 0.01:  # Close to VWAP
                    vwap_bonus = 10
            
            # Calculate enhanced score
            base_score = 0
            if volume_ratio > 1.5:
                base_score = 100
            elif volume_ratio > 1.2:
                base_score = 80
            elif volume_ratio > 1.0:
                base_score = 60
            elif volume_ratio > 0.8:
                base_score = 40
            else:
                base_score = 20
            
            enhanced_score = min(100, base_score + institutional_bonus + vwap_bonus)
            return enhanced_score
                
        except Exception as e:
            logger.error(f"Enhanced volume analysis error: {e}")
            return 50

    def analyze_timeframe_enhanced(self, df):
        """Enhanced timeframe analysis with ICT concepts"""
        try:
            if df.empty or len(df) < 20:
                return 0
                
            trend = self.analyze_trend(df)
            structure = self.analyze_enhanced_structure(df)  # Use enhanced structure
            volume = self.analyze_volume_enhanced(df)  # Use enhanced volume
            momentum = self.analyze_momentum(df)

            score = (
                trend * self.bias_factors['trend_strength'] +
                structure * self.bias_factors['structure'] +
                volume * self.bias_factors['volume'] +
                momentum * self.bias_factors['momentum']
            )
            
            return min(100, max(0, score))  # ✅ Ensure score is between 0-100
            
        except Exception as e:
            logger.error(f"Enhanced timeframe analysis error: {e}")
            return 0

    def get_bias_summary(self, symbol):
        """Get comprehensive bias summary"""
        try:
            bias_data = self.analyze_bias(symbol)
            
            if not safe_get(bias_data, 'valid', default=False):
                return f"❌ {symbol}: Insufficient data for analysis"
                
            summary = f"""
📊 **BIAS ANALYSIS - {symbol}**

🎯 **Overall Bias**: {safe_get(bias_data, 'direction', default='N/A')} ({safe_get(bias_data, 'strength', default=50):.1f}/100)
📊 **Regime**: {safe_get(bias_data, 'regime', {}).get('type', 'UNKNOWN')} ({safe_get(bias_data, 'regime_score', default=50):.1f}/100)
📊 **Volatility**: {safe_get(bias_data, 'volatility', default=1.0)}%

**Timeframe Breakdown:**
• Daily: {safe_get(bias_data, 'timeframe_scores', default={})['daily']:.1f}
• 4H: {safe_get(bias_data, 'timeframe_scores', default={})['4h']:.1f}
• 1H: {safe_get(bias_data, 'timeframe_scores', default={})['1h']:.1f}

**Status**: {'✅ Valid' if safe_get(bias_data, 'valid', default=False) else '❌ Invalid'}
"""
            return summary
            
        except Exception as e:
            logger.error(f"Bias summary error: {e}")
            return f"❌ {symbol}: Error generating summary"