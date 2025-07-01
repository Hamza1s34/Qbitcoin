#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open(os.path.join(this_directory, 'requirements.txt'), encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='qbitcoin',
    version='1.0.0',
    author='qbitcoin',
    author_email='qbitcoin@example.com',
    description='A Python-based cryptocurrency implementation with quantum-resistant features',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/qbitcoin/Qbitcoin',
    project_urls={
        'Bug Reports': 'https://github.com/qbitcoin/Qbitcoin/issues',
        'Source': 'https://github.com/qbitcoin/Qbitcoin',
        'Documentation': 'https://github.com/qbitcoin/Qbitcoin/tree/main/docs',
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
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'qbitcoin=qbitcoin.main:main',
            'qbitcoin-node=start_qbitcoin:main_entry',
        ],
    },
    include_package_data=True,
    package_data={
        'qbitcoin': ['core/*.yml', '**/*.proto'],
    },
    zip_safe=False,
)
