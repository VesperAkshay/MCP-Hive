#!/usr/bin/env python
"""
Unified MCP Client

This file implements a unified client for the Model Context Protocol, combining features from:
- client.py (StdIO transport)
- client_sse.py (SSE transport)
- mcp_client_config.py (Configuration management)

Features:
- Support for multiple transport methods (StdIO and SSE)
- Configuration-driven server connection
- Multiple LLM provider support (Gemini and Groq)
- Database-backed conversation history using SQLite
- FastAPI web server for GUI and API access
"""

import os
import json
import sys
import asyncio
import sqlite3
import logging
import argparse
import re
import time
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Union, Callable, Tuple
from datetime import datetime
from pathlib import Path
from contextlib import AsyncExitStack

# SSE-related imports
import requests
import sseclient

# FastAPI-related imports
import uvicorn
from fastapi import FastAPI, WebSocket, Request, BackgroundTasks, HTTPException, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# LLM Provider imports
import google.generativeai as genai
from google.api_core.exceptions import InvalidArgument
from groq import Groq

# MCP protocol imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

# LLM provider imports - Google Gemini
from google import genai
from google.genai import types as gemini_types
from google.genai.types import Tool as GeminiTool
from google.genai.types import FunctionDeclaration as GeminiFunctionDeclaration
from google.genai.types import GenerateContentConfig as GeminiGenerateContentConfig

# Environment variables
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Database and Conversation Management
# =============================================================================

class ConversationManager:
    """Manages conversation history using SQLite database with token-aware truncation."""
    
    def __init__(self, db_path=":memory:", max_tokens=8000):
        """
        Initialize the conversation manager with SQLite and tree structure.
        
        Args:
            db_path: Path to SQLite database file (default: in-memory)
            max_tokens: Maximum number of tokens to maintain in context
        """
        self.max_tokens = max_tokens
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.current_conversation_id = None
        self._setup_database()
        self._run_migrations()
    
    def _setup_database(self):
        """Create necessary database tables if they don't exist."""
        # Conversations table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            created_at INTEGER,
            last_updated INTEGER
        )
        ''')
        
        # Messages table with tree structure (parent_id for hierarchy)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            parent_id INTEGER,
            role TEXT,
            content TEXT,
            token_count INTEGER,
            timestamp INTEGER,
            type TEXT,
            tool_name TEXT,
            tool_args TEXT,
            tool_result TEXT,
            is_summarized INTEGER DEFAULT 0,
            llm_provider TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id),
            FOREIGN KEY (parent_id) REFERENCES messages (id)
        )
        ''')
        
        self.conn.commit()
    
    def _run_migrations(self):
        """Run database migrations to update schema when needed."""
        # This is a placeholder for future migrations
        pass
    
    def start_new_conversation(self, title=None):
        """Create a new conversation in the database."""
        timestamp = int(time.time())
        title = title or f"Conversation {timestamp}"
        
        self.cursor.execute(
            "INSERT INTO conversations (title, created_at, last_updated) VALUES (?, ?, ?)",
            (title, timestamp, timestamp)
        )
        self.conn.commit()
        
        self.current_conversation_id = self.cursor.lastrowid
        return self.current_conversation_id
    
    def _estimate_token_count(self, text):
        """
        Estimate the number of tokens in a string.
        Simple approximation - actual tokenizers would be more accurate.
        """
        # Very rough estimation: ~4 characters per token for English text
        if not text:
            return 0
        return len(text) // 4 + 1
    
    def add_message(self, role, content, parent_id=None, tool_name=None, tool_args=None, 
                   tool_result=None, llm_provider=None):
        """
        Add a message to the current conversation tree.
        
        Args:
            role: Message role (user, model, tool)
            content: Message content
            parent_id: Parent message ID (for tree structure)
            tool_name: Name of tool if message is a tool call
            tool_args: Tool arguments if applicable
            tool_result: Tool execution result if applicable
            llm_provider: Which LLM provider was used (gemini, groq)
        
        Returns:
            ID of the inserted message
        """
        if not self.current_conversation_id:
            self.start_new_conversation()
        
        timestamp = int(time.time())
        
        # Determine message type
        if tool_name:
            msg_type = "tool_call" if not tool_result else "tool_result"
        else:
            msg_type = "text"
        
        # Estimate token count
        token_count = self._estimate_token_count(content or "")
        if tool_args:
            token_count += self._estimate_token_count(json.dumps(tool_args))
        if tool_result:
            token_count += self._estimate_token_count(json.dumps(tool_result))
        
        # Store in database
        self.cursor.execute(
            """
            INSERT INTO messages 
            (conversation_id, parent_id, role, content, token_count, timestamp, type, 
             tool_name, tool_args, tool_result, llm_provider) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.current_conversation_id, 
                parent_id, 
                role, 
                content, 
                token_count, 
                timestamp, 
                msg_type, 
                tool_name, 
                json.dumps(tool_args) if tool_args else None, 
                json.dumps(tool_result) if tool_result else None,
                llm_provider
            )
        )
        self.conn.commit()
        
        # Update conversation last_updated timestamp
        self.cursor.execute(
            "UPDATE conversations SET last_updated = ? WHERE id = ?",
            (timestamp, self.current_conversation_id)
        )
        self.conn.commit()
        
        return self.cursor.lastrowid

    def _get_path_to_message(self, message_id):
        """Get the path from root to a specific message (for tree traversal)."""
        path = []
        current_id = message_id
        
        while current_id:
            self.cursor.execute(
                "SELECT id, parent_id FROM messages WHERE id = ?", 
                (current_id,)
            )
            row = self.cursor.fetchone()
            if not row:
                break
                
            path.append(row['id'])
            current_id = row['parent_id']
        
        return list(reversed(path))
    
    def get_conversation_for_context(self, latest_message_id=None, include_all_paths=False):
        """
        Retrieve messages for context window while respecting token budget.
        Uses tree structure to prioritize the current conversation path.
        
        Args:
            latest_message_id: ID of the latest message to use as reference point
            include_all_paths: Whether to include all paths in the tree or just the current path
            
        Returns:
            List of messages as raw database rows (not formatted for any specific LLM)
        """
        if not self.current_conversation_id:
            return []
        
        # Get the most recent message if not specified
        if not latest_message_id:
            self.cursor.execute(
                "SELECT id FROM messages WHERE conversation_id = ? ORDER BY timestamp DESC LIMIT 1", 
                (self.current_conversation_id,)
            )
            result = self.cursor.fetchone()
            if result:
                latest_message_id = result['id']
            else:
                return []  # No messages
        
        # Get the path to the latest message
        current_path = self._get_path_to_message(latest_message_id)
        
        # Gather all messages, prioritizing the current path
        all_messages = []
        token_budget = self.max_tokens
        
        # First add messages in the current path
        if current_path:
            placeholders = ', '.join('?' for _ in current_path)
            self.cursor.execute(
                f"""
                SELECT * FROM messages 
                WHERE id IN ({placeholders})
                ORDER BY timestamp ASC
                """, 
                current_path
            )
            path_messages = self.cursor.fetchall()
            
            # Add these messages first (they're the highest priority)
            for msg in path_messages:
                all_messages.append(msg)
                token_budget -= msg['token_count']
        
        # If we want to include other branches and have remaining token budget
        if include_all_paths and token_budget > 0:
            # Get messages not in the current path, ordered by recency
            if current_path:
                placeholders = ', '.join('?' for _ in current_path)
                self.cursor.execute(
                    f"""
                    SELECT * FROM messages 
                    WHERE conversation_id = ? AND id NOT IN ({placeholders})
                    ORDER BY timestamp DESC
                    LIMIT 100  # Reasonable limit to avoid processing too many messages
                    """, 
                    [self.current_conversation_id] + current_path
                )
            else:
                self.cursor.execute(
                    """
                    SELECT * FROM messages 
                    WHERE conversation_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 100
                    """, 
                    (self.current_conversation_id,)
                )
                
            other_messages = self.cursor.fetchall()
            
            # Add as many as fit in the token budget
            for msg in other_messages:
                if token_budget - msg['token_count'] >= 0:
                    all_messages.append(msg)
                    token_budget -= msg['token_count']
                else:
                    break
        
        return sorted(all_messages, key=lambda x: x['timestamp'])
    
    def format_messages_for_gemini(self, messages):
        """Convert database messages to Gemini API format."""
        gemini_messages = []
        
        for msg in messages:
            if msg['type'] == 'text':
                # Regular text message
                gemini_messages.append(gemini_types.Content(
                    role=msg['role'],
                    parts=[gemini_types.Part.from_text(text=msg['content'])]
                ))
            elif msg['type'] == 'tool_call':
                # Tool call message
                function_call = {
                    'name': msg['tool_name'],
                    'args': json.loads(msg['tool_args']) if msg['tool_args'] else {}
                }
                
                gemini_messages.append(gemini_types.Content(
                    role=msg['role'],
                    parts=[gemini_types.Part(function_call=function_call)]
                ))
            elif msg['type'] == 'tool_result':
                # Tool result message
                function_response = {
                    'name': msg['tool_name'],
                    'response': {'result': json.loads(msg['tool_result'])} if msg['tool_result'] else {}
                }
                
                gemini_messages.append(gemini_types.Content(
                    role='tool',
                    parts=[gemini_types.Part.from_function_response(
                        name=msg['tool_name'],
                        response=json.loads(msg['tool_result']) if msg['tool_result'] else {}
                    )]
                ))
        
        return gemini_messages
    
    def format_messages_for_groq(self, messages):
        """Convert database messages to Groq API format."""
        groq_messages = []
        
        for msg in messages:
            if msg['type'] == 'text':
                # Regular text message
                role = "assistant" if msg['role'] == "model" else msg['role']
                groq_messages.append({
                    "role": role,
                    "content": msg['content']
                })
            elif msg['type'] == 'tool_call':
                # Tool call message (from assistant)
                if msg['role'] == 'model':
                    # Structure for assistant's tool call
                    groq_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": f"call_{msg['id']}",
                            "type": "function",
                            "function": {
                                "name": msg['tool_name'],
                                "arguments": json.dumps(json.loads(msg['tool_args']) if msg['tool_args'] else {})
                            }
                        }]
                    })
            elif msg['type'] == 'tool_result':
                # Tool result message (from tool)
                groq_messages.append({
                    "role": "tool",
                    "content": json.dumps(json.loads(msg['tool_result']) if msg['tool_result'] else {}),
                    "tool_call_id": f"call_{msg['parent_id']}"
                })
        
        return groq_messages
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

# =============================================================================
# LLM Provider Interface 
# =============================================================================

class LLMProviderInterface:
    """Base interface for different LLM providers"""
    
    def __init__(self):
        self.function_declarations = None
    
    async def initialize(self):
        """Initialize the LLM provider"""
        pass
    
    async def process_query(self, query, conversation_history, mcp_client):
        """Process a query using this LLM provider"""
        raise NotImplementedError("Subclasses must implement process_query")
    
    def convert_tools(self, mcp_tools):
        """Convert MCP tools to provider-specific format"""
        raise NotImplementedError("Subclasses must implement convert_tools")

class GeminiProvider(LLMProviderInterface):
    """Gemini LLM provider implementation"""
    
    def __init__(self, api_key):
        super().__init__()
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found. Please add it to your .env file.")
        
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")
        self.genai_client = genai.Client(api_key=api_key)
    
    def convert_tools(self, mcp_tools):
        """Convert MCP tools to Gemini format"""
        gemini_tools = []
        
        for tool in mcp_tools:
            # Clean schema to comply with Gemini API requirements
            parameters = clean_schema(tool.inputSchema)
            
            # Create function declaration for each tool
            function_declaration = GeminiFunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=parameters
            )
            
            # Wrap in Gemini Tool object
            gemini_tool = GeminiTool(function_declarations=[function_declaration])
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
            config=GeminiGenerateContentConfig(
                tools=self.function_declarations,
            ),
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
                if not isinstance(part, gemini_types.Part):
                    continue
                    
                if part.function_call:
                    # We found a function call
                    has_function_call = True
                    function_call_part = part
                    tool_name = function_call_part.function_call.name
                    tool_args = function_call_part.function_call.args
                    break
                elif part.text and part.text.strip():
                    final_text.append(part.text)
        
        return {
            "has_function_call": has_function_call,
            "function_call_part": function_call_part,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "final_text": final_text,
            "provider": "gemini"
        }

class GroqProvider(LLMProviderInterface):
    """Groq LLM provider implementation"""
    
    def __init__(self, api_key):
        super().__init__()
        if not api_key:
            raise ValueError("GROQ_API_KEY not found. Please add it to your .env file.")
        
        self.model_name = os.getenv("GROQ_MODEL", "llama-3-70b-8192")
        self.groq_client = Groq(api_key=api_key)
    
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

# Helper function for schema cleaning
def clean_schema(schema):
    """
    Remove fields from JSON schemas to ensure compatibility with LLM APIs.
    
    Args:
        schema: JSON schema dictionary
        
    Returns:
        Cleaned schema dictionary suitable for LLM APIs
    """
    if isinstance(schema, dict):
        # Remove problematic fields that might cause validation errors
        keys_to_remove = ["title", "$schema", "additionalProperties", "$id", "default", "examples"]
        for key in keys_to_remove:
            schema.pop(key, None)
        
        # Process type field if it's a list (some LLMs don't support multiple types)
        if "type" in schema and isinstance(schema["type"], list):
            # Use the first type in the list
            schema["type"] = schema["type"][0]
        
        # Recursively process nested properties
        if "properties" in schema and isinstance(schema["properties"], dict):
            for key in schema["properties"]:
                schema["properties"][key] = clean_schema(schema["properties"][key])
        
        # Process items for arrays
        if "items" in schema and isinstance(schema["items"], dict):
            schema["items"] = clean_schema(schema["items"])
        
        # Process oneOf, anyOf, allOf
        for key in ["oneOf", "anyOf", "allOf"]:
            if key in schema and isinstance(schema[key], list):
                schema[key] = [clean_schema(item) for item in schema[key]]
    
    return schema

# =============================================================================
# Transport Types
# =============================================================================

class TransportType(str, Enum):
    """Enumeration of supported transport types"""
    STDIO = "stdio"
    SSE = "sse"

# =============================================================================
# Configuration Management
# =============================================================================

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

# =============================================================================
# MCP Server Connection
# =============================================================================

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
        
        if self.transport_type == TransportType.STDIO:
            await self._connect_stdio()
        elif self.transport_type == TransportType.SSE:
            await self._connect_sse()
        else:
            raise ValueError(f"Unsupported transport type '{self.transport_type}'")
        
        # Initialize the session
        await self.session.initialize()
        
        # Load available tools
        response = await self.session.list_tools()
        self.tools = response.tools
        
        tool_names = ", ".join(tool.name for tool in self.tools)
        logger.info(f"Server '{self.name}' provides tools: {tool_names}")
        
        return self.tools
    
    async def _connect_stdio(self):
        """Connect using StdIO transport."""
        server_params = StdioServerParameters(
            command=self.config["command"],
            args=self.config["args"]
        )
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
    
    async def _connect_sse(self):
        """Connect using SSE transport."""
        if "url" not in self.config:
            raise ValueError(f"SSE server '{self.name}' requires a 'url' parameter")
        
        # Open an SSE connection to the server
        streams_context = sse_client(url=self.config["url"])
        streams = await self.exit_stack.enter_async_context(streams_context)
        
        # Create an MCP session using the SSE connection
        session_context = ClientSession(*streams)
        self.session = await self.exit_stack.enter_async_context(session_context)
    
    async def call_tool(self, tool_name, tool_args):
        """Call a tool on this server."""
        if not self.session:
            raise ValueError(f"No active session for server '{self.name}'")
        
        logger.info(f"Calling tool '{tool_name}' on server '{self.name}' with args: {tool_args}")
        result = await self.session.call_tool(tool_name, tool_args)
        return result

# =============================================================================
# Unified MCP Client
# =============================================================================

class UnifiedMCPClient:
    """Unified MCP client that supports multiple transport methods and servers"""
    
    def __init__(self, config_path=None):
        """
        Initialize the unified MCP client.
        
        Args:
            config_path: Path to the JSON configuration file
        """
        # Initialize configuration
        self.config_manager = ConfigManager(config_path)
        
        # Initialize resource management
        self.exit_stack = AsyncExitStack()
        
        # Initialize server connections
        self.servers = {}
        
        # Initialize LLM providers
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        self.providers = {}
        if gemini_api_key:
            self.providers["gemini"] = GeminiProvider(gemini_api_key)
        if groq_api_key:
            self.providers["groq"] = GroqProvider(groq_api_key)
            
        if not self.providers:
            raise ValueError("No LLM providers configured. Please add GEMINI_API_KEY or GROQ_API_KEY to your .env file.")
        
        # Set default provider
        default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "gemini")
        if default_provider not in self.providers:
            default_provider = next(iter(self.providers.keys()))
        
        self.current_provider_name = default_provider
        self.current_provider = self.providers[default_provider]
        
        # Initialize conversation manager
        db_path = os.getenv("CONVERSATION_DB_PATH", ":memory:")
        max_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", "8000"))
        self.conversation_manager = ConversationManager(db_path, max_tokens)
        self.conversation_manager.start_new_conversation()
        
        # Track the latest message ID for context retrieval
        self.latest_message_id = None
        
        # Initialize server-specific data
        self.server_tools = {}  # Maps tool names to server connections
        
        logger.info(f"Initialized Unified MCP Client with {len(self.providers)} providers")
    
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
                        tool_result=self._ensure_json_serializable(function_response),
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
        print(f"\nUnified MCP Client Started! Available providers: {provider_list}")
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
    
    def _ensure_json_serializable(self, obj):
        """
        Ensure an object is JSON serializable by converting complex objects to strings.
        
        Args:
            obj: Object to make JSON serializable
            
        Returns:
            JSON serializable version of the object
        """
        if isinstance(obj, dict):
            return {k: self._ensure_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._ensure_json_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Handle custom objects by converting to dict
            return self._ensure_json_serializable(obj.__dict__)
        elif hasattr(obj, 'to_dict'):
            # Use to_dict method if available
            return self._ensure_json_serializable(obj.to_dict())
        elif hasattr(obj, 'as_dict'):
            # Use as_dict method if available
            return self._ensure_json_serializable(obj.as_dict())
        else:
            # Convert anything else to string if it's not a primitive type
            if not isinstance(obj, (str, int, float, bool, type(None))):
                return str(obj)
            return obj 

# =============================================================================
# FastAPI Web Server
# =============================================================================

class MCPWebServer:
    """FastAPI web server for the MCP client"""
    
    def __init__(self, mcp_client):
        """
        Initialize the web server.
        
        Args:
            mcp_client: UnifiedMCPClient instance
        """
        self.mcp_client = mcp_client
        self.app = FastAPI(title="Unified MCP Client API", description="API for the Unified MCP Client")
        self.connected_websockets = set()
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify exact domains
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register FastAPI routes."""
        
        @self.app.get("/")
        async def get_home():
            """Return basic HTML page with client UI."""
            return HTMLResponse(self._get_home_html())
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "ok", "providers": list(self.mcp_client.providers.keys())}
        
        @self.app.get("/providers")
        async def get_providers():
            """List available LLM providers."""
            return {
                "providers": list(self.mcp_client.providers.keys()),
                "current": self.mcp_client.current_provider_name
            }
        
        @self.app.post("/providers/{provider_name}")
        async def set_provider(provider_name: str):
            """Set active LLM provider."""
            result = await self.mcp_client.set_provider(provider_name)
            return {"message": result}
        
        @self.app.get("/servers")
        async def get_servers():
            """List connected MCP servers."""
            server_info = {}
            for name, server in self.mcp_client.servers.items():
                tools = [{"name": tool.name, "description": tool.description} 
                         for tool in server.tools]
                server_info[name] = {
                    "transport": server.transport_type,
                    "tools": tools
                }
            
            return {"servers": server_info}
        
        @self.app.post("/chat")
        async def chat(request: Request, background_tasks: BackgroundTasks):
            """Process a chat message."""
            data = await request.json()
            query = data.get("query")
            conversation_id = data.get("conversation_id")
            
            if not query:
                return JSONResponse(
                    status_code=400,
                    content={"error": "No query provided"}
                )
            
            # Process the query
            result = await self.mcp_client.process_query(query, conversation_id)
            
            # Broadcast the result to WebSocket clients if requested
            if data.get("broadcast", False) and self.connected_websockets:
                background_tasks.add_task(self._broadcast_response, result)
            
            return result
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time chat."""
            await websocket.accept()
            self.connected_websockets.add(websocket)
            
            try:
                while True:
                    # Receive message from client
                    data = await websocket.receive_json()
                    query = data.get("query")
                    conversation_id = data.get("conversation_id")
                    
                    if not query:
                        await websocket.send_json({"error": "No query provided"})
                        continue
                    
                    # Process the query
                    result = await self.mcp_client.process_query(query, conversation_id)
                    
                    # Send response back to this client
                    await websocket.send_json(result)
                    
                    # Broadcast to other clients if requested
                    if data.get("broadcast", False):
                        await self._broadcast_response(result, exclude=websocket)
            
            except WebSocketDisconnect:
                self.connected_websockets.remove(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if websocket in self.connected_websockets:
                    self.connected_websockets.remove(websocket)
    
    async def _broadcast_response(self, result, exclude=None):
        """Broadcast a response to all connected WebSocket clients."""
        disconnected_ws = set()
        for ws in self.connected_websockets:
            if ws != exclude:
                try:
                    await ws.send_json(result)
                except Exception:
                    disconnected_ws.add(ws)
        
        # Remove disconnected WebSockets
        self.connected_websockets -= disconnected_ws
    
    def _get_home_html(self):
        """Return basic HTML for the home page."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Unified MCP Client</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    line-height: 1.6;
                }
                h1 {
                    color: #333;
                    text-align: center;
                }
                .chat-container {
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    padding: 20px;
                    margin-top: 20px;
                    height: 400px;
                    overflow-y: auto;
                    background-color: #f9f9f9;
                }
                .message {
                    margin-bottom: 10px;
                    padding: 10px;
                    border-radius: 5px;
                }
                .user {
                    background-color: #e6f7ff;
                    margin-left: 20%;
                    text-align: right;
                }
                .bot {
                    background-color: #f0f0f0;
                    margin-right: 20%;
                }
                .input-container {
                    display: flex;
                    margin-top: 20px;
                }
                #user-input {
                    flex-grow: 1;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    margin-right: 10px;
                }
                button {
                    padding: 10px 20px;
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                }
                button:hover {
                    background-color: #45a049;
                }
                .provider-container {
                    display: flex;
                    justify-content: center;
                    margin-top: 20px;
                    gap: 10px;
                }
                .provider-button {
                    padding: 5px 10px;
                    background-color: #f0f0f0;
                    color: #333;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    cursor: pointer;
                }
                .provider-button.active {
                    background-color: #4CAF50;
                    color: white;
                }
            </style>
        </head>
        <body>
            <h1>Unified MCP Client</h1>
            <div class="provider-container" id="providers"></div>
            <div class="chat-container" id="chat-box"></div>
            <div class="input-container">
                <input type="text" id="user-input" placeholder="Type your message...">
                <button onclick="sendMessage()">Send</button>
            </div>

            <script>
                let conversationId = null;
                let currentProvider = '';
                
                // Connect WebSocket
                const socket = new WebSocket(`ws://${window.location.host}/ws`);
                
                socket.onopen = () => {
                    console.log('WebSocket connected');
                    addBotMessage('Connected to server. Type a message to begin!');
                    loadProviders();
                };
                
                socket.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.error) {
                        addBotMessage(`Error: ${data.error}`);
                    } else {
                        addBotMessage(data.response);
                        conversationId = data.conversation_id;
                    }
                };
                
                socket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    addBotMessage('Error connecting to server. Please try again later.');
                };
                
                socket.onclose = () => {
                    console.log('WebSocket disconnected');
                    addBotMessage('Disconnected from server.');
                };
                
                async function loadProviders() {
                    try {
                        const response = await fetch('/providers');
                        const data = await response.json();
                        
                        const providersContainer = document.getElementById('providers');
                        providersContainer.innerHTML = '';
                        
                        data.providers.forEach(provider => {
                            const button = document.createElement('button');
                            button.textContent = provider;
                            button.className = 'provider-button';
                            if (provider === data.current) {
                                button.classList.add('active');
                                currentProvider = provider;
                            }
                            button.onclick = () => setProvider(provider);
                            providersContainer.appendChild(button);
                        });
                    } catch (error) {
                        console.error('Error loading providers:', error);
                    }
                }
                
                async function setProvider(provider) {
                    try {
                        const response = await fetch(`/providers/${provider}`, {
                            method: 'POST'
                        });
                        const data = await response.json();
                        
                        // Update active provider button
                        document.querySelectorAll('.provider-button').forEach(button => {
                            button.classList.remove('active');
                            if (button.textContent === provider) {
                                button.classList.add('active');
                                currentProvider = provider;
                            }
                        });
                        
                        addBotMessage(data.message);
                    } catch (error) {
                        console.error('Error setting provider:', error);
                    }
                }
                
                function sendMessage() {
                    const input = document.getElementById('user-input');
                    const message = input.value.trim();
                    
                    if (message) {
                        addUserMessage(message);
                        
                        // Send through WebSocket
                        socket.send(JSON.stringify({
                            query: message,
                            conversation_id: conversationId
                        }));
                        
                        input.value = '';
                    }
                }
                
                function addUserMessage(text) {
                    const chatBox = document.getElementById('chat-box');
                    const message = document.createElement('div');
                    message.className = 'message user';
                    message.textContent = text;
                    chatBox.appendChild(message);
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
                
                function addBotMessage(text) {
                    const chatBox = document.getElementById('chat-box');
                    const message = document.createElement('div');
                    message.className = 'message bot';
                    message.textContent = text;
                    chatBox.appendChild(message);
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
                
                // Allow sending message with Enter key
                document.getElementById('user-input').addEventListener('keypress', function(event) {
                    if (event.key === 'Enter') {
                        sendMessage();
                    }
                });
            </script>
        </body>
        </html>
        """
    
    def run(self, host="0.0.0.0", port=8000):
        """Run the web server."""
        uvicorn.run(self.app, host=host, port=port)

# =============================================================================
# Main Entry Point and CLI
# =============================================================================

async def main_async(args):
    """Main asynchronous entry point."""
    try:
        # Create the MCP client
        client = UnifiedMCPClient(args.config)
        
        # Connect to all servers
        await client.connect_all_servers()
        
        if args.server:
            # Run the web server
            logger.info(f"Starting web server on {args.host}:{args.port}")
            web_server = MCPWebServer(client)
            web_server.run(host=args.host, port=args.port)
        else:
            # Run interactive CLI
            try:
                await client.chat_loop()
            finally:
                await client.cleanup()
    except Exception as e:
        logger.error(f"Error in main_async: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Unified MCP Client")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--server", action="store_true", help="Run as web server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind web server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind web server to")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Set up logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run the async main function
    asyncio.run(main_async(args))

if __name__ == "__main__":
    main() 