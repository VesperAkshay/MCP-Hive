#!/usr/bin/env python
"""
Streamlit UI for the Unified MCP Client

This script provides a web-based user interface for the UnifiedMCPClient
using Streamlit. It allows users to:
- Select and connect to MCP servers
- Choose LLM providers
- Send queries to the agent
- View conversation history
- Execute tools through the agent
"""

import os
import sys
import json
import asyncio
import streamlit as st
from typing import Dict, List, Any
import threading
import time
from pathlib import Path

# Import the UnifiedMCPClient
from unified_mcp_client import UnifiedMCPClient, ConfigManager, TransportType

# Setup for async operations in Streamlit
import nest_asyncio
nest_asyncio.apply()

# Set page configuration
st.set_page_config(
    page_title="MCP-Hive Client",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define CSS for improved UI
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton button {
        width: 100%;
    }
    .tool-message {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .user-message {
        background-color: #e6f3ff;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .assistant-message {
        background-color: #f0fff4;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .tool-result {
        background-color: #fff8e6;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for conversation and client
if 'client' not in st.session_state:
    st.session_state.client = None
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'connected_servers' not in st.session_state:
    st.session_state.connected_servers = set()
if 'available_tools' not in st.session_state:
    st.session_state.available_tools = []

async def initialize_client():
    """Initialize the UnifiedMCPClient"""
    if st.session_state.initialized:
        return
    
    # Load configuration
    config_path = os.path.join(os.path.dirname(__file__), "Mcphive_config.json")
    client = UnifiedMCPClient(config_path=config_path)
    
    # Initialize the client
    await client.initialize()
    
    # Store in session state
    st.session_state.client = client
    st.session_state.initialized = True
    
    # Start a new conversation
    st.session_state.conversation_id = client.conversation_manager.start_new_conversation("Streamlit Session")
    
    return client

async def connect_to_server(server_name):
    """Connect to an MCP server"""
    if not st.session_state.initialized:
        await initialize_client()
    
    try:
        result = await st.session_state.client.connect_to_server(server_name)
        if result:
            st.session_state.connected_servers.add(server_name)
            # Update available tools
            server_tools = st.session_state.client.server_connections[server_name].session.tools
            st.session_state.available_tools.extend(server_tools)
        return result
    except Exception as e:
        st.error(f"Error connecting to {server_name}: {str(e)}")
        return False

async def set_provider(provider_name):
    """Set the LLM provider"""
    if not st.session_state.initialized:
        await initialize_client()
    
    try:
        result = await st.session_state.client.set_provider(provider_name)
        return result
    except Exception as e:
        st.error(f"Error setting provider to {provider_name}: {str(e)}")
        return False

async def process_query(query):
    """Process a user query"""
    if not st.session_state.initialized:
        await initialize_client()
    
    if not query.strip():
        return None
    
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": query})
    
    try:
        # Process the query
        result = await st.session_state.client.process_query(
            query, 
            conversation_id=st.session_state.conversation_id
        )
        
        # Add result to messages
        if "has_function_call" in result and result["has_function_call"]:
            # Add tool call
            tool_name = result.get("tool_name", "unknown_tool")
            tool_args = result.get("tool_args", {})
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"I need to use the {tool_name} tool",
                "tool_name": tool_name,
                "tool_args": tool_args
            })
            
            # Add tool result if available
            if "tool_result" in result and result["tool_result"]:
                st.session_state.messages.append({
                    "role": "tool",
                    "content": str(result["tool_result"]),
                    "tool_name": tool_name
                })
            
            # Add final response if available
            if "final_text" in result and result["final_text"]:
                final_text = " ".join(result["final_text"]) if isinstance(result["final_text"], list) else result["final_text"]
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_text
                })
        else:
            # Just a regular response
            final_text = " ".join(result["final_text"]) if isinstance(result["final_text"], list) else result["final_text"]
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_text
            })
        
        return result
    except Exception as e:
        st.error(f"Error processing query: {str(e)}")
        st.session_state.messages.append({
            "role": "system",
            "content": f"Error: {str(e)}"
        })
        return None

def run_async(func, *args, **kwargs):
    """Run async function from sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(func(*args, **kwargs))
    loop.close()
    return result

def main():
    """Main Streamlit app function"""
    st.title("🔮 MCP-Hive Client")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Initialize client
        if not st.session_state.initialized:
            if st.button("Initialize Client"):
                with st.spinner("Initializing client..."):
                    run_async(initialize_client)
                st.success("Client initialized!")
        else:
            st.success("Client initialized")
        
        # Load config to display available servers
        if st.session_state.initialized:
            st.subheader("Connect to Servers")
            
            config_manager = st.session_state.client.config_manager
            server_names = config_manager.get_server_names()
            
            # Create buttons for each server
            for server_name in server_names:
                if server_name in st.session_state.connected_servers:
                    st.success(f"✅ {server_name}")
                else:
                    if st.button(f"Connect to {server_name}"):
                        with st.spinner(f"Connecting to {server_name}..."):
                            success = run_async(connect_to_server, server_name)
                        if success:
                            st.success(f"Connected to {server_name}!")
                            st.experimental_rerun()
                        else:
                            st.error(f"Failed to connect to {server_name}")
            
            # LLM provider selection
            st.subheader("LLM Provider")
            provider_options = ["gemini", "groq"]
            provider = st.selectbox("Select Provider", provider_options)
            
            if st.button("Set Provider"):
                with st.spinner(f"Setting provider to {provider}..."):
                    success = run_async(set_provider, provider)
                if success:
                    st.success(f"Provider set to {provider}")
                else:
                    st.error(f"Failed to set provider to {provider}")
            
            # Display available tools
            if st.session_state.available_tools:
                st.subheader("Available Tools")
                for tool in st.session_state.available_tools:
                    st.markdown(f"**{tool.name}**: {tool.description[:50]}...")
        
        # Reset conversation
        if st.session_state.initialized and st.button("New Conversation"):
            if st.session_state.client:
                st.session_state.conversation_id = st.session_state.client.conversation_manager.start_new_conversation("Streamlit Session")
                st.session_state.messages = []
                st.success("Started new conversation")
    
    # Main chat interface
    if st.session_state.initialized:
        # Display conversation
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"<div class='user-message'>**You:** {msg['content']}</div>", unsafe_allow_html=True)
            elif msg["role"] == "assistant":
                if "tool_name" in msg:
                    st.markdown(f"<div class='tool-message'>**Assistant:** Using tool '{msg['tool_name']}' with args: {json.dumps(msg['tool_args'], indent=2)}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='assistant-message'>**Assistant:** {msg['content']}</div>", unsafe_allow_html=True)
            elif msg["role"] == "tool":
                st.markdown(f"<div class='tool-result'>**Tool Result ({msg['tool_name']}):** {msg['content']}</div>", unsafe_allow_html=True)
            elif msg["role"] == "system":
                st.warning(msg["content"])
        
        # Input for new queries
        with st.form(key="query_form", clear_on_submit=True):
            user_input = st.text_area("Your query:", key="user_query", height=100)
            submit_button = st.form_submit_button("Send")
            
            if submit_button and user_input:
                with st.spinner("Processing..."):
                    run_async(process_query, user_input)
                st.experimental_rerun()
    else:
        st.info("Please initialize the client using the button in the sidebar.")

if __name__ == "__main__":
    main() 