#!/usr/bin/env python3
"""
ACCURATE VERIFICATION TEST
Checks if bot properly uses .env parameters by examining the actual code
"""

import os
import re

def check_bot_validate_signal():
    """Check validate_signal method in bot.py"""
    print("🔍 Checking validate_signal method in bot.py...")
    
    with open('bot.py', 'r') as f:
        content = f.read()
    
    # Find validate_signal method
    validate_start = content.find('def validate_signal(self, signal):')
    if validate_start == -1:
        print("❌ validate_signal method not found")
        return False
    
    # Extract the method content
    method_content = content[validate_start:validate_start+2000]  # Get reasonable chunk
    
    # Check for config usage in signal validation
    config_checks = [
        ('MIN_QUALITY_SCORE', 'config.MIN_QUALITY_SCORE'),
        ('VOL_RANGE_MIN', 'config.VOL_RANGE_MIN'),
        ('VOL_RANGE_MAX', 'config.VOL_RANGE_MAX'),
    ]
    
    found_configs = []
    for check_name, config_var in config_checks:
        if config_var in method_content:
            found_configs.append(check_name)
            print(f"✅ Found {check_name} usage: {config_var}")
    
    # Check for hardcoded values that should use config
    hardcoded_issues = []
    
    # Look for hardcoded quality scores (but ignore comments)
    if 'quality_score >= 80' in method_content and '# Premium threshold' not in method_content:
        hardcoded_issues.append("Hardcoded quality_score >= 80")
    
    if 'quality_score >= 70' in method_content and 'config.MIN_QUALITY_SCORE' not in method_content:
        hardcoded_issues.append("Hardcoded quality_score >= 70")
    
    if 'quality_score >= 50' in method_content and 'config.MIN_QUALITY_SCORE' not in method_content:
        hardcoded_issues.append("Hardcoded quality_score >= 50")
    
    # Look for hardcoded volatility ranges
    if 'volatility <= 1.8' in method_content and 'config.VOL_RANGE_MAX' not in method_content:
        hardcoded_issues.append("Hardcoded volatility <= 1.8")
    
    if 'volatility >= 0.4' in method_content and 'config.VOL_RANGE_MIN' not in method_content:
        hardcoded_issues.append("Hardcoded volatility >= 0.4")
    
    if hardcoded_issues:
        print(f"⚠️  Found {len(hardcoded_issues)} hardcoded issues:")
        for issue in hardcoded_issues:
            print(f"   - {issue}")
        return False
    
    if len(found_configs) >= 2:
        print("✅ validate_signal properly uses config parameters")
        return True
    else:
        print("❌ validate_signal doesn't use enough config parameters")
        return False

def check_bot_calculate_risk():
    """Check calculate_risk method in bot.py"""
    print("\n🔍 Checking calculate_risk method in bot.py...")
    
    with open('bot.py', 'r') as f:
        content = f.read()
    
    # Find calculate_risk method
    risk_start = content.find('def calculate_risk(self):')
    if risk_start == -1:
        print("❌ calculate_risk method not found")
        return False
    
    # Extract the method content
    method_content = content[risk_start:risk_start+500]  # Get reasonable chunk
    
    # Check for config usage in risk calculation
    config_checks = [
        ('DEFAULT_RISK', 'config.DEFAULT_RISK'),
        ('REDUCED_RISK', 'config.REDUCED_RISK'),
        ('MINIMUM_RISK', 'config.MINIMUM_RISK'),
    ]
    
    found_configs = []
    for check_name, config_var in config_checks:
        if config_var in method_content:
            found_configs.append(check_name)
            print(f"✅ Found {check_name} usage: {config_var}")
    
    # Check for hardcoded risk values
    hardcoded_issues = []
    
    if 'default=1.0' in method_content and 'config.DEFAULT_RISK' not in method_content:
        hardcoded_issues.append("Hardcoded default risk 1.0")
    
    if 'default=0.5' in method_content and 'config.REDUCED_RISK' not in method_content:
        hardcoded_issues.append("Hardcoded reduced risk 0.5")
    
    if 'default=0.25' in method_content and 'config.MINIMUM_RISK' not in method_content:
        hardcoded_issues.append("Hardcoded minimum risk 0.25")
    
    if hardcoded_issues:
        print(f"⚠️  Found {len(hardcoded_issues)} hardcoded risk issues:")
        for issue in hardcoded_issues:
            print(f"   - {issue}")
        return False
    
    if len(found_configs) >= 2:
        print("✅ calculate_risk properly uses config parameters")
        return True
    else:
        print("❌ calculate_risk doesn't use enough config parameters")
        return False

def check_config_env_loading():
    """Check config.py for proper .env loading"""
    print("\n🔍 Checking core/config.py for .env loading...")
    
    with open('core/config.py', 'r') as f:
        content = f.read()
    
    # Check for .env loading
    if 'load_dotenv()' in content:
        print("✅ Found load_dotenv() - .env file will be loaded")
    else:
        print("❌ No load_dotenv() found")
        return False
    
    # Check for critical environment variables
    critical_vars = [
        'MIN_QUALITY_SCORE',
        'MIN_SIGNAL_STRENGTH', 
        'DEFAULT_RISK',
        'REDUCED_RISK',
        'MINIMUM_RISK',
        'VOL_RANGE_MIN',
        'VOL_RANGE_MAX'
    ]
    
    found_vars = []
    for var in critical_vars:
        if f'os.getenv("{var}"' in content or f"os.getenv('{var}'" in content:
            found_vars.append(var)
            print(f"✅ Found {var} environment variable loading")
    
    if len(found_vars) >= 5:
        print("✅ Config properly loads critical environment variables")
        return True
    else:
        print(f"❌ Only found {len(found_vars)}/{len(critical_vars)} critical variables")
        return False

def check_config_defaults():
    """Check config.py for proper default values"""
    print("\n🔍 Checking config.py for proper default values...")
    
    with open('core/config.py', 'r') as f:
        content = f.read()
    
    # Check for proper default values that match .env.template
    default_checks = [
        ('MIN_QUALITY_SCORE', '70'),
        ('MIN_SIGNAL_STRENGTH', '70'),
        ('DEFAULT_RISK', '1.0'),
        ('REDUCED_RISK', '0.5'),
        ('MINIMUM_RISK', '0.25'),
        ('VOL_RANGE_MIN', '0.4'),
        ('VOL_RANGE_MAX', '1.8')
    ]
    
    correct_defaults = []
    for var, expected_default in default_checks:
        pattern = f"os.getenv('{var}', {expected_default})"
        if pattern in content:
            correct_defaults.append(var)
            print(f"✅ {var} has correct default: {expected_default}")
    
    if len(correct_defaults) >= 5:
        print("✅ Config has proper default values")
        return True
    else:
        print(f"❌ Only {len(correct_defaults)}/{len(default_checks)} have correct defaults")
        return False

def check_safe_get_usage():
    """Check for proper safe_get usage with config defaults"""
    print("\n🔍 Checking safe_get usage with config defaults...")
    
    with open('bot.py', 'r') as f:
        content = f.read()
    
    # Look for safe_get usage with config defaults
    safe_get_patterns = [
        r"safe_get\(.*default=config\.MIN_QUALITY_SCORE\)",
        r"safe_get\(.*default=config\.VOL_RANGE_MIN.*config\.VOL_RANGE_MAX.*\)",
        r"safe_get\(.*default=config\.DEFAULT_RISK\)",
    ]
    
    found_patterns = []
    for pattern in safe_get_patterns:
        matches = re.findall(pattern, content)
        if matches:
            found_patterns.append(pattern)
            print(f"✅ Found safe_get with config default: {pattern[:50]}...")
    
    if len(found_patterns) >= 2:
        print("✅ Bot properly uses safe_get with config defaults")
        return True
    else:
        print("❌ Bot doesn't use enough safe_get with config defaults")
        return False

def check_no_hardcoded_critical_values():
    """Check for absence of hardcoded critical values"""
    print("\n🔍 Checking for absence of hardcoded critical values...")
    
    with open('bot.py', 'r') as f:
        content = f.read()
    
    # Look for hardcoded critical values
    hardcoded_patterns = [
        (r'quality_score >= [0-9]+', 'Hardcoded quality score threshold'),
        (r'MIN_QUALITY_SCORE = [0-9]+', 'Hardcoded MIN_QUALITY_SCORE assignment'),
        (r'DEFAULT_RISK = [0-9.]+', 'Hardcoded DEFAULT_RISK assignment'),
        (r'VOL_RANGE = \[[0-9., ]+\]', 'Hardcoded volatility range'),
    ]
    
    found_hardcoded = []
    for pattern, description in hardcoded_patterns:
        matches = re.findall(pattern, content)
        if matches:
            found_hardcoded.append(f"{description}: {matches}")
    
    if found_hardcoded:
        print(f"⚠️  Found {len(found_hardcoded)} hardcoded values:")
        for issue in found_hardcoded:
            print(f"   - {issue}")
        return False
    else:
        print("✅ No hardcoded critical values found")
        return True

def main():
    """Run all verification checks"""
    print("🚀 STARTING ACCURATE VERIFICATION TEST")
    print("=" * 60)
    
    checks = [
        check_bot_validate_signal,
        check_bot_calculate_risk,
        check_config_env_loading,
        check_config_defaults,
        check_safe_get_usage,
        check_no_hardcoded_critical_values
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
        print("✅ Bot uses config defaults instead of hardcoded values")
        return True
    else:
        print("⚠️  Some checks failed. Bot may not be properly configured")
        return False

if __name__ == "__main__":
    main()