#!/usr/bin/env python3
"""
Post-installation script for Qbitcoin
This script runs automatically after pip install qbitcoin
"""

import sys
import os
import subprocess


def run_smart_installer():
    """Run the smart installer after package installation"""
    try:
        print("🔧 Running Qbitcoin post-installation setup...")
        
        # Import and run the smart installer
        from qbitcoin.smart_installer import SmartInstaller
        
        installer = SmartInstaller()
        success = installer.install()
        
        if success:
            print("✅ Qbitcoin installation completed successfully!")
            print("🚀 You can now use: import qbitcoin")
        else:
            print("⚠️  Installation completed with some warnings")
            print("💡 Try running: python -m qbitcoin.smart_installer")
            
    except Exception as e:
        print(f"❌ Post-installation setup failed: {e}")
        print("💡 You can manually run: python -m qbitcoin.smart_installer")


if __name__ == '__main__':
    run_smart_installer()
