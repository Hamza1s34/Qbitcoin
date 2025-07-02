# -*- coding: utf-8 -*-
"""
Centralized version management for Qbitcoin
This is the single source of truth for version information
"""

__version__ = "1.0.3"

def get_version():
    """Get the current version"""
    return __version__

def get_version_info():
    """Get version as tuple"""
    return tuple(map(int, __version__.split('.')))

# For backwards compatibility with versioneer
def get_versions():
    """Compatibility function for versioneer"""
    return {
        'version': __version__,
        'full-revisionid': None,
        'dirty': False,
        'error': None,
        'date': None
    }
