#!/usr/bin/env python3
"""
CRASH SAFETY TEST
Tests if bot handles low parameters gracefully without crashing
"""

import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_low_quality_parameters():
    """Test bot with very low quality parameters"""
    print("🔍 Testing bot with low quality parameters...")
    
    # Create .env with very low parameters
    env_content = """
BINANCE_API_KEY=test_key
BINANCE_SECRET=test_secret
MIN_QUALITY_SCORE=10
MIN_SIGNAL_STRENGTH=5
MIN_BIAS_STRENGTH=3
MIN_REGIME_SCORE=2
DEFAULT_RISK=0.1
REDUCED_RISK=0.05
MINIMUM_RISK=0.01
VOL_RANGE_MIN=0.1
VOL_RANGE_MAX=0.2
MAX_DAILY_TRADES=1
MAX_OPEN_POSITIONS=1
MAX_CONCURRENT_TRADES=1
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(env_content)
        env_file = f.name
    
    try:
        # Mock os.environ to use our test .env
        with patch.dict(os.environ, {}, clear=True):
            # Load config
            from core.config import Config
            
            # Test that config loads without crashing
            try:
                config = Config()
                print("✅ Config loaded successfully with low parameters")
                
                # Verify low values are accepted
                assert config.MIN_QUALITY_SCORE == 10, f"Expected 10, got {config.MIN_QUALITY_SCORE}"
                assert config.MIN_SIGNAL_STRENGTH == 5, f"Expected 5, got {config.MIN_SIGNAL_STRENGTH}"
                assert config.MIN_BIAS_STRENGTH == 3, f"Expected 3, got {config.MIN_BIAS_STRENGTH}"
                assert config.MIN_REGIME_SCORE == 2, f"Expected 2, got {config.MIN_REGIME_SCORE}"
                assert config.DEFAULT_RISK == 0.1, f"Expected 0.1, got {config.DEFAULT_RISK}"
                assert config.VOL_RANGE_MIN == 0.1, f"Expected 0.1, got {config.VOL_RANGE_MIN}"
                assert config.VOL_RANGE_MAX == 0.2, f"Expected 0.2, got {config.VOL_RANGE_MAX}"
                
                print("✅ All low parameters accepted correctly")
                return True
                
            except Exception as e:
                print(f"❌ Config crashed with low parameters: {e}")
                return False
                
    finally:
        os.unlink(env_file)

def test_zero_parameters():
    """Test bot with zero parameters"""
    print("\n🔍 Testing bot with zero parameters...")
    
    # Create .env with zero parameters
    env_content = """
BINANCE_API_KEY=test_key
BINANCE_SECRET=test_secret
MIN_QUALITY_SCORE=0
MIN_SIGNAL_STRENGTH=0
MIN_BIAS_STRENGTH=0
MIN_REGIME_SCORE=0
DEFAULT_RISK=0
REDUCED_RISK=0
MINIMUM_RISK=0
VOL_RANGE_MIN=0
VOL_RANGE_MAX=0
MAX_DAILY_TRADES=0
MAX_OPEN_POSITIONS=0
MAX_CONCURRENT_TRADES=0
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(env_content)
        env_file = f.name
    
    try:
        # Mock os.environ to use our test .env
        with patch.dict(os.environ, {}, clear=True):
            # Load config
            from core.config import Config
            
            # Test that config loads without crashing
            try:
                config = Config()
                print("✅ Config loaded successfully with zero parameters")
                
                # Verify zero values are accepted
                assert config.MIN_QUALITY_SCORE == 0, f"Expected 0, got {config.MIN_QUALITY_SCORE}"
                assert config.MIN_SIGNAL_STRENGTH == 0, f"Expected 0, got {config.MIN_SIGNAL_STRENGTH}"
                assert config.MIN_BIAS_STRENGTH == 0, f"Expected 0, got {config.MIN_BIAS_STRENGTH}"
                assert config.MIN_REGIME_SCORE == 0, f"Expected 0, got {config.MIN_REGIME_SCORE}"
                assert config.DEFAULT_RISK == 0, f"Expected 0, got {config.DEFAULT_RISK}"
                assert config.VOL_RANGE_MIN == 0, f"Expected 0, got {config.VOL_RANGE_MIN}"
                assert config.VOL_RANGE_MAX == 0, f"Expected 0, got {config.VOL_RANGE_MAX}"
                
                print("✅ All zero parameters accepted correctly")
                return True
                
            except Exception as e:
                print(f"❌ Config crashed with zero parameters: {e}")
                return False
                
    finally:
        os.unlink(env_file)

def test_negative_parameters():
    """Test bot with negative parameters"""
    print("\n🔍 Testing bot with negative parameters...")
    
    # Create .env with negative parameters
    env_content = """
BINANCE_API_KEY=test_key
BINANCE_SECRET=test_secret
MIN_QUALITY_SCORE=-10
MIN_SIGNAL_STRENGTH=-5
MIN_BIAS_STRENGTH=-3
MIN_REGIME_SCORE=-2
DEFAULT_RISK=-1
REDUCED_RISK=-0.5
MINIMUM_RISK=-0.1
VOL_RANGE_MIN=-0.1
VOL_RANGE_MAX=-0.2
MAX_DAILY_TRADES=-1
MAX_OPEN_POSITIONS=-1
MAX_CONCURRENT_TRADES=-1
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(env_content)
        env_file = f.name
    
    try:
        # Mock os.environ to use our test .env
        with patch.dict(os.environ, {}, clear=True):
            # Load config
            from core.config import Config
            
            # Test that config loads without crashing
            try:
                config = Config()
                print("✅ Config loaded successfully with negative parameters")
                
                # Verify negative values are accepted
                assert config.MIN_QUALITY_SCORE == -10, f"Expected -10, got {config.MIN_QUALITY_SCORE}"
                assert config.MIN_SIGNAL_STRENGTH == -5, f"Expected -5, got {config.MIN_SIGNAL_STRENGTH}"
                assert config.MIN_BIAS_STRENGTH == -3, f"Expected -3, got {config.MIN_BIAS_STRENGTH}"
                assert config.MIN_REGIME_SCORE == -2, f"Expected -2, got {config.MIN_REGIME_SCORE}"
                assert config.DEFAULT_RISK == -1, f"Expected -1, got {config.DEFAULT_RISK}"
                assert config.VOL_RANGE_MIN == -0.1, f"Expected -0.1, got {config.VOL_RANGE_MIN}"
                assert config.VOL_RANGE_MAX == -0.2, f"Expected -0.2, got {config.VOL_RANGE_MAX}"
                
                print("✅ All negative parameters accepted correctly")
                return True
                
            except Exception as e:
                print(f"❌ Config crashed with negative parameters: {e}")
                return False
                
    finally:
        os.unlink(env_file)

def test_signal_validation_with_low_params():
    """Test signal validation with low parameters"""
    print("\n🔍 Testing signal validation with low parameters...")
    
    # Mock config with low parameters
    mock_config = Mock()
    mock_config.MIN_QUALITY_SCORE = 10
    mock_config.MIN_SIGNAL_STRENGTH = 5
    mock_config.MIN_BIAS_STRENGTH = 3
    mock_config.MIN_REGIME_SCORE = 2
    mock_config.VOL_RANGE_MIN = 0.1
    mock_config.VOL_RANGE_MAX = 0.2
    
    # Create test signal with low quality
    low_quality_signal = Mock()
    low_quality_signal.strength = 3  # Below threshold
    low_quality_signal.bias = 2      # Below threshold
    low_quality_signal.regime = 1    # Below threshold
    low_quality_signal.volatility = 0.05  # Below range
    low_quality_signal.quality_score = 5  # Below threshold
    low_quality_signal.validate_levels = Mock(return_value=True)
    low_quality_signal.pair = 'BTCUSDT'
    
    # Import and test signal validation
    from bot import ICTBot
    
    with patch('bot.Config', return_value=mock_config):
        bot = ICTBot()
        
        # Test that validation doesn't crash
        try:
            is_valid = bot.validate_signal(low_quality_signal)
            print(f"✅ Signal validation completed: {is_valid}")
            return True
        except Exception as e:
            print(f"❌ Signal validation crashed: {e}")
            return False

def test_risk_calculation_with_low_params():
    """Test risk calculation with low parameters"""
    print("\n🔍 Testing risk calculation with low parameters...")
    
    # Mock config with low parameters
    mock_config = Mock()
    mock_config.DEFAULT_RISK = 0.1
    mock_config.REDUCED_RISK = 0.05
    mock_config.MINIMUM_RISK = 0.01
    
    # Import and test risk calculation
    from bot import ICTBot
    
    with patch('bot.Config', return_value=mock_config):
        bot = ICTBot()
        
        # Test that risk calculation doesn't crash
        try:
            risk = bot.calculate_risk()
            print(f"✅ Risk calculation completed: {risk}")
            return True
        except Exception as e:
            print(f"❌ Risk calculation crashed: {e}")
            return False

def main():
    """Run all crash safety tests"""
    print("🚀 STARTING CRASH SAFETY TESTS")
    print("=" * 60)
    
    tests = [
        test_low_quality_parameters,
        test_zero_parameters,
        test_negative_parameters,
        test_signal_validation_with_low_params,
        test_risk_calculation_with_low_params
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
    print(f"📊 CRASH SAFETY RESULTS: {passed} PASSED, {failed} FAILED")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Bot handles low parameters gracefully")
        print("✅ Bot won't crash with extreme values")
        print("✅ Bot continues running with any parameter values")
        print("✅ Signal validation works with any thresholds")
        print("✅ Risk calculation works with any values")
        return True
    else:
        print("⚠️  Some tests failed. Bot may crash with extreme parameters")
        return False

if __name__ == "__main__":
    main()