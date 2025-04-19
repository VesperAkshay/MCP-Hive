# Import necessary libraries
import asyncio  # For handling asynchronous operations
import os       # For environment variable access
import sys      # For system-specific parameters and functions
import json     # For handling JSON data (used when printing function declarations)
import sqlite3
import time
from typing import Optional, Dict, List, Tuple, Any
from contextlib import AsyncExitStack  # For managing multiple async tasks
from mcp import ClientSession, StdioServerParameters  # MCP session management
from mcp.client.stdio import stdio_client  # MCP client for standard I/O communication

# Import Google's Gen AI SDK
from google import genai
from google.genai import types
from google.genai.types import Tool, FunctionDeclaration
from google.genai.types import GenerateContentConfig

from dotenv import load_dotenv  # For loading API keys from a .env file

# Load environment variables from .env file
load_dotenv()

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
            FOREIGN KEY (conversation_id) REFERENCES conversations (id),
            FOREIGN KEY (parent_id) REFERENCES messages (id)
        )
        ''')
        
        self.conn.commit()
    
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
        return len(text) // 4 + 1
    
    def add_message(self, role, content, parent_id=None, tool_name=None, tool_args=None, tool_result=None):
        """
        Add a message to the current conversation tree.
        
        Args:
            role: Message role (user, model, tool)
            content: Message content
            parent_id: Parent message ID (for tree structure)
            tool_name: Name of tool if message is a tool call
            tool_args: Tool arguments if applicable
            tool_result: Tool execution result if applicable
        
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
            (conversation_id, parent_id, role, content, token_count, timestamp, type, tool_name, tool_args, tool_result) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                json.dumps(tool_result) if tool_result else None
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
            List of messages formatted for Gemini API
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
                    LIMIT 100  -- Reasonable limit to avoid processing too many messages
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
        
        # Format messages for Gemini API
        gemini_messages = self._format_messages_for_gemini(all_messages)
        return gemini_messages
    
    def _format_messages_for_gemini(self, messages):
        """Convert database messages to Gemini API format."""
        gemini_messages = []
        
        for msg in sorted(messages, key=lambda x: x['timestamp']):
            if msg['type'] == 'text':
                # Regular text message
                gemini_messages.append(types.Content(
                    role=msg['role'],
                    parts=[types.Part.from_text(text=msg['content'])]
                ))
            elif msg['type'] == 'tool_call':
                # Tool call message
                function_call = {
                    'name': msg['tool_name'],
                    'args': json.loads(msg['tool_args']) if msg['tool_args'] else {}
                }
                
                gemini_messages.append(types.Content(
                    role=msg['role'],
                    parts=[types.Part(function_call=function_call)]
                ))
            elif msg['type'] == 'tool_result':
                # Tool result message
                function_response = {
                    'name': msg['tool_name'],
                    'response': {'result': json.loads(msg['tool_result'])} if msg['tool_result'] else {}
                }
                
                gemini_messages.append(types.Content(
                    role='tool',
                    parts=[types.Part.from_function_response(
                        name=msg['tool_name'],
                        response=json.loads(msg['tool_result']) if msg['tool_result'] else {}
                    )]
                ))
        
        return gemini_messages
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

class MCPClient:
    def __init__(self):
        """Initialize the MCP client with Gemini API configuration."""
        # Initialize session and resource management
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        
        # Configure Gemini API with key from environment variables
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found. Please add it to your .env file.")
        
        self.genai_client = genai.Client(api_key=gemini_api_key)
        
        # Initialize conversation manager with SQLite backend
        db_path = os.getenv("CONVERSATION_DB_PATH", ":memory:")
        max_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", "8000"))
        self.conversation_manager = ConversationManager(db_path, max_tokens)
        self.conversation_manager.start_new_conversation()
        
        # Track the latest message ID for context retrieval
        self.latest_message_id = None

    async def connect_to_server(self, server_script_path: str):
        """Establish connection to the MCP server and prepare tools for Gemini."""
        # Determine appropriate runtime environment (Python or Node.js)
        command = "python" if server_script_path.endswith('.py') else "node"
        
        # Configure server connection parameters
        server_params = StdioServerParameters(command=command, args=[server_script_path])
        
        # Establish bidirectional communication channel with the server
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        
        # Initialize MCP session and retrieve available tools
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()
        
        response = await self.session.list_tools()
        tools = response.tools
        
        print("\nConnected to server with tools:", [tool.name for tool in tools])
        
        # Convert MCP tools format to be compatible with Gemini API
        self.function_declarations = convert_mcp_tools_to_gemini(tools)

    async def process_query(self, query: str) -> str:
        """
        Process user queries through Gemini API with tool-calling capabilities.
        
        Args:
            query: The user's text input question or instruction
            
        Returns:
            Gemini's response, potentially after executing requested tools
        """
        # Add user query to conversation history
        user_msg_id = self.conversation_manager.add_message(
            role='user',
            content=query
        )
        self.latest_message_id = user_msg_id
        
        # Get conversation context from database with token awareness
        conversation_history = self.conversation_manager.get_conversation_for_context(
            latest_message_id=user_msg_id,
            include_all_paths=False  # Only include the current path for focused reasoning
        )
        
        # Send initial request to Gemini with available tools
        response = self.genai_client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents=conversation_history,
            config=types.GenerateContentConfig(
                tools=self.function_declarations,
            ),
        )
        
        # Prepare collection for final response text
        final_text = []
        
        # Continue processing tool calls until Gemini provides a final answer
        while True:
            has_function_call = False
            
            # Process Gemini's response, handling any tool execution requests
            for candidate in response.candidates:
                if not candidate.content or not candidate.content.parts:
                    continue
                    
                for part in candidate.content.parts:
                    if not isinstance(part, types.Part):
                        continue
                        
                    if part.function_call:
                        # We found a function call, set flag to true
                        has_function_call = True
                        
                        # Extract tool call details from Gemini's response
                        function_call_part = part
                        tool_name = function_call_part.function_call.name
                        tool_args = function_call_part.function_call.args
                        
                        print(f"\n[Gemini requested tool call: {tool_name} with args {tool_args}]")
                        
                        # Add model's tool call to conversation history
                        model_msg_id = self.conversation_manager.add_message(
                            role='model',
                            parent_id=self.latest_message_id,
                            tool_name=tool_name,
                            tool_args=tool_args,
                            content=None
                        )
                        self.latest_message_id = model_msg_id
                        
                        # Execute the requested tool via MCP server
                        try:
                            result = await self.session.call_tool(tool_name, tool_args)
                            function_response = {"result": result.content}
                        except Exception as e:
                            function_response = {"error": str(e)}
                            print(f"Error executing tool: {str(e)}")
                        
                        # Add tool response to conversation history
                        tool_msg_id = self.conversation_manager.add_message(
                            role='tool',
                            parent_id=model_msg_id,
                            tool_name=tool_name,
                            tool_result=self._ensure_json_serializable(function_response),
                            content=None
                        )
                        self.latest_message_id = tool_msg_id
                        
                        # Get updated conversation history
                        conversation_history = self.conversation_manager.get_conversation_for_context(
                            latest_message_id=tool_msg_id,
                            include_all_paths=False
                        )
                        
                        # Send updated conversation with tool results back to Gemini
                        response = self.genai_client.models.generate_content(
                            model='gemini-2.0-flash-001',
                            contents=conversation_history,
                            config=types.GenerateContentConfig(
                                tools=self.function_declarations,
                            ),
                        )
                        
                        # We've processed one function call, break the inner loop
                        # to re-evaluate the new response for more function calls
                        break
                        
                    else:
                        # No function call, just text response
                        if part.text and part.text.strip():
                            final_text.append(part.text)
                
                # Break out of candidate loop if we found and processed a function call
                if has_function_call:
                    break
            
            # If no function calls were found in this response, we're done
            if not has_function_call:
                # One last check for text responses in the final message
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if isinstance(part, types.Part) and part.text and part.text.strip():
                                final_text.append(part.text)
                
                # Add final model response to conversation history
                final_response = "\n".join([text for text in final_text if text is not None and text.strip()])
                if final_response:
                    final_msg_id = self.conversation_manager.add_message(
                        role='model',
                        parent_id=self.latest_message_id,
                        content=final_response
                    )
                    self.latest_message_id = final_msg_id
                
                break
        
        # Filter out None values and empty strings
        filtered_text = [text for text in final_text if text is not None and text.strip()]
        
        # Return empty string if no valid responses
        if not filtered_text:
            return "No response generated."
            
        # Combine all response segments
        return "\n".join(filtered_text)

    async def chat_loop(self):
        """Run interactive chat session between user and Gemini with tool capabilities."""
        print("\nMCP Client Started! Type 'quit' to exit.")
        
        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == 'quit':
                break
                
            response = await self.process_query(query)
            print("\n" + response)

    async def cleanup(self):
        """Release all resources and connections."""
        await self.exit_stack.aclose()
        self.conversation_manager.close()

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

def clean_schema(schema):
    """
    Remove title fields from JSON schemas to ensure compatibility with Gemini API.
    
    Args:
        schema: JSON schema dictionary
        
    Returns:
        Cleaned schema dictionary suitable for Gemini
    """
    if isinstance(schema, dict):
        schema.pop("title", None)
        
        # Recursively process nested properties
        if "properties" in schema and isinstance(schema["properties"], dict):
            for key in schema["properties"]:
                schema["properties"][key] = clean_schema(schema["properties"][key])
    
    return schema

def convert_mcp_tools_to_gemini(mcp_tools):
    """
    Convert MCP tool definitions to Gemini-compatible format.
    
    Args:
        mcp_tools: List of tool objects from MCP server
        
    Returns:
        List of tools formatted for Gemini API function calling
    """
    gemini_tools = []
    
    for tool in mcp_tools:
        # Clean schema to comply with Gemini API requirements
        parameters = clean_schema(tool.inputSchema)
        
        # Create function declaration for each tool
        function_declaration = FunctionDeclaration(
            name=tool.name,
            description=tool.description,
            parameters=parameters
        )
        
        # Wrap in Gemini Tool object
        gemini_tool = Tool(function_declarations=[function_declaration])
        gemini_tools.append(gemini_tool)
    
    return gemini_tools

async def main():
    """
    Main entry point for the MCP client application.
    Requires server script path as command line argument.
    """
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
    
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())


