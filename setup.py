#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from setuptools.command.install import install
import os
import sys


def read_requirements():
    """Read requirements from requirements.txt"""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(requirements_path, 'r') as f:
        requirements = []
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('pyqrllib') and not line.startswith('pyqryptonight') and not line.startswith('pyqrandomx'):
                requirements.append(line)
        return requirements


def get_version():
    """Get version from the centralized version file"""
    version_file = os.path.join(os.path.dirname(__file__), 'qbitcoin', 'version.py')
    with open(version_file, 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"\'')
    return "1.0.7"  # fallback version


class PostInstallCommand(install):
    """Custom post-installation command"""
    def run(self):
        install.run(self)
        
        # Run smart installer for quantum libraries after basic installation
        try:
            print("🔧 Running Qbitcoin smart installer for quantum libraries...")
            print("📋 This will install: pyqrllib, pyqryptonight, pyqrandomx")
            print("⏳ This may take a few minutes for compilation...")
            
            # Import and run smart installer
            from qbitcoin.smart_installer import SmartInstaller
            installer = SmartInstaller()
            
            print("🧬 Installing quantum-resistant libraries with mining support...")
            success = installer.install_all_quantum_libraries()
            
            if success:
                print("✅ Smart installation completed successfully!")
            else:
                print("⚠️  Some quantum libraries may have failed - basic functionality available")
                print("💡 You can manually run: python -m qbitcoin.smart_installer")
            
        except Exception as e:
            print(f"⚠️  Smart installer encountered issues: {e}")
            print("💡 You can manually install quantum libraries by running:")
            print("   python -m qbitcoin.smart_installer")
            # Don't fail the entire installation for quantum library issues


# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get requirements from requirements.txt
install_requirements = read_requirements()
quantum_requirements = [
    'pqcrypto>=0.3.0',
]

# Note: Advanced quantum libraries (pyqrllib, pyqryptonight, pyqrandomx) 
# are installed separately by the smart installer to handle compilation issues

setup(
    name='qbitcoin',
    version=get_version(),
    author='Hamza',
    author_email='qbitcoin@example.com',
    description='A Python-based cryptocurrency implementation with quantum-resistant features',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Hamza1s34/Qbitcoin',
    project_urls={
        'Bug Reports': 'https://github.com/Hamza1s34/Qbitcoin/issues',
        'Source': 'https://github.com/Hamza1s34/Qbitcoin',
        'Documentation': 'https://github.com/Hamza1s34/Qbitcoin/tree/main/docs',
    },
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Security :: Cryptography',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    python_requires='>=3.8',
    install_requires=install_requirements,
    extras_require={
        'quantum-full': [
            # Note: These require compilation and are better installed via smart installer
            # 'pyqrllib>=1.2.3',
            # 'pyqryptonight>=0.99.0', 
            # 'pyqrandomx>=0.3.0',
        ],
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'black>=22.0.0',
            'flake8>=5.0.0',
            'build>=0.8.0',
            'twine>=4.0.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'qbitcoin=qbitcoin.main:main',
            'qbitcoin-node=start_qbitcoin:main_entry',
            'qbitcoin-installer=qbitcoin.smart_installer:main',
        ],
    },
    cmdclass={
        'install': PostInstallCommand,
    },
    include_package_data=True,
    package_data={
        'qbitcoin': ['core/*.yml', '**/*.proto'],
    },
    zip_safe=False,
)
