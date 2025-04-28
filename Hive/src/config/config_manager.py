"""Configuration manager for MCP-Hive backend."""

import os
import json
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Handles configuration loading and management"""
    
    def __init__(self, config_path=None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the JSON configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from the specified JSON file or find a default one."""
        if self.config_path:
            # Use the specified config path
            try:
                with open(self.config_path, "r") as f:
                    logger.info(f"Loading configuration from {self.config_path}")
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config from '{self.config_path}': {e}")
                raise ValueError(f"Failed to load config from '{self.config_path}': {e}")
        else:
            # Try to locate a default config file
            default_locations = [
                "Mcphive_config.json",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "Mcphive_config.json"),
                os.path.join(os.getcwd(), "Mcphive_config.json")
            ]
            
            for location in default_locations:
                try:
                    with open(location, "r") as f:
                        logger.info(f"Loading configuration from {location}")
                        return json.load(f)
                except (FileNotFoundError, IsADirectoryError):
                    continue
            
            # If no config file found, use a minimal default configuration
            logger.warning("No config file found. Using default minimal configuration.")
            return {"mcpServers": {}}
    
    def get_server_config(self, server_name):
        """Get configuration for a specific MCP server."""
        servers = self.config.get("mcpServers", {})
        return servers.get(server_name)
    
    def get_all_servers(self):
        """Get configurations for all MCP servers."""
        return self.config.get("mcpServers", {})
    
    def get_server_names(self):
        """Get names of all configured servers."""
        return list(self.config.get("mcpServers", {}).keys()) 