"""MCP server connection implementation."""

import logging
from ..transports import TransportType, create_transport

logger = logging.getLogger(__name__)

class MCPServerConnection:
    """Manages a connection to an MCP server with a specific transport"""
    
    def __init__(self, name, config, exit_stack):
        """
        Initialize a server connection.
        
        Args:
            name: Name of the server (used for identification)
            config: Server configuration dictionary
            exit_stack: AsyncExitStack for resource management
        """
        self.name = name
        self.config = config
        self.exit_stack = exit_stack
        self.session = None
        self.transport_type = self._determine_transport_type()
        self.tools = []
    
    def _determine_transport_type(self):
        """Determine the transport type from the server configuration."""
        if "type" in self.config and self.config["type"].lower() == "sse":
            return TransportType.SSE
        elif "command" in self.config and "args" in self.config:
            return TransportType.STDIO
        else:
            raise ValueError(f"Cannot determine transport type for server '{self.name}'")
    
    async def connect(self):
        """Establish connection to the MCP server and load available tools."""
        logger.info(f"Connecting to server '{self.name}' with transport {self.transport_type}")
        
        # Create transport and session
        _, self.session = await create_transport(
            self.transport_type, 
            self.config, 
            self.exit_stack
        )
        
        # Initialize the session
        await self.session.initialize()
        
        # Load available tools
        response = await self.session.list_tools()
        self.tools = response.tools
        
        tool_names = ", ".join(tool.name for tool in self.tools)
        logger.info(f"Server '{self.name}' provides tools: {tool_names}")
        
        return self.tools
    
    async def call_tool(self, tool_name, tool_args):
        """Call a tool on this server."""
        if not self.session:
            raise ValueError(f"No active session for server '{self.name}'")
        
        logger.info(f"Calling tool '{tool_name}' on server '{self.name}' with args: {tool_args}")
        result = await self.session.call_tool(tool_name, tool_args)
        return result 