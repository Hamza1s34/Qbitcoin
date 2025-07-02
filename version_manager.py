#!/usr/bin/env python3
"""
Version management script for Qbitcoin
Handles version updates across all files and Git tags
"""

import os
import re
import subprocess
import sys
from pathlib import Path


def get_current_version():
    """Get current version from version.py"""
    version_file = Path(__file__).parent / 'qbitcoin' / 'version.py'
    with open(version_file, 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"\'')
    return None


def update_version_in_file(file_path, new_version, pattern_replacements):
    """Update version in a specific file"""
    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        updated = False
        for pattern, replacement in pattern_replacements.items():
            new_content = re.sub(pattern, replacement.format(version=new_version), content)
            if new_content != content:
                content = new_content
                updated = True
        
        if updated:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✅ Updated {file_path}")
            return True
        else:
            print(f"ℹ️  No changes needed in {file_path}")
            return True
            
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False


def update_all_versions(new_version):
    """Update version in all relevant files"""
    print(f"🔄 Updating all files to version {new_version}")
    
    # Define files and their version patterns
    files_to_update = {
        'qbitcoin/version.py': {
            r'__version__\s*=\s*["\'][^"\']*["\']': '__version__ = "{version}"'
        },
        'setup.py': {
            # We don't need to update setup.py since it reads from version.py
        },
        'pyproject.toml': {
            r'version\s*=\s*["\'][^"\']*["\']': 'version = "{version}"'
        }
    }
    
    success = True
    for file_path, patterns in files_to_update.items():
        if patterns:  # Skip files with empty patterns
            if not update_version_in_file(file_path, new_version, patterns):
                success = False
    
    return success


def delete_git_tag(tag_name):
    """Delete a Git tag locally and remotely"""
    try:
        # Delete local tag
        result = subprocess.run(['git', 'tag', '-d', tag_name], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Deleted local tag: {tag_name}")
        else:
            print(f"ℹ️  Local tag {tag_name} doesn't exist")
        
        # Delete remote tag (if exists)
        result = subprocess.run(['git', 'push', 'origin', '--delete', tag_name], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Deleted remote tag: {tag_name}")
        else:
            print(f"ℹ️  Remote tag {tag_name} doesn't exist or couldn't be deleted")
        
        return True
    except Exception as e:
        print(f"⚠️  Error deleting tag {tag_name}: {e}")
        return False


def create_git_tag(tag_name, message=None):
    """Create a new Git tag"""
    try:
        if message is None:
            message = f"Release {tag_name}"
        
        result = subprocess.run(['git', 'tag', '-a', tag_name, '-m', message], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Created git tag: {tag_name}")
            return True
        else:
            print(f"❌ Failed to create tag {tag_name}: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error creating tag {tag_name}: {e}")
        return False


def bump_version(version_part='patch'):
    """Bump version number"""
    current = get_current_version()
    if not current:
        print("❌ Could not get current version")
        return None
    
    try:
        major, minor, patch = map(int, current.split('.'))
        
        if version_part == 'major':
            major += 1
            minor = 0
            patch = 0
        elif version_part == 'minor':
            minor += 1
            patch = 0
        elif version_part == 'patch':
            patch += 1
        else:
            print(f"❌ Invalid version part: {version_part}")
            return None
        
        new_version = f"{major}.{minor}.{patch}"
        print(f"🔼 Bumping version from {current} to {new_version}")
        return new_version
        
    except ValueError as e:
        print(f"❌ Invalid version format {current}: {e}")
        return None


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Qbitcoin Version Manager')
    parser.add_argument('--bump', choices=['major', 'minor', 'patch'], 
                       help='Bump version part')
    parser.add_argument('--set', help='Set specific version (e.g., 1.0.7)')
    parser.add_argument('--current', action='store_true', 
                       help='Show current version')
    parser.add_argument('--sync', action='store_true', 
                       help='Sync all files to current version')
    parser.add_argument('--tag', action='store_true', 
                       help='Create git tag for current version')
    parser.add_argument('--fix-conflicts', action='store_true', 
                       help='Fix version conflicts by syncing everything')
    
    args = parser.parse_args()
    
    if args.current:
        version = get_current_version()
        print(f"Current version: {version}")
        return
    
    if args.fix_conflicts:
        print("🔧 Fixing version conflicts...")
        current = get_current_version()
        if current:
            # Delete any conflicting tags
            for v in ['1.0.3', '1.0.4', '1.0.5', '1.0.6']:
                delete_git_tag(f'v{v}')
            
            # Update all files to current version
            if update_all_versions(current):
                print(f"✅ All files synced to version {current}")
                
                # Create clean tag
                tag_name = f"v{current}"
                delete_git_tag(tag_name)  # Clean up if exists
                create_git_tag(tag_name, f"Qbitcoin v{current} - Version conflicts resolved")
            else:
                print("❌ Failed to sync all files")
        return
    
    new_version = None
    
    if args.set:
        new_version = args.set
    elif args.bump:
        new_version = bump_version(args.bump)
    
    if new_version:
        # Update version.py first
        version_file = 'qbitcoin/version.py'
        if update_version_in_file(version_file, new_version, {
            r'__version__\s*=\s*["\'][^"\']*["\']': '__version__ = "{version}"'
        }):
            # Then update all other files
            if update_all_versions(new_version):
                print(f"✅ Successfully updated to version {new_version}")
                
                if args.tag:
                    tag_name = f"v{new_version}"
                    delete_git_tag(tag_name)  # Clean up if exists
                    create_git_tag(tag_name, f"Qbitcoin v{new_version}")
            else:
                print("❌ Failed to update all files")
        else:
            print("❌ Failed to update version.py")
    
    elif args.sync:
        current = get_current_version()
        if current and update_all_versions(current):
            print(f"✅ All files synced to version {current}")
        else:
            print("❌ Failed to sync versions")
    
    elif args.tag:
        current = get_current_version()
        if current:
            tag_name = f"v{current}"
            delete_git_tag(tag_name)  # Clean up if exists
            create_git_tag(tag_name, f"Qbitcoin v{current}")
        else:
            print("❌ Could not get current version for tagging")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
