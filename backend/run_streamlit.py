#!/usr/bin/env python
"""
MCP-Hive Streamlit App Launcher

This script launches the Streamlit app for MCP-Hive with proper environment setup.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the Streamlit app"""
    # Get the directory of this script
    script_dir = Path(__file__).parent.absolute()
    
    # Set the Streamlit app path
    app_path = script_dir / "streamlit_app.py"
    
    # Check if the app exists
    if not app_path.exists():
        print(f"Error: Streamlit app not found at {app_path}")
        sys.exit(1)
    
    # Launch Streamlit
    print(f"Launching Streamlit app from {app_path}")
    cmd = ["streamlit", "run", str(app_path), "--server.port=8501"]
    
    try:
        # Launch streamlit process
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nStreamlit app stopped")
    except Exception as e:
        print(f"Error launching Streamlit app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 