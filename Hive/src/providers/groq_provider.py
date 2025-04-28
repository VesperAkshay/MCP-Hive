"""Groq LLM provider implementation."""

import os
import json
import logging
from groq import Groq

from .provider_interface import LLMProviderInterface
from ..utils.schema_utils import clean_schema

logger = logging.getLogger(__name__)

class GroqProvider(LLMProviderInterface):
    """Groq LLM provider implementation"""
    
    def __init__(self, api_key):
        super().__init__()
        if not api_key:
            raise ValueError("GROQ_API_KEY not found. Please add it to your .env file.")
        
        self.model_name = os.getenv("GROQ_MODEL", "llama-3-70b-8192")
        self.api_key = api_key
        self.groq_client = None
    
    async def initialize(self):
        """Initialize the Groq client."""
        self.groq_client = Groq(api_key=self.api_key)
    
    def convert_tools(self, mcp_tools):
        """Convert MCP tools to Groq format"""
        groq_tools = []
        
        for tool in mcp_tools:
            # Clean schema to comply with Groq API requirements
            parameters = clean_schema(tool.inputSchema)
            
            # Create function declaration for each tool
            groq_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters
                }
            }
            
            groq_tools.append(groq_tool)
        
        self.function_declarations = groq_tools
        return groq_tools
    
    async def process_query(self, query, conversation_history, mcp_client):
        """Process a query using Groq"""
        # Format conversation for Groq API
        groq_messages = mcp_client.conversation_manager.format_messages_for_groq(conversation_history)
        
        # System message to guide Groq's behavior
        system_message = {
            "role": "system", 
            "content": "You are a helpful assistant that can use tools when needed. "
                      "Always use tools when available and appropriate for the task."
        }
        
        # Add system message at the beginning
        complete_messages = [system_message] + groq_messages
        
        # Send request to Groq with available tools
        response = self.groq_client.chat.completions.create(
            model=self.model_name,
            messages=complete_messages,
            tools=self.function_declarations,
            tool_choice="auto"
        )
        
        # Prepare collection for final response text
        final_text = []
        has_function_call = False
        function_call_part = None
        tool_name = None
        tool_args = None
        
        # Extract response
        if response.choices and response.choices[0].message:
            message = response.choices[0].message
            
            # Check for tool calls
            if hasattr(message, 'tool_calls') and message.tool_calls and len(message.tool_calls) > 0:
                has_function_call = True
                tool_call = message.tool_calls[0]
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                function_call_part = tool_call  # Store the whole tool call
            elif message.content:
                final_text.append(message.content)
        
        return {
            "has_function_call": has_function_call,
            "function_call_part": function_call_part,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "final_text": final_text,
            "provider": "groq"
        } 