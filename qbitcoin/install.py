import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
import argparse

def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return the result."""
    print(f"Running: {cmd}")
    if isinstance(cmd, str):
        cmd = cmd.split()
    
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    
    if check and result.returncode != 0:
        print(f"Command failed with return code {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd)
    
    return result

def fix_cpp_files(source_dir, package_name):
    """Fix C++ files by adding missing #include <cstdint> headers."""
    print(f"Fixing C++ files for {package_name}...")
    
    # Files that need the cstdint include for different packages
    files_to_fix = {
        "pyqrllib": [
            "src/dilithium/dilithium.h",
            "src/dilithium/dilithium.cpp",
            "src/kyber/kyber.h",
            "src/kyber/kyber.cpp",
            "src/qrl/misc.h",
        ],
        "pyqrandomx": [
            "src/qrandomx/qrandomx.h",
            "src/qrandomx/qrandomx.cpp",
            "src/pow/powhelper.h",
            "src/misc/strbignum.h",
            "src/qrandomx/threadedqrandomx.h",
            "src/qrandomx/qrxminer.h",
            "src/qrandomx/rx-slow-hash.c",  # Also fix the C file
        ],
        "pyqryptonight": [
            "src/qryptonight/qryptonight.h",
            "src/qryptonight/qryptominer.h",
            "src/pow/powhelper.h",
            "src/misc/strbignum.h",
            "deps/xmr-stak/xmrstak/misc/console.hpp",  # Needs cstdio for FILE
            "deps/xmr-stak/xmrstak/backend/cpu/crypto/cryptonight_types.h",
        ]
    }
    
    if package_name not in files_to_fix:
        print(f"No files to fix for package {package_name}")
        return
    
    for file_path in files_to_fix[package_name]:
        full_path = source_dir / file_path
        if full_path.exists():
            print(f"Fixing {file_path}...")
            
            # Read the file
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Special handling for C files and specific header files
            if file_path.endswith('.c'):
                # For C files, we need to add different includes
                if 'rx-slow-hash.c' in file_path:
                    # Add unistd.h for _exit function
                    if '#include <unistd.h>' not in content:
                        # Find a good place to insert the include
                        lines = content.split('\n')
                        insert_index = 0
                        
                        # Look for the first #include line and insert after it
                        found_include = False
                        for i, line in enumerate(lines):
                            stripped = line.strip()
                            if stripped.startswith('#include'):
                                insert_index = i + 1
                                found_include = True
                            elif found_include and not stripped.startswith('#include'):
                                # We've found all the includes, insert before the next line
                                break
                        
                        # Insert the include
                        lines.insert(insert_index, '#include <unistd.h>')
                        
                        # Write back the modified content
                        with open(full_path, 'w') as f:
                            f.write('\n'.join(lines))
                        
                        print(f"Added #include <unistd.h> to {file_path} at line {insert_index + 1}")
                    else:
                        print(f"{file_path} already has #include <unistd.h>")
                continue
            
            # Special handling for console.hpp which needs cstdio for FILE
            if 'console.hpp' in file_path:
                if '#include <cstdio>' not in content:
                    # Find a good place to insert the include
                    lines = content.split('\n')
                    insert_index = 0
                    
                    # Look for the first #include line and insert after it
                    found_include = False
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped.startswith('#include'):
                            insert_index = i + 1
                            found_include = True
                        elif found_include and not stripped.startswith('#include'):
                            # We've found all the includes, insert before the next line
                            break
                    
                    # Insert the include
                    lines.insert(insert_index, '#include <cstdio>')
                    
                    # Write back the modified content
                    with open(full_path, 'w') as f:
                        f.write('\n'.join(lines))
                    
                    print(f"Added #include <cstdio> to {file_path} at line {insert_index + 1}")
                else:
                    print(f"{file_path} already has #include <cstdio>")
                continue
            
            # Check if cstdint is already included
            if '#include <cstdint>' not in content:
                # Find a good place to insert the include
                lines = content.split('\n')
                insert_index = 0
                
                # Look for the first #include line and insert after it
                # or if no includes, insert at the beginning after any header guards
                found_include = False
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith('#include'):
                        insert_index = i + 1
                        found_include = True
                    elif found_include and not stripped.startswith('#include'):
                        # We've found all the includes, insert before the next line
                        break
                    elif not found_include and stripped.startswith('#ifndef') or stripped.startswith('#define'):
                        # Skip header guards
                        insert_index = i + 1
                
                # If no includes found, insert early in the file
                if not found_include and insert_index == 0:
                    # Find first non-empty, non-comment line
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped and not stripped.startswith('//') and not stripped.startswith('/*') and not stripped.startswith('#ifndef') and not stripped.startswith('#define'):
                            insert_index = i
                            break
                    if insert_index == 0:
                        insert_index = 0  # Insert at the very beginning if needed
                
                # Insert the include
                lines.insert(insert_index, '#include <cstdint>')
                
                # Write back the modified content
                with open(full_path, 'w') as f:
                    f.write('\n'.join(lines))
                
                print(f"Added #include <cstdint> to {file_path} at line {insert_index + 1}")
            else:
                print(f"{file_path} already has #include <cstdint>")
        else:
            print(f"Warning: {file_path} not found")

def install_package(package_name):
    """Download, fix, and install a single package."""
    print(f"\n=== Installing {package_name} ===")
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Working in temporary directory: {temp_dir}")
        
        # Download the source code
        print(f"Downloading {package_name} source code...")
        try:
            run_command(["pip", "download", "--no-binary", ":all:", "--no-deps", package_name], cwd=temp_dir)
        except subprocess.CalledProcessError:
            print(f"Failed to download {package_name} source. Trying alternative method...")
            # Try downloading from PyPI directly for known packages
            if package_name == "pyqrllib":
                run_command(["wget", "https://files.pythonhosted.org/packages/source/p/pyqrllib/pyqrllib-1.2.4.tar.gz"], cwd=temp_dir)
            elif package_name == "pyqrandomx":
                run_command(["wget", "https://files.pythonhosted.org/packages/source/p/pyqrandomx/pyqrandomx-0.3.2.tar.gz"], cwd=temp_dir)
            elif package_name == "pyqryptonight":
                run_command(["wget", "https://files.pythonhosted.org/packages/source/p/pyqryptonight/pyqryptonight-0.99.11.tar.gz"], cwd=temp_dir)
            else:
                print(f"No alternative download method for {package_name}")
                return 1
        
        # Find the downloaded tar.gz file
        tar_files = list(temp_path.glob("*.tar.gz"))
        if not tar_files:
            print("No tar.gz file found. Exiting.")
            return 1
        
        tar_file = tar_files[0]
        print(f"Found source archive: {tar_file}")
        
        # Extract the archive
        print("Extracting source archive...")
        run_command(["tar", "-xzf", str(tar_file)], cwd=temp_dir)
        
        # Find the extracted directory
        extracted_dirs = [d for d in temp_path.iterdir() if d.is_dir() and d.name.startswith(package_name)]
        if not extracted_dirs:
            print("No extracted directory found. Exiting.")
            return 1
        
        source_dir = extracted_dirs[0]
        print(f"Source directory: {source_dir}")
        
        # Fix the C++ files
        fix_cpp_files(source_dir, package_name)
        
        # Install the fixed version
        print(f"Installing the fixed {package_name}...")
        try:
            # First try to install build dependencies
            print("Installing build dependencies...")
            deps = ["cmake", "setuptools", "wheel", "pybind11"]
            if package_name == "pyqrandomx":
                deps.append("boost")  # pyqrandomx might need boost
            
            run_command(["pip", "install"] + deps)
            
            # Install the fixed package
            run_command(["pip", "install", "."], cwd=source_dir)
            
            print(f"Successfully installed {package_name}!")
            return 0
            
        except subprocess.CalledProcessError as e:
            print(f"Installation failed: {e}")
            print("You may need to install additional system dependencies:")
            print("sudo apt-get update")
            print("sudo apt-get install build-essential cmake libssl-dev libboost-all-dev")
            return 1

def main():
    """Main function to download, fix, and install QRL packages."""
    parser = argparse.ArgumentParser(description="Install QRL packages with C++ fixes")
    parser.add_argument("packages", nargs="*", default=["pyqrllib", "pyqrandomx", "pyqryptonight"],
                        help="Packages to install (default: pyqrllib pyqrandomx pyqryptonight)")
    parser.add_argument("--package", "-p", action="append", dest="single_packages",
                        help="Install a single package (can be used multiple times)")
    
    args = parser.parse_args()
    
    # Determine which packages to install
    if args.single_packages:
        packages = args.single_packages
    else:
        packages = args.packages
    
    print(f"Installing packages: {', '.join(packages)}")
    
    failed_packages = []
    
    for package in packages:
        try:
            result = install_package(package)
            if result != 0:
                failed_packages.append(package)
        except Exception as e:
            print(f"Error installing {package}: {e}")
            failed_packages.append(package)
    
    # Summary
    print(f"\n=== Installation Summary ===")
    successful_packages = [p for p in packages if p not in failed_packages]
    
    if successful_packages:
        print(f"Successfully installed: {', '.join(successful_packages)}")
    
    if failed_packages:
        print(f"Failed to install: {', '.join(failed_packages)}")
        return 1
    
    print("All packages installed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
