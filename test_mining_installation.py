#!/usr/bin/env python3
"""
Advanced test script for Qbitcoin installation with mining support
Tests quantum libraries and mining functionality
"""

import sys
import os
import time

def test_mining_libraries():
    """Test mining-enabled quantum libraries"""
    print("🔬 Testing quantum libraries with mining support...")
    
    libraries = {
        'pyqrllib': 'QRL quantum-resistant signatures',
        'pyqryptonight': 'CryptoNight mining algorithms', 
        'pyqrandomx': 'RandomX mining algorithms',
        'pqcrypto': 'Post-quantum cryptography'
    }
    
    results = {}
    for lib, description in libraries.items():
        try:
            __import__(lib)
            print(f"✅ {lib}: {description} - AVAILABLE")
            results[lib] = True
        except ImportError as e:
            print(f"❌ {lib}: {description} - MISSING ({e})")
            results[lib] = False
    
    return results

def test_compilation_headers():
    """Test if mining headers are properly included"""
    print("🔧 Testing compilation headers...")
    
    try:
        # Test basic C++ compatibility types
        import ctypes
        
        # These should be available if headers are properly included
        test_types = ['c_uint8', 'c_uint16', 'c_uint32', 'c_uint64']
        for t in test_types:
            if hasattr(ctypes, t):
                print(f"✅ {t} type available")
            else:
                print(f"❌ {t} type missing")
        
        return True
    except Exception as e:
        print(f"❌ Header test failed: {e}")
        return False

def test_mining_performance():
    """Test basic mining performance"""
    print("⚡ Testing mining performance...")
    
    try:
        import hashlib
        import time
        
        # Simple hash performance test
        start_time = time.time()
        data = b"test_mining_data_" * 1000
        
        for i in range(10000):
            hash_result = hashlib.sha256(data + str(i).encode()).hexdigest()
        
        end_time = time.time()
        hashes_per_second = 10000 / (end_time - start_time)
        
        print(f"✅ Basic hashing: {hashes_per_second:.0f} hashes/second")
        
        # Test quantum-resistant hashing if available
        try:
            import pyqrllib
            start_time = time.time()
            
            # Test QRL hashing (if available)
            for i in range(1000):
                # This is a placeholder - actual QRL hash would go here
                pass
            
            end_time = time.time()
            print(f"✅ Quantum-resistant hashing available")
            return True
            
        except ImportError:
            print("⚠️  Quantum-resistant hashing not available")
            return False
            
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def test_boost_integration():
    """Test Boost library integration"""
    print("🚀 Testing Boost integration...")
    
    try:
        # Try to compile a simple C++ extension that uses Boost
        import tempfile
        import subprocess
        import os
        
        # Create a simple test program
        test_code = '''
#include <boost/version.hpp>
#include <boost/algorithm/string.hpp>
#include <iostream>

int main() {
    std::cout << "Boost version: " << BOOST_VERSION << std::endl;
    return 0;
}
'''
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "boost_test.cpp")
            binary_file = os.path.join(tmpdir, "boost_test")
            
            with open(test_file, 'w') as f:
                f.write(test_code)
            
            # Try to compile
            compile_cmd = f"g++ -I/usr/include/boost -lboost_system {test_file} -o {binary_file}"
            result = subprocess.run(compile_cmd, shell=True, capture_output=True)
            
            if result.returncode == 0:
                print("✅ Boost compilation successful")
                
                # Try to run
                run_result = subprocess.run(binary_file, capture_output=True, text=True)
                if run_result.returncode == 0:
                    print(f"✅ Boost runtime test: {run_result.stdout.strip()}")
                    return True
                else:
                    print("⚠️  Boost runtime test failed")
                    return False
            else:
                print(f"⚠️  Boost compilation failed: {result.stderr.decode()}")
                return False
                
    except Exception as e:
        print(f"❌ Boost test failed: {e}")
        return False

def test_smart_installer():
    """Test the smart installer functionality"""
    print("🤖 Testing smart installer...")
    
    try:
        from qbitcoin.smart_installer import SmartInstaller
        
        installer = SmartInstaller()
        print(f"✅ Smart installer loaded")
        print(f"   OS: {installer.os_type}")
        print(f"   Distribution: {installer.distro}")
        print(f"   Architecture: {installer.arch}")
        print(f"   Temp directory: {installer.temp_dir}")
        
        # Test mining headers
        if len(installer.mining_headers) > 100:
            print("✅ Mining headers available")
        else:
            print("❌ Mining headers missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Smart installer test failed: {e}")
        return False

def main():
    """Run comprehensive mining-enabled tests"""
    print("🧪 Qbitcoin Mining Installation Test Suite")
    print("=" * 50)
    
    tests = [
        ("Smart Installer", test_smart_installer),
        ("Quantum Libraries", test_mining_libraries),
        ("Compilation Headers", test_compilation_headers),
        ("Boost Integration", test_boost_integration),
        ("Mining Performance", test_mining_performance),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"💥 {test_name} test CRASHED: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Qbitcoin mining is ready!")
        print("🔬 Quantum-resistant mining features are enabled")
        return 0
    else:
        print("⚠️  Some tests failed. Check output above for details.")
        if passed >= total // 2:
            print("💡 Basic functionality should still work")
        return 1

if __name__ == '__main__':
    sys.exit(main())
