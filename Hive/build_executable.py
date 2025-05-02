#!/usr/bin/env python
"""
Build script for creating an executable backend for MCP-Hive.
This script compiles the Python backend into an executable using PyInstaller
and prepares it for packaging with Electron.
"""

import os
import sys
import shutil
import subprocess
import platform

# Directory setup
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT_DIR, 'dist')
BUILD_DIR = os.path.join(ROOT_DIR, 'build')
ELECTRON_RESOURCES_DIR = os.path.join(ROOT_DIR, '..', 'MCP-Hive-Desktop', 'resources', 'Hive')

def clean_directories():
    """Clean up previous build artifacts"""
    print("Cleaning up previous build directories...")
    for directory in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(directory):
            shutil.rmtree(directory)
    
    # Create electron resources directory if it doesn't exist
    if not os.path.exists(ELECTRON_RESOURCES_DIR):
        os.makedirs(ELECTRON_RESOURCES_DIR, exist_ok=True)

def install_dependencies():
    """Install required dependencies for building the executable"""
    print("Installing required dependencies...")
    
    # Create a temporary requirements file with only the minimal dependencies needed
    tmp_requirements = os.path.join(ROOT_DIR, 'tmp_requirements.txt')
    with open(tmp_requirements, 'w') as f:
        f.write("""# Core dependencies
fastapi>=0.115.12
uvicorn>=0.21.1
websockets>=11.0.1
python-dotenv>=1.0.1
anyio>=3.6.2

# MCP library - essential for the application
mcp>=1.4.1

# LLM providers (only Groq)
groq>=0.22.0

# Advanced AI capabilities
langchain>=0.3.21
langchain-mcp-adapters>=0.0.5
langgraph>=0.3.18

# Database
sqlalchemy>=2.0.0

# HTTP client
requests>=2.32.3
httpx>=0.24.0
sseclient-py>=1.8.0

# Document processing
python-docx>=1.1.2
pillow>=11.1.0

# Utilities
pydantic>=2.0.0
nest-asyncio>=1.6.0
streamlit>=1.44.1
""")
    
    # Install the dependencies
    print("Installing MCP, Groq and other dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", tmp_requirements, "--upgrade"],
        check=False,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("Error installing dependencies:")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    
    # Install PyInstaller
    print("Installing PyInstaller...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "pyinstaller>=6.13.0"],
        check=False,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("Error installing PyInstaller:")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    
    # Cleanup
    os.remove(tmp_requirements)

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable with PyInstaller...")
    
    # Determine PyInstaller command based on platform
    pyinstaller_cmd = sys.executable + " -m PyInstaller"
    
    # Run PyInstaller with the spec file
    command = f"{pyinstaller_cmd} mcp_hive_backend.spec"
    result = subprocess.run(
        command,
        shell=True,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("PyInstaller failed:")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    
    print("Executable built successfully.")

def copy_resources():
    """Copy necessary resources for the Electron app"""
    print("Copying resources for Electron packaging...")
    
    # Copy the executable
    exe_name = "mcp_hive_backend.exe" if platform.system() == "Windows" else "mcp_hive_backend"
    exe_path = os.path.join(DIST_DIR, exe_name)
    
    if not os.path.exists(exe_path):
        print(f"Error: Executable not found at {exe_path}")
        sys.exit(1)
    
    # Copy executable to Electron resources
    shutil.copy2(exe_path, ELECTRON_RESOURCES_DIR)
    
    # Copy configuration file
    config_file = os.path.join(ROOT_DIR, "Mcphive_config.json")
    if os.path.exists(config_file):
        shutil.copy2(config_file, ELECTRON_RESOURCES_DIR)
    
    # Create empty .env file in resources directory if it doesn't exist
    env_file = os.path.join(ELECTRON_RESOURCES_DIR, ".env")
    if not os.path.exists(env_file):
        with open(env_file, "w") as f:
            f.write("""# API Keys for LLM Providers (Replace with your actual keys)
GROQ_API_KEY=your_groq_api_key_here

# Default provider
DEFAULT_LLM_PROVIDER=groq

# Server settings
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
""")
    
    print("Resources copied successfully.")

def main():
    """Main build function"""
    print("Starting MCP-Hive backend packaging...")
    
    # Clean directories
    clean_directories()
    
    # Install dependencies
    install_dependencies()
    
    # Build executable
    build_executable()
    
    # Copy resources
    copy_resources()
    
    print("Backend packaging complete!")
    print(f"Executable and resources copied to: {ELECTRON_RESOURCES_DIR}")

if __name__ == "__main__":
    main() 