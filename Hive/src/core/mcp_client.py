"""Main MCP client implementation."""

import os
import logging
from contextlib import AsyncExitStack
from typing import Dict, Optional, Any, List

from ..config import ConfigManager
from ..database import ConversationManager
from ..providers import create_all_available_providers
from ..tools import MCPServerConnection
from ..utils import ensure_json_serializable

logger = logging.getLogger(__name__)

class MCPClient:
    """Unified MCP client with multi-server and multi-LLM provider support"""
    
    def __init__(self, config_path=None):
        """
        Initialize the MCP client.
        
        Args:
            config_path: Path to configuration file
        """
        # Initialize configuration
        self.config_manager = ConfigManager(config_path)
        
        # Initialize resource management
        self.exit_stack = AsyncExitStack()
        
        # Initialize server connections
        self.servers = {}
        
        # Available LLM providers and current selection
        self.providers = {}
        self.current_provider_name = None
        self.current_provider = None
        
        # Server tools registry for routing tool calls
        self.server_tools = {}  
        
        # Conversation history management
        db_path = os.getenv("CONVERSATION_DB_PATH", ":memory:")
        max_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", "8000"))
        self.conversation_manager = ConversationManager(db_path, max_tokens)
        
        # Initialize state
        self.latest_message_id = None
    
    async def initialize(self):
        """Initialize the client, including LLM providers and conversation history."""
        # Initialize all available LLM providers
        self.providers = await create_all_available_providers()
        
        if not self.providers:
            raise ValueError("No LLM providers configured. Please add API keys to environment variables.")
        
        # Set default provider
        default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "gemini")
        if default_provider not in self.providers:
            default_provider = next(iter(self.providers.keys()))
        
        self.current_provider_name = default_provider
        self.current_provider = self.providers[default_provider]
        
        # Initialize conversation
        self.conversation_manager.start_new_conversation()
        
        logger.info(f"Initialized MCP Client with {len(self.providers)} providers")
        logger.info(f"Default provider: {self.current_provider_name}")
    
    async def connect_all_servers(self):
        """Connect to all servers defined in the configuration."""
        all_servers = self.config_manager.get_all_servers()
        
        if not all_servers:
            logger.warning("No MCP servers defined in configuration")
            return
        
        # Collect all tools from all servers
        all_tools = []
        
        for server_name, server_config in all_servers.items():
            try:
                server_conn = MCPServerConnection(server_name, server_config, self.exit_stack)
                self.servers[server_name] = server_conn
                
                # Connect to the server and get its tools
                tools = await server_conn.connect()
                
                # Register each tool with its server
                for tool in tools:
                    self.server_tools[tool.name] = server_conn
                
                # Add tools to our collection
                all_tools.extend(tools)
                
                logger.info(f"Successfully connected to server '{server_name}'")
            except Exception as e:
                logger.error(f"Failed to connect to server '{server_name}': {e}")
        
        # After connecting to all servers, convert the combined tools for each provider
        for provider in self.providers.values():
            provider.convert_tools(all_tools)
        
        logger.info(f"Connected to {len(self.servers)} servers with {len(self.server_tools)} total tools")
    
    async def connect_to_server(self, server_name):
        """Connect to a specific server by name."""
        server_config = self.config_manager.get_server_config(server_name)
        if not server_config:
            raise ValueError(f"Server '{server_name}' not found in configuration")
        
        try:
            server_conn = MCPServerConnection(server_name, server_config, self.exit_stack)
            self.servers[server_name] = server_conn
            
            # Connect to the server and get its tools
            tools = await server_conn.connect()
            
            # Register each tool with its server
            for tool in tools:
                self.server_tools[tool.name] = server_conn
            
            # Collect all tools from all servers including the new ones
            all_tools = []
            for server in self.servers.values():
                all_tools.extend(server.tools)
            
            # Convert the combined tools for each provider
            for provider in self.providers.values():
                provider.convert_tools(all_tools)
            
            logger.info(f"Successfully connected to server '{server_name}'")
            return tools
        except Exception as e:
            logger.error(f"Failed to connect to server '{server_name}': {e}")
            raise
    
    async def set_provider(self, provider_name):
        """Change the active LLM provider."""
        if provider_name not in self.providers:
            available = ", ".join(self.providers.keys())
            return f"Provider '{provider_name}' not available. Use one of: {available}"
        
        self.current_provider_name = provider_name
        self.current_provider = self.providers[provider_name]
        return f"Switched to {provider_name} provider"
    
    async def process_query(self, query, conversation_id=None):
        """
        Process a user query through the current LLM provider with tool-calling capabilities.
        
        Args:
            query: The user's text input
            conversation_id: Optional conversation ID to use (if None, uses current conversation)
            
        Returns:
            Dict containing response text and metadata
        """
        # Set the active conversation if specified
        if conversation_id and conversation_id != self.conversation_manager.current_conversation_id:
            self.conversation_manager.current_conversation_id = conversation_id
        
        # Handle provider switching command
        if query.lower().startswith("use provider "):
            provider = query[13:].strip()
            result = await self.set_provider(provider)
            return {"response": result, "conversation_id": self.conversation_manager.current_conversation_id}
        
        # Add user query to conversation history
        user_msg_id = self.conversation_manager.add_message(
            role='user',
            content=query,
            llm_provider=self.current_provider_name
        )
        self.latest_message_id = user_msg_id
        
        # Get conversation context from database
        conversation_history = self.conversation_manager.get_conversation_for_context(
            latest_message_id=user_msg_id,
            include_all_paths=False
        )
        
        # Process with current LLM provider
        final_text = []
        
        # Continue processing tool calls until LLM provides a final answer
        try:
            while True:
                # Get response from current LLM provider
                llm_response = await self.current_provider.process_query(
                    query, 
                    conversation_history, 
                    self
                )
                
                has_function_call = llm_response["has_function_call"]
                function_call_part = llm_response["function_call_part"]
                tool_name = llm_response["tool_name"]
                tool_args = llm_response["tool_args"]
                provider = llm_response["provider"]
                
                # Collect any text responses
                if llm_response["final_text"]:
                    final_text.extend(llm_response["final_text"])
                
                # Process function calls if present
                if has_function_call:
                    logger.info(f"LLM requested tool call: {tool_name} with args {tool_args}")
                    
                    # Add model's tool call to conversation history
                    model_msg_id = self.conversation_manager.add_message(
                        role='model',
                        parent_id=self.latest_message_id,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        content=None,
                        llm_provider=provider
                    )
                    self.latest_message_id = model_msg_id
                    
                    # Find the server that provides this tool
                    server_conn = self.server_tools.get(tool_name)
                    if not server_conn:
                        logger.error(f"Tool '{tool_name}' not found on any connected server")
                        function_response = {"error": f"Tool '{tool_name}' not available. Available tools are: {', '.join(self.server_tools.keys())}"}
                    else:
                        # Execute the requested tool
                        try:
                            result = await server_conn.call_tool(tool_name, tool_args)
                            function_response = {"result": result.content}
                        except Exception as e:
                            logger.error(f"Error executing tool '{tool_name}': {e}")
                            function_response = {"error": str(e)}
                    
                    # Add tool response to conversation history
                    tool_msg_id = self.conversation_manager.add_message(
                        role='tool',
                        parent_id=model_msg_id,
                        tool_name=tool_name,
                        tool_result=ensure_json_serializable(function_response),
                        content=None,
                        llm_provider=provider
                    )
                    self.latest_message_id = tool_msg_id
                    
                    # Get updated conversation history
                    conversation_history = self.conversation_manager.get_conversation_for_context(
                        latest_message_id=tool_msg_id,
                        include_all_paths=False
                    )
                else:
                    # No more function calls, exit the loop
                    break
            
            # Add final model response to conversation history
            final_response = "\n".join([text for text in final_text if text is not None and text.strip()])
            if final_response:
                final_msg_id = self.conversation_manager.add_message(
                    role='model',
                    parent_id=self.latest_message_id,
                    content=final_response,
                    llm_provider=provider
                )
                self.latest_message_id = final_msg_id
            
            # Filter out None values and empty strings
            filtered_text = [text for text in final_text if text is not None and text.strip()]
            
            # Return empty string if no valid responses
            if not filtered_text:
                response_text = "No response generated."
            else:
                # Combine all response segments
                response_text = "\n".join(filtered_text)
            
            return {
                "response": response_text,
                "conversation_id": self.conversation_manager.current_conversation_id,
                "provider": self.current_provider_name
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "response": f"Error: {str(e)}",
                "conversation_id": self.conversation_manager.current_conversation_id,
                "error": str(e)
            }
    
    async def chat_loop(self):
        """Run interactive chat session between user and LLM."""
        provider_list = ", ".join(self.providers.keys())
        print(f"\nMCP-Hive Client Started! Available providers: {provider_list}")
        print(f"Current provider: {self.current_provider_name}")
        print(f"Type 'use provider <name>' to switch providers. Type 'quit' to exit.")
        
        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == 'quit':
                break
            
            result = await self.process_query(query)
            print("\n" + result["response"])
    
    async def cleanup(self):
        """Clean up resources and close connections."""
        logger.info("Cleaning up resources")
        
        # Close conversation manager
        self.conversation_manager.close()
        
        # Close all server connections via the exit stack
        await self.exit_stack.aclose() 