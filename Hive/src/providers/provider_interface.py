"""Base interface for LLM providers."""

from abc import ABC, abstractmethod

class LLMProviderInterface(ABC):
    """Base interface for different LLM providers"""
    
    def __init__(self):
        self.function_declarations = None
    
    @abstractmethod
    async def initialize(self):
        """Initialize the LLM provider"""
        pass
    
    @abstractmethod
    async def process_query(self, query, conversation_history, mcp_client):
        """
        Process a query using this LLM provider
        
        Args:
            query: User query text
            conversation_history: List of message objects from conversation history
            mcp_client: Reference to the MCP client for tool execution
            
        Returns:
            Dict containing:
            - has_function_call (bool): Whether the response contains a function call
            - function_call_part: Function call details (provider-specific)
            - tool_name (str): Name of the tool to call, if applicable
            - tool_args (dict): Arguments for the tool, if applicable
            - final_text (list): List of text response segments
            - provider (str): Provider identifier
        """
        pass
    
    @abstractmethod
    def convert_tools(self, mcp_tools):
        """
        Convert MCP tools to provider-specific format
        
        Args:
            mcp_tools: List of MCP tool definitions
            
        Returns:
            Provider-specific representation of tools
        """
        pass 