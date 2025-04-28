"""Google Gemini LLM provider implementation."""

import os
import logging
import google.generativeai as genai
from google.api_core.exceptions import InvalidArgument

from .provider_interface import LLMProviderInterface
from ..utils.schema_utils import clean_schema

logger = logging.getLogger(__name__)

class GeminiProvider(LLMProviderInterface):
    """Gemini LLM provider implementation"""
    
    def __init__(self, api_key):
        super().__init__()
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found. Please add it to your .env file.")
        
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")
        self.api_key = api_key
        self.genai_client = None
    
    async def initialize(self):
        """Initialize the Gemini client."""
        self.genai_client = genai.Client(api_key=self.api_key)
    
    def convert_tools(self, mcp_tools):
        """Convert MCP tools to Gemini format"""
        gemini_tools = []
        
        for tool in mcp_tools:
            # Clean schema to comply with Gemini API requirements
            parameters = clean_schema(tool.inputSchema)
            
            # Create function declaration for each tool
            function_declaration = {
                "name": tool.name,
                "description": tool.description,
                "parameters": parameters
            }
            
            # Wrap in Gemini Tool object
            gemini_tool = {"function_declarations": [function_declaration]}
            gemini_tools.append(gemini_tool)
        
        self.function_declarations = gemini_tools
        return gemini_tools
    
    async def process_query(self, query, conversation_history, mcp_client):
        """Process a query using Gemini"""
        # Format conversation for Gemini API
        gemini_messages = mcp_client.conversation_manager.format_messages_for_gemini(conversation_history)
        
        # Send initial request to Gemini with available tools
        response = self.genai_client.models.generate_content(
            model=self.model_name,
            contents=gemini_messages,
            tools=self.function_declarations,
        )
        
        # Prepare collection for final response text
        final_text = []
        has_function_call = False
        function_call_part = None
        tool_name = None
        tool_args = None
        
        # Process Gemini's response, handling any tool execution requests
        for candidate in response.candidates:
            if not candidate.content or not candidate.content.parts:
                continue
                
            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    # We found a function call
                    has_function_call = True
                    function_call_part = part
                    tool_name = function_call_part.function_call.name
                    tool_args = function_call_part.function_call.args
                    break
                elif hasattr(part, 'text') and part.text and part.text.strip():
                    final_text.append(part.text)
        
        return {
            "has_function_call": has_function_call,
            "function_call_part": function_call_part,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "final_text": final_text,
            "provider": "gemini"
        } 