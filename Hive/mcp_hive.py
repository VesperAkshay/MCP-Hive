#!/usr/bin/env python
"""
MCP-Hive - A modular, scalable Model Control Protocol client

This is the main entry point for the MCP-Hive system.
"""

import os
import sys
import asyncio
import logging
import argparse
from dotenv import load_dotenv

from src.core import MCPClient
from src.server import MCPWebServer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_cli(args):
    """Run the client in CLI mode"""
    client = MCPClient(args.config)
    
    try:
        # Initialize the client
        await client.initialize()
        
        # Connect to all servers
        await client.connect_all_servers()
        
        # Run CLI chat loop
        await client.chat_loop()
    finally:
        await client.cleanup()

async def run_server(args):
    """Run the client in web server mode"""
    client = MCPClient(args.config)
    
    try:
        # Initialize the client
        await client.initialize()
        
        # Connect to all servers
        await client.connect_all_servers()
        
        # Create and run web server
        logger.info(f"Starting web server on {args.host}:{args.port}")
        web_server = MCPWebServer(client)
        await web_server.run(host=args.host, port=args.port)
    finally:
        await client.cleanup()

def main():
    """Main entry point for MCP-Hive"""
    parser = argparse.ArgumentParser(description="MCP-Hive Client")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--server", action="store_true", help="Run as web server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind web server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind web server to")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Set up logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        if args.server:
            # Run in web server mode
            asyncio.run(run_server(args))
        else:
            # Run in CLI mode
            asyncio.run(run_cli(args))
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 