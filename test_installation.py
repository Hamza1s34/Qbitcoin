#!/usr/bin/env python3
"""
Test script to verify Qbitcoin installation and smart installer
"""

import sys
import os

def test_basic_import():
    """Test basic qbitcoin import"""
    try:
        import qbitcoin
        print(f"✅ Basic import successful - Version: {qbitcoin.__version__}")
        return True
    except Exception as e:
        print(f"❌ Basic import failed: {e}")
        return False

def test_smart_installer():
    """Test smart installer functionality"""
    try:
        from qbitcoin.smart_installer import SmartInstaller
        installer = SmartInstaller()
        print(f"✅ Smart installer loaded - OS: {installer.os_type} ({installer.distro})")
        return True
    except Exception as e:
        print(f"❌ Smart installer test failed: {e}")
        return False

def test_core_modules():
    """Test core qbitcoin modules"""
    modules_to_test = [
        'qbitcoin.core',
        'qbitcoin.crypto', 
        'qbitcoin.services',
        'qbitcoin.tools'
    ]
    
    success_count = 0
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module} imported successfully")
            success_count += 1
        except Exception as e:
            print(f"⚠️  {module} import failed: {e}")
    
    return success_count > 0

def main():
    """Run all tests"""
    print("🧪 Testing Qbitcoin Installation")
    print("=" * 40)
    
    tests = [
        ("Basic Import", test_basic_import),
        ("Smart Installer", test_smart_installer), 
        ("Core Modules", test_core_modules)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        if test_func():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Qbitcoin is ready to use.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
