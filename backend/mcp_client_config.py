#!/usr/bin/env python
"""
langchain_mcp_client_wconfig.py

This file implements a LangChain MCP client that:
  - Loads configuration from a JSON file specified by the MCPHIVE_CONFIG environment variable.
  - Connects to one or more MCP servers defined in the config.
  - Loads available MCP tools from each connected server.
  - Uses the Google Gemini API (via LangChain) to create a React agent with access to all tools.
  - Runs an interactive chat loop where user queries are processed by the agent.

Detailed explanations:
  - Retries (max_retries=2): If an API call fails due to transient issues (e.g., timeouts), it will retry up to 2 times.
  - Temperature (set to 0): A value of 0 means fully deterministic output; increase this for more creative responses.
  - Environment Variable: MCPHIVE_CONFIG should point to a config JSON that defines all MCP servers.
"""

import asyncio                        # For asynchronous operations
import os                             # To access environment variables and file paths
import sys                            # For system-specific parameters and error handling
import json                           # For reading and writing JSON data
from contextlib import AsyncExitStack # For managing multiple asynchronous context managers

# ---------------------------
# MCP Client Imports
# ---------------------------
from mcp import ClientSession, StdioServerParameters  # For managing MCP client sessions and server parameters
from mcp.client.stdio import stdio_client             # For establishing a stdio connection to an MCP server

# ---------------------------
# Agent and LLM Imports
# ---------------------------
from langchain_mcp_adapters.tools import load_mcp_tools  # Adapter to convert MCP tools to LangChain compatible tools
from langgraph.prebuilt import create_react_agent        # Function to create a prebuilt React agent using LangGraph
from langchain_google_genai import ChatGoogleGenerativeAI  # Wrapper for the Google Gemini API via LangChain

# ---------------------------
# Environment Setup
# ---------------------------
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from a .env file (e.g., GOOGLE_API_KEY)

# ---------------------------
# Custom JSON Encoder for LangChain objects
# ---------------------------
class CustomEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle non-serializable objects returned by LangChain.
    If the object has a 'content' attribute (such as HumanMessage or ToolMessage), serialize it accordingly.
    """
    def default(self, o):
        # Check if the object has a 'content' attribute
        if hasattr(o, "content"):
            # Return a dictionary containing the type and content of the object
            return {"type": o.__class__.__name__, "content": o.content}
        # Otherwise, use the default serialization
        return super().default(o)

# ---------------------------
# Function: read_config_json
# ---------------------------
def read_config_json():
    """
    Reads the MCP server configuration JSON.
    
    Returns:
        dict: Parsed JSON content with MCP server definitions.
    """
    # Get the first command-line argument as the config file path if provided
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        # Use the mcphive_config.json file in the same directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "Mcphive_config.json")
        print(f"⚠️  MCP-HIVE_CONFIG not set. Falling back to: {config_path}")
    
    try:
        # Open and read the JSON config file
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        # If reading fails, print an error and exit the program
        print(f"❌ Failed to read config file at '{config_path}': {e}")
        sys.exit(1)

# ---------------------------
# Google Gemini LLM Instantiation
# ---------------------------
# Check if API key is available in environment
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    print("❌ GEMINI_API_KEY not found in environment variables. Please set it and try again.")
    sys.exit(1)

# Initialize the LLM using direct API key authentication
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-001",
        temperature=0,
        max_retries=2,
        google_api_key=gemini_api_key  # Pass GEMINI_API_KEY to google_api_key parameter
    )
    print("✅ Successfully initialized Google Gemini LLM")
except Exception as e:
    print(f"❌ Failed to initialize Gemini LLM: {str(e)}")
    sys.exit(1)

# ---------------------------
# Main Function: run_agent
# ---------------------------
async def run_agent():
    """
    Connects to all MCP servers defined in the configuration, loads their tools, creates a unified React agent,
    and starts an interactive loop to query the agent.
    """
    config = read_config_json()  # Load MCP server configuration from the JSON file
    mcp_servers = config.get("mcpServers", {})  # Retrieve the MCP server definitions from the config
    if not mcp_servers:
        print("❌ No MCP servers found in the configuration.")
        return

    tools = []  # Initialize an empty list to hold all the tools from the connected servers

    # Use AsyncExitStack to manage and cleanly close multiple asynchronous resources
    async with AsyncExitStack() as stack:
        # Iterate over each MCP server defined in the configuration
        for server_name, server_info in mcp_servers.items():
            print(f"\n🔗 Connecting to MCP Server: {server_name}...")

            # Create StdioServerParameters using the command and arguments specified for the server
            server_params = StdioServerParameters(
                command=server_info["command"],
                args=server_info["args"]
            )

            try:
                # Establish a stdio connection to the server using the server parameters
                read, write = await stack.enter_async_context(stdio_client(server_params))
                # Create a client session using the read and write streams from the connection
                session = await stack.enter_async_context(ClientSession(read, write))
                # Initialize the session (e.g., perform handshake or setup operations)
                await session.initialize()

                # Load the MCP tools from the connected server using the adapter function
                server_tools = await load_mcp_tools(session)

                # Iterate over each tool and add it to the aggregated tools list
                for tool in server_tools:
                    print(f"\n🔧 Loaded tool: {tool.name}")
                    tools.append(tool)

                print(f"\n✅ {len(server_tools)} tools loaded from {server_name}.")
            except Exception as e:
                # Handle any errors that occur during connection or tool loading for the server
                print(f"❌ Failed to connect to server {server_name}: {e}")

        # If no tools were loaded from any server, exit the function
        if not tools:
            print("❌ No tools loaded from any server. Exiting.")
            return

        # Create a React agent using the Google Gemini LLM and the list of aggregated tools
        agent = create_react_agent(llm, tools)

        # Start the interactive chat loop
        print("\n🚀 MCP Client Ready! Type 'quit' to exit.")
        while True:
            # Prompt the user to enter a query
            query = input("\nQuery: ").strip()
            if query.lower() == "quit":
                # Exit the loop if the user types 'quit'
                break

            # Invoke the agent asynchronously with the query as the input message
            response = await agent.ainvoke({"messages": query})

            # Format and print the agent's response as nicely formatted JSON
            print("\nResponse:")
            try:
                # Extract only the AI's message content from the response
                messages = response.get("messages", [])
                # Find the last AI message in the list
                for message in reversed(messages):
                    if isinstance(message, dict) and message.get("type") == "AIMessage":
                        print(message.get("content", "No response content"))
                        break
                    elif hasattr(message, "__class__") and message.__class__.__name__ == "AIMessage":
                        print(message.content)
                        break
                else:
                    # If no AI message was found
                    print("No AI response found in the messages")
            except Exception as e:
                # If extraction fails, simply print the raw response
                print(f"Error formatting response: {e}")
                print(str(response))

# ---------------------------
# Entry Point
# ---------------------------
if __name__ == "__main__":
    # Run the asynchronous run_agent function using asyncio's event loop
    asyncio.run(run_agent())

# ---------------------------
# LLM Provider Classes
# ---------------------------
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
        
        self.model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versetile")
        self.groq_client = groq.Client(api_key=api_key)
    
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

# Helper functions
def clean_schema(schema):
    """
    Remove title fields from JSON schemas to ensure compatibility with LLM APIs.
    
    Args:
        schema: JSON schema dictionary
        
    Returns:
        Cleaned schema dictionary suitable for LLM APIs
    """
    if isinstance(schema, dict):
        schema.pop("title", None)
        
        # Recursively process nested properties
        if "properties" in schema and isinstance(schema["properties"], dict):
            for key in schema["properties"]:
                schema["properties"][key] = clean_schema(schema["properties"][key])
    
    return schema
