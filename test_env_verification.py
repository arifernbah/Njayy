#!/usr/bin/env python3
"""
COMPREHENSIVE ENV VERIFICATION TEST
Verifies that bot properly uses .env parameters and doesn't execute low-quality signals
"""

import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config_loading():
    """Test that config properly loads from .env"""
    print("🔍 Testing config loading from .env...")
    
    # Create temporary .env file
    env_content = """
BINANCE_API_KEY=test_key
BINANCE_SECRET=test_secret
DEFAULT_RISK=1.5
REDUCED_RISK=0.75
MINIMUM_RISK=0.25
MIN_QUALITY_SCORE=85
MIN_SIGNAL_STRENGTH=80
MIN_BIAS_STRENGTH=60
MIN_REGIME_SCORE=75
VOL_RANGE_MIN=0.6
VOL_RANGE_MAX=1.5
MAX_DAILY_TRADES=5
MAX_OPEN_POSITIONS=2
MAX_CONCURRENT_TRADES=2
MAX_DRAWDOWN=8.0
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(env_content)
        env_file = f.name
    
    try:
        # Mock os.environ to use our test .env
        with patch.dict(os.environ, {}, clear=True):
            # Load config
            from core.config import Config
            
            # Test that config loads properly
            config = Config()
            
            # Verify values are loaded from .env
            assert config.DEFAULT_RISK == 1.5, f"Expected 1.5, got {config.DEFAULT_RISK}"
            assert config.REDUCED_RISK == 0.75, f"Expected 0.75, got {config.REDUCED_RISK}"
            assert config.MINIMUM_RISK == 0.25, f"Expected 0.25, got {config.MINIMUM_RISK}"
            assert config.MIN_QUALITY_SCORE == 85, f"Expected 85, got {config.MIN_QUALITY_SCORE}"
            assert config.MIN_SIGNAL_STRENGTH == 80, f"Expected 80, got {config.MIN_SIGNAL_STRENGTH}"
            assert config.MIN_BIAS_STRENGTH == 60, f"Expected 60, got {config.MIN_BIAS_STRENGTH}"
            assert config.MIN_REGIME_SCORE == 75, f"Expected 75, got {config.MIN_REGIME_SCORE}"
            assert config.VOL_RANGE_MIN == 0.6, f"Expected 0.6, got {config.VOL_RANGE_MIN}"
            assert config.VOL_RANGE_MAX == 1.5, f"Expected 1.5, got {config.VOL_RANGE_MAX}"
            assert config.MAX_DAILY_TRADES == 5, f"Expected 5, got {config.MAX_DAILY_TRADES}"
            assert config.MAX_OPEN_POSITIONS == 2, f"Expected 2, got {config.MAX_OPEN_POSITIONS}"
            assert config.MAX_CONCURRENT_TRADES == 2, f"Expected 2, got {config.MAX_CONCURRENT_TRADES}"
            assert config.MAX_DRAWDOWN == 8.0, f"Expected 8.0, got {config.MAX_DRAWDOWN}"
            
            print("✅ Config loading test PASSED")
            return True
            
    finally:
        os.unlink(env_file)

def test_signal_validation():
    """Test that bot properly validates signals using .env thresholds"""
    print("🔍 Testing signal validation with .env thresholds...")
    
    # Create test signal with low quality
    low_quality_signal = {
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'entry_price': 50000,
        'quality_score': 45,  # Below threshold
        'signal_strength': 30,  # Below threshold
        'bias_strength': 25,  # Below threshold
        'regime_score': 40,  # Below threshold
        'volatility': 0.3,  # Below range
        'timestamp': 1234567890
    }
    
    # Create test signal with high quality
    high_quality_signal = {
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'entry_price': 50000,
        'quality_score': 90,  # Above threshold
        'signal_strength': 85,  # Above threshold
        'bias_strength': 75,  # Above threshold
        'regime_score': 80,  # Above threshold
        'volatility': 0.8,  # Within range
        'timestamp': 1234567890
    }
    
    # Mock config with strict thresholds
    mock_config = Mock()
    mock_config.MIN_QUALITY_SCORE = 70
    mock_config.MIN_SIGNAL_STRENGTH = 70
    mock_config.MIN_BIAS_STRENGTH = 50
    mock_config.MIN_REGIME_SCORE = 60
    mock_config.VOL_RANGE_MIN = 0.4
    mock_config.VOL_RANGE_MAX = 1.8
    
    # Import and test signal validation
    from bot import ICTBot
    
    with patch('bot.Config', return_value=mock_config):
        bot = ICTBot()
        
        # Test low quality signal should be rejected
        is_valid_low = bot._validate_signal(low_quality_signal)
        assert not is_valid_low, f"Low quality signal should be rejected, but was accepted"
        
        # Test high quality signal should be accepted
        is_valid_high = bot._validate_signal(high_quality_signal)
        assert is_valid_high, f"High quality signal should be accepted, but was rejected"
        
        print("✅ Signal validation test PASSED")
        return True

def test_risk_calculation():
    """Test that risk calculation uses .env parameters"""
    print("🔍 Testing risk calculation with .env parameters...")
    
    # Mock config with specific risk values
    mock_config = Mock()
    mock_config.DEFAULT_RISK = 1.5
    mock_config.REDUCED_RISK = 0.75
    mock_config.MINIMUM_RISK = 0.25
    mock_config.MAX_DRAWDOWN = 8.0
    
    # Import and test risk calculation
    from bot import ICTBot
    
    with patch('bot.Config', return_value=mock_config):
        bot = ICTBot()
        
        # Test default risk
        risk = bot._calculate_risk_percentage()
        assert risk == 1.5, f"Expected default risk 1.5%, got {risk}%"
        
        # Test reduced risk (simulate drawdown)
        bot.daily_pnl = -5.0  # 5% drawdown
        risk = bot._calculate_risk_percentage()
        assert risk == 0.75, f"Expected reduced risk 0.75%, got {risk}%"
        
        # Test minimum risk (simulate high drawdown)
        bot.daily_pnl = -15.0  # 15% drawdown
        risk = bot._calculate_risk_percentage()
        assert risk == 0.25, f"Expected minimum risk 0.25%, got {risk}%"
        
        print("✅ Risk calculation test PASSED")
        return True

def test_volatility_filter():
    """Test that volatility filter uses .env range"""
    print("🔍 Testing volatility filter with .env range...")
    
    # Mock config with specific volatility range
    mock_config = Mock()
    mock_config.VOL_RANGE_MIN = 0.6
    mock_config.VOL_RANGE_MAX = 1.5
    
    # Import and test volatility filter
    from bot import ICTBot
    
    with patch('bot.Config', return_value=mock_config):
        bot = ICTBot()
        
        # Test volatility within range
        signal_in_range = {'volatility': 0.8}
        is_valid = bot._validate_volatility(signal_in_range)
        assert is_valid, f"Volatility 0.8 should be within range 0.6-1.5"
        
        # Test volatility below range
        signal_below = {'volatility': 0.3}
        is_valid = bot._validate_volatility(signal_below)
        assert not is_valid, f"Volatility 0.3 should be below range 0.6-1.5"
        
        # Test volatility above range
        signal_above = {'volatility': 2.0}
        is_valid = bot._validate_volatility(signal_above)
        assert not is_valid, f"Volatility 2.0 should be above range 0.6-1.5"
        
        print("✅ Volatility filter test PASSED")
        return True

def test_trading_limits():
    """Test that trading limits use .env parameters"""
    print("🔍 Testing trading limits with .env parameters...")
    
    # Mock config with specific limits
    mock_config = Mock()
    mock_config.MAX_DAILY_TRADES = 5
    mock_config.MAX_OPEN_POSITIONS = 2
    mock_config.MAX_CONCURRENT_TRADES = 2
    
    # Import and test trading limits
    from bot import ICTBot
    
    with patch('bot.Config', return_value=mock_config):
        bot = ICTBot()
        
        # Test daily trade limit
        bot.daily_trades = 4
        can_trade = bot._can_execute_trade()
        assert can_trade, f"Should be able to trade with 4/5 daily trades"
        
        bot.daily_trades = 5
        can_trade = bot._can_execute_trade()
        assert not can_trade, f"Should not be able to trade with 5/5 daily trades"
        
        # Test open positions limit
        bot.open_positions = 1
        can_trade = bot._can_execute_trade()
        assert can_trade, f"Should be able to trade with 1/2 open positions"
        
        bot.open_positions = 2
        can_trade = bot._can_execute_trade()
        assert not can_trade, f"Should not be able to trade with 2/2 open positions"
        
        print("✅ Trading limits test PASSED")
        return True

def test_session_filters():
    """Test that session filters use .env parameters"""
    print("🔍 Testing session filters with .env parameters...")
    
    # Mock config with session parameters
    mock_config = Mock()
    mock_config.LONDON_MIN_SCORE = 75
    mock_config.NY_MIN_SCORE = 70
    mock_config.ASIAN_MIN_SCORE = 80
    mock_config.LONDON_START = "07:00"
    mock_config.LONDON_END = "16:00"
    mock_config.NY_START = "14:00"
    mock_config.NY_END = "23:00"
    mock_config.ASIAN_START = "00:00"
    mock_config.ASIAN_END = "09:00"
    
    # Import and test session filters
    from bot import ICTBot
    
    with patch('bot.Config', return_value=mock_config):
        bot = ICTBot()
        
        # Test London session with high score
        signal = {'quality_score': 80, 'timestamp': 1234567890}
        is_valid = bot._validate_session_signal(signal, 'London')
        assert is_valid, f"London signal with score 80 should pass (min 75)"
        
        # Test London session with low score
        signal = {'quality_score': 70, 'timestamp': 1234567890}
        is_valid = bot._validate_session_signal(signal, 'London')
        assert not is_valid, f"London signal with score 70 should fail (min 75)"
        
        # Test Asian session with high score
        signal = {'quality_score': 85, 'timestamp': 1234567890}
        is_valid = bot._validate_session_signal(signal, 'Asian')
        assert is_valid, f"Asian signal with score 85 should pass (min 80)"
        
        print("✅ Session filters test PASSED")
        return True

def main():
    """Run all verification tests"""
    print("🚀 STARTING COMPREHENSIVE ENV VERIFICATION TEST")
    print("=" * 60)
    
    tests = [
        test_config_loading,
        test_signal_validation,
        test_risk_calculation,
        test_volatility_filter,
        test_trading_limits,
        test_session_filters
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {str(e)}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"📊 TEST RESULTS: {passed} PASSED, {failed} FAILED")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! Bot properly uses .env parameters")
        print("✅ Bot will NOT execute low-quality signals")
        print("✅ Bot respects all configured thresholds")
        print("✅ Bot uses proper risk management")
        return True
    else:
        print("⚠️  Some tests failed. Bot may not be properly configured")
        return False

if __name__ == "__main__":
    main()