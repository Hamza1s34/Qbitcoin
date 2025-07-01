# -*- coding: utf-8 -*-

__all__ = ['core', 'crypto']

from . import _version
__version__ = _version.get_versions()['version']

# Smart dependency checking and installation
import os
import sys
import warnings

def _check_dependencies():
    """Check and install missing dependencies automatically"""
    missing_deps = []
    
    # Check for critical dependencies
    critical_deps = [
        'plyvel', 'twisted', 'colorlog', 'simplejson', 'yaml',
        'grpc', 'cryptography', 'flask'
    ]
    
    for dep in critical_deps:
        try:
            if dep == 'yaml':
                import yaml
            elif dep == 'grpc':
                import grpc
            elif dep == 'twisted':
                import twisted
            else:
                __import__(dep)
        except ImportError:
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"🔍 Missing dependencies detected: {missing_deps}")
        
        # Ask user if they want to auto-install
        if os.getenv('QBITCOIN_AUTO_INSTALL', '').lower() in ['1', 'true', 'yes']:
            auto_install = True
        else:
            try:
                response = input("📦 Would you like to automatically install missing dependencies? (y/n): ")
                auto_install = response.lower().startswith('y')
            except (EOFError, KeyboardInterrupt):
                auto_install = False
        
        if auto_install:
            print("🚀 Starting automatic dependency installation...")
            try:
                from .smart_installer import SmartInstaller
                installer = SmartInstaller()
                installer.install()
                print("✅ Dependencies installed successfully!")
            except Exception as e:
                warnings.warn(f"Auto-installation failed: {e}")
                print("💡 Try running: pip install qbitcoin --upgrade --force-reinstall")
        else:
            print("💡 To install dependencies manually, run:")
            print("   pip install qbitcoin --upgrade --force-reinstall")
            print("   Or set QBITCOIN_AUTO_INSTALL=1 environment variable")

# Run dependency check on import (only if not in setup.py)
if 'setup.py' not in sys.argv[0]:
    try:
        _check_dependencies()
    except Exception as e:
        warnings.warn(f"Dependency check failed: {e}")
