"""Factory for creating different MCP transport types."""

import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

logger = logging.getLogger(__name__)

async def create_transport(transport_type, config, exit_stack):
    """
    Factory method to create the appropriate transport based on type.
    
    Args:
        transport_type: The transport type (stdio, sse)
        config: Transport configuration dictionary
        exit_stack: AsyncExitStack for resource management
        
    Returns:
        Tuple containing: (transport_streams, session)
    """
    if transport_type == "stdio":
        return await create_stdio_transport(config, exit_stack)
    elif transport_type == "sse":
        return await create_sse_transport(config, exit_stack)
    else:
        raise ValueError(f"Unsupported transport type: {transport_type}")

async def create_stdio_transport(config, exit_stack):
    """
    Create a StdIO-based MCP transport.
    
    Args:
        config: Dictionary containing 'command' and 'args' keys
        exit_stack: AsyncExitStack for resource management
        
    Returns:
        Tuple containing (transport_streams, session)
    """
    if "command" not in config or "args" not in config:
        raise ValueError("StdIO transport requires 'command' and 'args' in configuration")
    
    server_params = StdioServerParameters(
        command=config["command"],
        args=config["args"]
    )
    
    transport_streams = await exit_stack.enter_async_context(stdio_client(server_params))
    read, write = transport_streams
    session = await exit_stack.enter_async_context(ClientSession(read, write))
    
    return transport_streams, session

async def create_sse_transport(config, exit_stack):
    """
    Create an SSE-based MCP transport.
    
    Args:
        config: Dictionary containing 'url' key
        exit_stack: AsyncExitStack for resource management
        
    Returns:
        Tuple containing (transport_streams, session)
    """
    if "url" not in config:
        raise ValueError("SSE transport requires 'url' in configuration")
    
    transport_streams = await exit_stack.enter_async_context(sse_client(url=config["url"]))
    session = await exit_stack.enter_async_context(ClientSession(*transport_streams))
    
    return transport_streams, session 