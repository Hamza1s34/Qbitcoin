#!/bin/bash
# GitHub Actions compatible version management script

set -e

echo "🔍 Qbitcoin Version Management"

# Get current version from centralized source
CURRENT_VERSION=$(python -c "
import sys
sys.path.insert(0, '.')
from qbitcoin.version import __version__
print(__version__)
")

echo "📋 Current version: $CURRENT_VERSION"

# Check if this version tag already exists
if git rev-parse "v$CURRENT_VERSION" >/dev/null 2>&1; then
    echo "⚠️  Tag v$CURRENT_VERSION already exists"
    echo "🔧 Cleaning up conflicting tag..."
    
    # Delete local tag if exists
    git tag -d "v$CURRENT_VERSION" 2>/dev/null || true
    
    # Delete remote tag if exists (in CI/CD, you might want to skip this or handle permissions)
    if [ "$GITHUB_ACTIONS" = "true" ]; then
        echo "🏗️  In GitHub Actions - will create fresh tag"
    else
        git push origin --delete "v$CURRENT_VERSION" 2>/dev/null || true
    fi
fi

# Create new tag
echo "🏷️  Creating tag v$CURRENT_VERSION"
git tag -a "v$CURRENT_VERSION" -m "Qbitcoin v$CURRENT_VERSION - Automated release"

echo "✅ Version management completed successfully"
echo "📦 Ready for release: v$CURRENT_VERSION"

# Show current tag info
git show --no-patch --format="Tag: %D%nDate: %ad%nMessage: %s" "v$CURRENT_VERSION"
