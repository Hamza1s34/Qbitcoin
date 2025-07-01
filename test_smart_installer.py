#!/usr/bin/env python3
"""
Test script for the Smart Installer
"""

import sys
import os

# Add the qbitcoin module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'qbitcoin'))

from smart_installer import SmartInstaller

def main():
    print("🚀 Testing Qbitcoin Smart Installer")
    print("=" * 50)
    
    installer = SmartInstaller()
    success = installer.install()
    
    if success:
        print("\n🎉 Smart Installer completed successfully!")
        print("🔬 Testing quantum library imports...")
        
        # Test imports
        test_results = {}
        
        libraries = ['pyqrllib', 'pyqryptonight', 'pyqrandomx', 'pqcrypto']
        
        for lib in libraries:
            try:
                __import__(lib)
                test_results[lib] = "✅ SUCCESS"
            except ImportError as e:
                test_results[lib] = f"❌ FAILED: {e}"
        
        print("\n📊 Import Test Results:")
        for lib, result in test_results.items():
            print(f"  {lib}: {result}")
        
        # Test Qbitcoin import
        try:
            import qbitcoin
            print(f"\n✅ Qbitcoin core module imported successfully!")
            print(f"📍 Qbitcoin version: {getattr(qbitcoin, '__version__', 'unknown')}")
        except ImportError as e:
            print(f"\n❌ Qbitcoin import failed: {e}")
            
    else:
        print("\n❌ Smart Installer failed!")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
