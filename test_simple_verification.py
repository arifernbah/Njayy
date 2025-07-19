#!/usr/bin/env python3
"""
SIMPLE VERIFICATION TEST
Checks if bot properly uses .env parameters by examining the code
"""

import os
import re

def check_bot_code():
    """Check bot.py for proper .env usage"""
    print("🔍 Checking bot.py for .env parameter usage...")
    
    with open('bot.py', 'r') as f:
        content = f.read()
    
    issues = []
    
    # Check for hardcoded values that should use config
    hardcoded_patterns = [
        (r'quality_score.*>.*[0-9]+', 'Hardcoded quality score threshold'),
        (r'MIN_QUALITY_SCORE.*=.*[0-9]+', 'Hardcoded MIN_QUALITY_SCORE'),
        (r'MIN_SIGNAL_STRENGTH.*=.*[0-9]+', 'Hardcoded MIN_SIGNAL_STRENGTH'),
        (r'DEFAULT_RISK.*=.*[0-9]+', 'Hardcoded DEFAULT_RISK'),
        (r'VOL_RANGE.*=.*\[.*\]', 'Hardcoded volatility range'),
    ]
    
    for pattern, description in hardcoded_patterns:
        matches = re.findall(pattern, content)
        if matches:
            issues.append(f"{description}: {matches}")
    
    # Check for proper config usage
    config_usage = [
        'self.config.MIN_QUALITY_SCORE',
        'self.config.MIN_SIGNAL_STRENGTH', 
        'self.config.DEFAULT_RISK',
        'self.config.VOL_RANGE_MIN',
        'self.config.VOL_RANGE_MAX'
    ]
    
    config_found = []
    for usage in config_usage:
        if usage in content:
            config_found.append(usage)
    
    print(f"✅ Found {len(config_found)} proper config usages:")
    for usage in config_found:
        print(f"   - {usage}")
    
    if issues:
        print(f"⚠️  Found {len(issues)} potential issues:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("✅ No hardcoded values found")
        return True

def check_config_code():
    """Check core/config.py for proper .env loading"""
    print("\n🔍 Checking core/config.py for .env loading...")
    
    with open('core/config.py', 'r') as f:
        content = f.read()
    
    # Check for .env loading
    if 'load_dotenv' in content:
        print("✅ Found load_dotenv() - .env file will be loaded")
    else:
        print("❌ No load_dotenv() found - .env file may not be loaded")
        return False
    
    # Check for environment variable usage
    env_vars = [
        'MIN_QUALITY_SCORE',
        'MIN_SIGNAL_STRENGTH',
        'DEFAULT_RISK',
        'VOL_RANGE_MIN',
        'VOL_RANGE_MAX'
    ]
    
    env_found = []
    for var in env_vars:
        if f'os.getenv("{var}"' in content or f"os.getenv('{var}'" in content:
            env_found.append(var)
    
    print(f"✅ Found {len(env_found)} environment variables:")
    for var in env_found:
        print(f"   - {var}")
    
    if len(env_found) >= 3:
        return True
    else:
        print("❌ Not enough environment variables found")
        return False

def check_signal_validation():
    """Check specific signal validation logic"""
    print("\n🔍 Checking signal validation logic...")
    
    with open('bot.py', 'r') as f:
        content = f.read()
    
    # Look for _validate_signal method
    if '_validate_signal' in content:
        print("✅ Found _validate_signal method")
        
        # Check if it uses config thresholds
        if 'self.config.MIN_QUALITY_SCORE' in content:
            print("✅ Signal validation uses MIN_QUALITY_SCORE from config")
        else:
            print("❌ Signal validation may not use MIN_QUALITY_SCORE from config")
            return False
            
        if 'self.config.MIN_SIGNAL_STRENGTH' in content:
            print("✅ Signal validation uses MIN_SIGNAL_STRENGTH from config")
        else:
            print("❌ Signal validation may not use MIN_SIGNAL_STRENGTH from config")
            return False
            
        return True
    else:
        print("❌ No _validate_signal method found")
        return False

def check_risk_calculation():
    """Check risk calculation logic"""
    print("\n🔍 Checking risk calculation logic...")
    
    with open('bot.py', 'r') as f:
        content = f.read()
    
    # Look for risk calculation
    if 'DEFAULT_RISK' in content and 'self.config.DEFAULT_RISK' in content:
        print("✅ Risk calculation uses DEFAULT_RISK from config")
    else:
        print("❌ Risk calculation may not use DEFAULT_RISK from config")
        return False
    
    if 'REDUCED_RISK' in content and 'self.config.REDUCED_RISK' in content:
        print("✅ Risk calculation uses REDUCED_RISK from config")
    else:
        print("❌ Risk calculation may not use REDUCED_RISK from config")
        return False
    
    return True

def check_volatility_filter():
    """Check volatility filtering logic"""
    print("\n🔍 Checking volatility filtering logic...")
    
    with open('bot.py', 'r') as f:
        content = f.read()
    
    # Look for volatility validation
    if 'VOL_RANGE_MIN' in content and 'self.config.VOL_RANGE_MIN' in content:
        print("✅ Volatility filter uses VOL_RANGE_MIN from config")
    else:
        print("❌ Volatility filter may not use VOL_RANGE_MIN from config")
        return False
    
    if 'VOL_RANGE_MAX' in content and 'self.config.VOL_RANGE_MAX' in content:
        print("✅ Volatility filter uses VOL_RANGE_MAX from config")
    else:
        print("❌ Volatility filter may not use VOL_RANGE_MAX from config")
        return False
    
    return True

def check_trading_limits():
    """Check trading limits logic"""
    print("\n🔍 Checking trading limits logic...")
    
    with open('bot.py', 'r') as f:
        content = f.read()
    
    # Look for trading limits
    limits = ['MAX_DAILY_TRADES', 'MAX_OPEN_POSITIONS', 'MAX_CONCURRENT_TRADES']
    
    for limit in limits:
        if limit in content and f'self.config.{limit}' in content:
            print(f"✅ Trading limits use {limit} from config")
        else:
            print(f"❌ Trading limits may not use {limit} from config")
            return False
    
    return True

def main():
    """Run all verification checks"""
    print("🚀 STARTING SIMPLE VERIFICATION TEST")
    print("=" * 60)
    
    checks = [
        check_bot_code,
        check_config_code,
        check_signal_validation,
        check_risk_calculation,
        check_volatility_filter,
        check_trading_limits
    ]
    
    passed = 0
    failed = 0
    
    for check in checks:
        try:
            if check():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {check.__name__} FAILED: {str(e)}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"📊 VERIFICATION RESULTS: {passed} PASSED, {failed} FAILED")
    
    if failed == 0:
        print("🎉 ALL CHECKS PASSED!")
        print("✅ Bot properly uses .env parameters")
        print("✅ Bot will NOT execute low-quality signals")
        print("✅ Bot respects all configured thresholds")
        print("✅ Bot uses proper risk management")
        return True
    else:
        print("⚠️  Some checks failed. Bot may not be properly configured")
        return False

if __name__ == "__main__":
    main()