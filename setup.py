#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from setuptools.command.install import install
import os
import sys


class PostInstallCommand(install):
    """Custom post-installation command"""
    def run(self):
        install.run(self)
        
        # Run smart installer after installation
        try:
            print("🔧 Running Qbitcoin smart installer...")
            from qbitcoin.smart_installer import SmartInstaller
            installer = SmartInstaller()
            installer.install_python_deps_safely()
            print("✅ Smart installation completed!")
        except Exception as e:
            print(f"⚠️  Smart installer had issues: {e}")
            print("💡 You can manually run: python -m qbitcoin.smart_installer")


# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Basic requirements that should work on most systems
basic_requirements = [
    'plyvel>=1.5.0',
    'ntplib>=0.4.0', 
    'Twisted>=22.0.0',
    'colorlog>=6.0.0',
    'simplejson>=3.17.0',
    'PyYAML>=6.0',
    'grpcio-tools>=1.50.0',
    'grpcio>=1.50.0',
    'google-api-python-client>=2.70.0',
    'google-auth>=2.0.0',
    'httplib2>=0.20.0',
    'service_identity>=21.0.0',
    'protobuf>=4.0.0',
    'pyopenssl>=23.0.0',
    'six>=1.16.0',
    'click>=8.0.0',
    'cryptography>=40.0.0',
    'Flask>=2.0.0',
    'json-rpc>=1.13.0',
    'idna>=3.0',
    'base58>=2.1.0',
    'mock>=4.0.0',
    'daemonize>=2.5.0',
]

# Optional quantum libraries (may fail to install)
quantum_requirements = [
    'pqcrypto>=0.3.0; platform_machine=="x86_64"',
]

setup(
    name='qbitcoin',
    version='1.0.2',
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
    install_requires=basic_requirements + quantum_requirements,
    extras_require={
        'quantum': [
            'pyqrllib>=1.2.3',
            'pyqryptonight>=0.99.0', 
            'pyqrandomx>=0.3.0',
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
