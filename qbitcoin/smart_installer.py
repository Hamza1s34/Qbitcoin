#!/usr/bin/env python3
"""
Smart Dependency Installer for Qbitcoin
Automatically detects OS and installs required system dependencies
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path


class SmartInstaller:
    def __init__(self):
        self.os_type = platform.system().lower()
        self.arch = platform.machine().lower()
        self.distro = self.get_linux_distro()
        
    def get_linux_distro(self):
        """Detect Linux distribution"""
        try:
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    content = f.read().lower()
                    if 'ubuntu' in content or 'debian' in content:
                        return 'debian'
                    elif 'centos' in content or 'rhel' in content or 'fedora' in content:
                        return 'redhat'
                    elif 'arch' in content:
                        return 'arch'
                    elif 'alpine' in content:
                        return 'alpine'
        except:
            pass
        return 'unknown'
    
    def run_command(self, cmd, silent=False):
        """Run shell command safely"""
        try:
            if not silent:
                print(f"Running: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0 and not silent:
                print(f"Warning: Command failed: {cmd}")
                print(f"Error: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            if not silent:
                print(f"Error running command: {e}")
            return False
    
    def check_command(self, cmd):
        """Check if command exists"""
        return shutil.which(cmd) is not None
    
    def install_system_dependencies(self):
        """Install system dependencies based on OS"""
        print(f"🔍 Detected OS: {self.os_type} ({self.distro}) on {self.arch}")
        
        if self.os_type == 'linux':
            return self.install_linux_deps()
        elif self.os_type == 'darwin':
            return self.install_macos_deps()
        elif self.os_type == 'windows':
            return self.install_windows_deps()
        else:
            print(f"⚠️  Unsupported OS: {self.os_type}")
            return False
    
    def install_linux_deps(self):
        """Install Linux dependencies"""
        print("📦 Installing Linux system dependencies...")
        
        # Common packages needed
        packages = [
            'build-essential', 'cmake', 'pkg-config', 'libssl-dev', 
            'libffi-dev', 'python3-dev', 'git', 'autoconf', 'libtool',
            'libboost-all-dev', 'libgmp-dev', 'libmpfr-dev', 'libmpc-dev'
        ]
        
        if self.distro == 'debian':
            # Ubuntu/Debian
            if not self.check_command('apt-get'):
                print("❌ apt-get not found")
                return False
                
            # Update package list
            self.run_command('sudo apt-get update')
            
            # Install packages
            cmd = f"sudo apt-get install -y {' '.join(packages)}"
            return self.run_command(cmd)
            
        elif self.distro == 'redhat':
            # CentOS/RHEL/Fedora
            if self.check_command('dnf'):
                pkg_manager = 'dnf'
            elif self.check_command('yum'):
                pkg_manager = 'yum'
            else:
                print("❌ No supported package manager found")
                return False
            
            # Convert package names for RedHat
            redhat_packages = [
                'gcc-c++', 'cmake', 'pkgconfig', 'openssl-devel',
                'libffi-devel', 'python3-devel', 'git', 'autoconf', 'libtool',
                'boost-devel', 'gmp-devel', 'mpfr-devel', 'libmpc-devel'
            ]
            
            cmd = f"sudo {pkg_manager} install -y {' '.join(redhat_packages)}"
            return self.run_command(cmd)
            
        elif self.distro == 'arch':
            # Arch Linux
            if not self.check_command('pacman'):
                print("❌ pacman not found")
                return False
                
            arch_packages = [
                'base-devel', 'cmake', 'pkgconf', 'openssl', 'libffi',
                'python', 'git', 'autoconf', 'libtool', 'boost',
                'gmp', 'mpfr', 'libmpc'
            ]
            
            cmd = f"sudo pacman -S --noconfirm {' '.join(arch_packages)}"
            return self.run_command(cmd)
            
        elif self.distro == 'alpine':
            # Alpine Linux
            if not self.check_command('apk'):
                print("❌ apk not found")
                return False
                
            alpine_packages = [
                'build-base', 'cmake', 'pkgconfig', 'openssl-dev',
                'libffi-dev', 'python3-dev', 'git', 'autoconf', 'libtool',
                'boost-dev', 'gmp-dev', 'mpfr-dev', 'mpc1-dev'
            ]
            
            self.run_command('sudo apk update')
            cmd = f"sudo apk add {' '.join(alpine_packages)}"
            return self.run_command(cmd)
        
        else:
            print(f"⚠️  Unknown Linux distribution: {self.distro}")
            return False
    
    def install_macos_deps(self):
        """Install macOS dependencies"""
        print("🍎 Installing macOS system dependencies...")
        
        # Check if Homebrew is installed
        if not self.check_command('brew'):
            print("📥 Installing Homebrew...")
            cmd = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            if not self.run_command(cmd):
                print("❌ Failed to install Homebrew")
                return False
        
        # Install packages with Homebrew
        packages = [
            'cmake', 'pkg-config', 'openssl', 'libffi', 'git',
            'autoconf', 'libtool', 'boost', 'gmp', 'mpfr', 'libmpc'
        ]
        
        for package in packages:
            self.run_command(f'brew install {package}', silent=True)
        
        return True
    
    def install_windows_deps(self):
        """Install Windows dependencies"""
        print("🪟 Setting up Windows dependencies...")
        
        # Check if we're in a conda environment
        if 'CONDA_DEFAULT_ENV' in os.environ:
            print("📦 Installing dependencies with conda...")
            packages = ['cmake', 'git', 'm2w64-gcc', 'm2w64-gcc-fortran']
            for package in packages:
                self.run_command(f'conda install -y {package}', silent=True)
            return True
        
        # Check if chocolatey is available
        elif self.check_command('choco'):
            print("📦 Installing dependencies with Chocolatey...")
            packages = ['cmake', 'git', 'mingw']
            for package in packages:
                self.run_command(f'choco install -y {package}', silent=True)
            return True
        
        else:
            print("⚠️  Please install Visual Studio Build Tools or MinGW manually")
            print("   Or use conda/chocolatey for easier dependency management")
            return False
    
    def install_python_deps_safely(self):
        """Install Python dependencies with fallback options"""
        print("🐍 Installing Python dependencies...")
        
        # Basic dependencies that usually work
        basic_deps = [
            'plyvel', 'ntplib', 'Twisted', 'colorlog', 'simplejson',
            'PyYAML', 'grpcio-tools', 'grpcio', 'google-api-python-client',
            'google-auth', 'httplib2', 'service_identity', 'protobuf',
            'pyopenssl', 'six', 'click', 'cryptography', 'Flask',
            'json-rpc', 'idna', 'base58', 'mock', 'daemonize'
        ]
        
        # Install basic dependencies
        for dep in basic_deps:
            print(f"Installing {dep}...")
            self.run_command(f'pip install "{dep}"', silent=True)
        
        # Try to install quantum libraries (these might fail)
        quantum_deps = ['pqcrypto', 'pyqrllib', 'pyqryptonight', 'pyqrandomx']
        
        print("🔬 Installing quantum-resistant libraries (optional)...")
        for dep in quantum_deps:
            print(f"Attempting to install {dep}...")
            if not self.run_command(f'pip install "{dep}"', silent=True):
                print(f"⚠️  {dep} installation failed - quantum features may be limited")
        
        return True
    
    def verify_installation(self):
        """Verify that Qbitcoin can be imported"""
        print("🧪 Verifying installation...")
        try:
            import qbitcoin
            print("✅ Qbitcoin imported successfully!")
            return True
        except ImportError as e:
            print(f"❌ Import failed: {e}")
            return False
    
    def install(self):
        """Main installation process"""
        print("🚀 Qbitcoin Smart Installer")
        print("=" * 50)
        
        # Install system dependencies
        if not self.install_system_dependencies():
            print("⚠️  System dependency installation had issues, but continuing...")
        
        # Upgrade pip
        print("⬆️  Upgrading pip...")
        self.run_command('pip install --upgrade pip setuptools wheel')
        
        # Install Python dependencies
        if not self.install_python_deps_safely():
            print("❌ Failed to install Python dependencies")
            return False
        
        print("🎉 Installation completed!")
        return True


def main():
    """Entry point for smart installation"""
    installer = SmartInstaller()
    return installer.install()


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
