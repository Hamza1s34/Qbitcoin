#!/usr/bin/env python3
"""
Quick installation script for Qbitcoin using the smart installer
"""

import sys
import os
import subprocess

def main():
    print("🚀 Qbitcoin Quick Installation")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9 or higher is required")
        print(f"   Current version: {sys.version}")
        return 1
    
    print(f"✅ Python version: {sys.version}")
    
    # Add the qbitcoin module to the path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    qbitcoin_path = os.path.join(script_dir, 'qbitcoin')
    sys.path.insert(0, qbitcoin_path)
    
    try:
        from smart_installer import SmartInstaller
        
        installer = SmartInstaller()
        success = installer.install()
        
        if success:
            print("\n🎉 Qbitcoin installation completed successfully!")
            print("\n📋 Next steps:")
            print("   1. Start the node: python -m qbitcoin.qbitnode")
            print("   2. Create a wallet: python -m qbitcoin.cli wallet create")
            print("   3. Check balance: python -m qbitcoin.cli wallet balance")
            print("\n📚 For more information, see: docs/03-Quick-Start.md")
            return 0
        else:
            print("\n❌ Installation failed!")
            print("   Please check the error messages above.")
            print("   For help, visit: https://github.com/your-repo/qbitcoin/issues")
            return 1
            
    except ImportError as e:
        print(f"\n❌ Failed to import smart installer: {e}")
        print("   Make sure you're running this script from the Qbitcoin directory.")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
