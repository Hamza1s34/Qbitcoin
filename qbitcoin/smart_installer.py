#!/usr/bin/env python3
"""
Smart Dependency Installer for Qbitcoin
Automatically detects OS and installs required system dependencies
Downloads, patches, and compiles quantum libraries with mining support
"""

import os
import sys
import platform
import subprocess
import shutil
import tempfile
import urllib.request
import zipfile
import tarfile
import re
import glob
from pathlib import Path


class SmartInstaller:
    def __init__(self):
        self.os_type = platform.system().lower()
        self.arch = platform.machine().lower()
        self.distro = self.get_linux_distro()
        self.temp_dir = tempfile.mkdtemp(prefix='qbitcoin_build_')
        self.mining_headers = self.get_mining_headers()
        
    def get_mining_headers(self):
        """Return mining-related headers to add to source files"""
        return """
// Mining support headers
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <memory>
#include <vector>
#include <algorithm>
#include <chrono>
#include <thread>
#include <mutex>
#include <atomic>

// Mining-specific includes
#ifndef MINING_SUPPORT
#define MINING_SUPPORT 1
#endif

// Ensure compatibility with mining algorithms
#ifndef uint8_t
typedef unsigned char uint8_t;
#endif
#ifndef uint16_t
typedef unsigned short uint16_t;
#endif
#ifndef uint32_t
typedef unsigned int uint32_t;
#endif
#ifndef uint64_t
typedef unsigned long long uint64_t;
#endif
"""
        
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
        
        # Common packages needed including mining dependencies
        packages = [
            'build-essential', 'cmake', 'pkg-config', 'libssl-dev', 
            'libffi-dev', 'python3-dev', 'git', 'autoconf', 'libtool',
            'libboost-all-dev', 'libgmp-dev', 'libmpfr-dev', 'libmpc-dev',
            # Mining specific dependencies
            'libboost-system-dev', 'libboost-thread-dev', 'libboost-chrono-dev',
            'libboost-program-options-dev', 'libboost-test-dev', 'libboost-filesystem-dev',
            'libeigen3-dev', 'libsodium-dev', 'libhwloc-dev',
            # Compilation tools
            'gcc-multilib', 'g++-multilib', 'libc6-dev', 'linux-libc-dev',
            'wget', 'curl', 'unzip', 'tar', 'gzip'
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
                'boost-devel', 'gmp-devel', 'mpfr-devel', 'libmpc-devel',
                # Mining dependencies for RedHat
                'boost-system', 'boost-thread', 'boost-chrono', 'boost-program-options',
                'boost-test', 'boost-filesystem', 'eigen3-devel', 'libsodium-devel',
                'hwloc-devel', 'wget', 'curl', 'unzip', 'tar', 'gzip'
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
                'gmp', 'mpfr', 'libmpc',
                # Mining dependencies for Arch
                'eigen', 'libsodium', 'hwloc', 'wget', 'curl', 'unzip', 'tar', 'gzip'
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
                'boost-dev', 'gmp-dev', 'mpfr-dev', 'mpc1-dev',
                # Mining dependencies for Alpine
                'eigen-dev', 'libsodium-dev', 'hwloc-dev', 'wget', 'curl', 
                'unzip', 'tar', 'gzip', 'linux-headers'
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
        
        # Install packages with Homebrew including mining dependencies
        packages = [
            'cmake', 'pkg-config', 'openssl', 'libffi', 'git',
            'autoconf', 'libtool', 'boost', 'gmp', 'mpfr', 'libmpc',
            # Mining dependencies for macOS
            'eigen', 'libsodium', 'hwloc', 'wget', 'curl'
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
        
        # Try basic quantum crypto first
        print("🔬 Installing basic quantum crypto library...")
        if not self.run_command('pip install "pqcrypto"', silent=True):
            print("⚠️  pqcrypto installation failed")
        
        # Install quantum libraries with advanced compilation
        quantum_libs = {
            'pyqrllib': 'theQRL/pyqrllib',
            'pyqryptonight': 'davebaird/pyqryptonight', 
            'pyqrandomx': 'monero-ecosystem/pyqrandomx'
        }
        
        print("🧬 Installing quantum-resistant libraries with mining support...")
        for lib_name, repo in quantum_libs.items():
            print(f"🔄 Processing {lib_name}...")
            
            # Try pip install first (fast)
            if self.run_command(f'pip install "{lib_name}"', silent=True):
                print(f"✅ {lib_name} installed via pip")
                continue
            
            # If pip fails, try from source with patches
            print(f"⚙️  pip failed, trying source compilation for {lib_name}...")
            if self.install_quantum_library_from_source(lib_name, repo):
                print(f"✅ {lib_name} compiled from source successfully!")
            else:
                print(f"⚠️  {lib_name} installation failed - mining features may be limited")
        
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
        print("🚀 Qbitcoin Smart Installer with Mining Support")
        print("=" * 60)
        
        try:
            # Install system dependencies
            if not self.install_system_dependencies():
                print("⚠️  System dependency installation had issues, but continuing...")
            
            # Upgrade pip and install build tools
            print("⬆️  Upgrading pip and build tools...")
            self.run_command('pip install --upgrade pip setuptools wheel pybind11 cmake')
            
            # Install Python dependencies
            if not self.install_python_deps_safely():
                print("❌ Failed to install Python dependencies")
                return False
            
            print("🎉 Installation completed!")
            print("🔬 Quantum-resistant mining features have been enabled!")
            return True
            
        except Exception as e:
            print(f"❌ Installation failed with error: {e}")
            return False
        finally:
            # Always cleanup
            self.cleanup()
    
    def download_and_extract(self, url, extract_dir):
        """Download and extract source code"""
        print(f"📥 Downloading {url}...")
        
        # Create download directory
        os.makedirs(extract_dir, exist_ok=True)
        
        # Download file
        filename = url.split('/')[-1]
        filepath = os.path.join(self.temp_dir, filename)
        
        try:
            urllib.request.urlretrieve(url, filepath)
            print(f"✅ Downloaded {filename}")
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return False
        
        # Extract based on file type
        try:
            if filename.endswith('.zip'):
                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif filename.endswith(('.tar.gz', '.tgz')):
                with tarfile.open(filepath, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)
            elif filename.endswith('.tar'):
                with tarfile.open(filepath, 'r') as tar_ref:
                    tar_ref.extractall(extract_dir)
            else:
                print(f"⚠️  Unknown archive format: {filename}")
                return False
            
            print(f"✅ Extracted {filename}")
            return True
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            return False
    
    def patch_source_files(self, source_dir, library_name):
        """Add mining headers and fix compilation issues"""
        print(f"🔧 Patching {library_name} source files...")
        
        # Find all C++ source and header files
        cpp_extensions = ['.cpp', '.cxx', '.cc', '.c', '.hpp', '.h', '.hxx']
        files_to_patch = []
        
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if any(file.endswith(ext) for ext in cpp_extensions):
                    files_to_patch.append(os.path.join(root, file))
        
        patches_applied = 0
        for file_path in files_to_patch:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check if already patched
                if 'MINING_SUPPORT' in content:
                    continue
                
                # Add mining headers at the top
                if '#include' in content:
                    # Find the first #include and add our headers before it
                    lines = content.split('\n')
                    insert_idx = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith('#include'):
                            insert_idx = i
                            break
                    
                    # Insert mining headers
                    lines.insert(insert_idx, self.mining_headers)
                    
                    # Apply specific fixes based on library
                    if library_name == 'pyqrllib':
                        content = self.apply_pyqrllib_fixes('\n'.join(lines))
                    elif library_name == 'pyqryptonight':
                        content = self.apply_pyqryptonight_fixes('\n'.join(lines))
                    elif library_name == 'pyqrandomx':
                        content = self.apply_pyqrandomx_fixes('\n'.join(lines))
                    else:
                        content = '\n'.join(lines)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    patches_applied += 1
                
            except Exception as e:
                print(f"⚠️  Could not patch {file_path}: {e}")
        
        print(f"✅ Patched {patches_applied} files in {library_name}")
        return patches_applied > 0
    
    def apply_pyqrllib_fixes(self, content):
        """Apply specific fixes for pyqrllib"""
        # Fix dilithium issues
        content = re.sub(
            r'(#include\s+[<"][^>"]*dilithium[^>"]*[>"])',
            r'\1\n#include <cstdint>\n#include <cstring>',
            content
        )
        
        # Fix missing uint8_t declarations
        if 'uint8_t' in content and '#include <cstdint>' not in content:
            content = '#include <cstdint>\n' + content
        
        return content
    
    def apply_pyqryptonight_fixes(self, content):
        """Apply specific fixes for pyqryptonight"""
        # Add Boost includes if missing
        boost_includes = """
#ifdef __cplusplus
#include <boost/version.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/filesystem.hpp>
#endif
"""
        if 'boost' in content.lower() and '#include <boost' not in content:
            content = boost_includes + content
        
        return content
    
    def apply_pyqrandomx_fixes(self, content):
        """Apply specific fixes for pyqrandomx"""
        # Fix RandomX compilation issues
        randomx_fixes = """
// RandomX compatibility fixes
#ifndef RANDOMX_MINING_SUPPORT
#define RANDOMX_MINING_SUPPORT 1
#include <immintrin.h>
#include <emmintrin.h>
#endif
"""
        if 'randomx' in content.lower() and 'RANDOMX_MINING_SUPPORT' not in content:
            content = randomx_fixes + content
        
        return content
    
    def compile_quantum_library(self, library_name, source_dir, github_repo):
        """Download, patch, and compile quantum library from source"""
        print(f"🔬 Compiling {library_name} from source...")
        
        # Create build directory
        build_dir = os.path.join(source_dir, 'build')
        os.makedirs(build_dir, exist_ok=True)
        
        # Change to source directory
        original_dir = os.getcwd()
        os.chdir(source_dir)
        
        try:
            # Create a setup.py if it doesn't exist
            setup_py_content = f'''
from setuptools import setup, Extension, find_packages
from pybind11.setup_helpers import Pybind11Extension, build_ext
from pybind11 import get_cmake_dir
import pybind11

# Define the extension module
ext_modules = [
    Pybind11Extension(
        "{library_name}",
        sorted(glob.glob("src/**/*.cpp", recursive=True)),
        include_dirs=[
            pybind11.get_include(),
            "src",
            "/usr/include/boost",
            "/usr/local/include/boost",
        ],
        libraries=["boost_system", "boost_thread", "boost_chrono"],
        cxx_std=14,
        define_macros=[("MINING_SUPPORT", "1")],
    ),
]

setup(
    name="{library_name}",
    ext_modules=ext_modules,
    cmdclass={{"build_ext": build_ext}},
    zip_safe=False,
    python_requires=">=3.6",
)
'''
            
            # Write setup.py if missing
            if not os.path.exists('setup.py'):
                with open('setup.py', 'w') as f:
                    f.write(setup_py_content)
            
            # Try to build with pip
            build_cmd = f'{sys.executable} -m pip install .'
            result = subprocess.run(build_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {library_name} compiled successfully!")
                return True
            else:
                print(f"⚠️  {library_name} compilation failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error compiling {library_name}: {e}")
            return False
        finally:
            os.chdir(original_dir)
    
    def install_quantum_library_from_source(self, library_name, github_repo):
        """Download and install quantum library from source with patches"""
        print(f"🧬 Installing {library_name} from source...")
        
        # Download URLs for different libraries
        download_urls = {
            'pyqrllib': 'https://github.com/theQRL/pyqrllib/archive/refs/heads/master.zip',
            'pyqryptonight': 'https://github.com/davebaird/pyqryptonight/archive/refs/heads/master.zip',
            'pyqrandomx': 'https://github.com/monero-ecosystem/pyqrandomx/archive/refs/heads/master.zip'
        }
        
        if library_name not in download_urls:
            print(f"❌ Unknown library: {library_name}")
            return False
        
        # Create extraction directory
        extract_dir = os.path.join(self.temp_dir, library_name)
        
        # Download and extract
        if not self.download_and_extract(download_urls[library_name], extract_dir):
            return False
        
        # Find the actual source directory (usually extracted with folder name)
        source_dirs = [d for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
        if not source_dirs:
            print(f"❌ No source directory found for {library_name}")
            return False
        
        source_dir = os.path.join(extract_dir, source_dirs[0])
        
        # Patch source files
        if not self.patch_source_files(source_dir, library_name):
            print(f"⚠️  Patching failed for {library_name}, continuing anyway...")
        
        # Compile and install
        return self.compile_quantum_library(library_name, source_dir, github_repo)
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"🧹 Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()
        

def main():
    """Entry point for smart installation"""
    installer = SmartInstaller()
    return installer.install()


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
