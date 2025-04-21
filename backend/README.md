# MCP-Hive Backend

## Overview
This repository contains the Python backend services for the MCP-Hive project. It's designed to function as an API service that enables integration with LLM models (specifically Google's Gemini and Groq) using the Model Control Protocol (MCP).

## Features
- MCP (Model Control Protocol) client implementation
- Multiple transport mechanisms (StdIO and SSE)
- Integration with Google's Gemini AI and Groq LLM models
- SQLite-based conversation management and persistence
- Asynchronous processing with asyncio
- Tool/function calling capabilities
- Environment configuration management
- LangChain React agent implementation

## Tech Stack
- Python 3.12+
- Google Generative AI SDK
- Groq API for additional LLM options
- MCP (Model Control Protocol)
- Server-Sent Events (SSE) for web transport
- SQLite for conversation storage
- dotenv for environment management
- LangChain and LangGraph for AI agent frameworks

## Getting Started

### Prerequisites
- Python 3.12 or higher
- pip or uv package manager

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/MCP-Hive-backend.git
   ```

2. Set up a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Create a `.env` file based on `.env.example`
   - Add your API keys: 
     ```
     GEMINI_API_KEY=your_gemini_api_key
     GROQ_API_KEY=your_groq_api_key
     CONVERSATION_DB_PATH=./conversations.db
     MAX_CONTEXT_TOKENS=8000
     DEFAULT_LLM_PROVIDER=gemini
     ```

### Running the Service

#### Standard MCP Client (StdIO-based transport)
Run the main client with a local MCP server:
```
python client.py path/to/server_script.py
```

#### SSE-based MCP Client (Web transport)
Run the SSE client with a web-based MCP server:
```
python client_sse.py http://localhost:8081/sse
```

#### LangChain React Agent Client
Run the LangChain React agent client with a configuration file:
```
python mcp_client_config.py
```

For testing with a simple MCP server:
```
python test_server.py
```

For testing with an SSE-based MCP server:
```
python test_server_sse.py
```

## Project Structure
- `client.py` - Main MCP client implementation with conversation management
- `client_sse.py` - SSE-based MCP client for web transport
- `mcp_client_config.py` - LangChain React agent with MCP tools integration
- `test_server.py` - Simple MCP server for testing
- `test_server_sse.py` - SSE-based MCP server for testing
- `conversations.db` - SQLite database for storing conversations
- `.env` - Environment configuration

## MCP Client Types

### StdIO-based Client
The standard MCP client uses StdIO for communication with local MCP servers. This is ideal for:
- Local deployment scenarios
- Direct integration with Python-based servers
- Command-line applications

### SSE-based Client
The SSE client uses Server-Sent Events for communication, enabling:
- Web-based integration
- Connection to remote MCP servers
- Browser compatibility
- Real-time streaming responses

### LangChain React Agent Client
The LangChain client implements the React agent pattern for more sophisticated reasoning:
- Configuration-based MCP server connections
- ReAct pattern for reasoning and acting
- Structured agent-based decision making
- JSON configuration for multiple server setup

## MCP Integration
The backend uses the Model Control Protocol (MCP) to interact with AI services, enabling:
- Structured function calling
- Conversation management
- Context awareness
- Tool integration

## Multi-LLM Support
The clients support multiple LLM providers:
- **Google Gemini**: High-quality responses with function calling capabilities
- **Groq LLM**: Fast, low-latency responses with competitive quality

## Database Schema
The SQLite database contains:
- `conversations` table - Tracks conversation metadata
- `messages` table - Stores all messages with tree structure support for managing complex conversations

## Contributing
(Your contribution guidelines)

## License
(Your chosen license)

# MCP Client with Multi-LLM Support

A flexible Multi-modal Capability Protocol (MCP) client that connects natural language processing with executable tools.

## Features

- **Multiple LLM Providers**: Support for both Google's Gemini and Groq's LLMs
- **Persistent Conversation History**: SQLite database with token-aware management
- **Tree-Based Conversation Structure**: Maintains conversation branches and context
- **Tool Execution**: Seamless execution of server-side tools through natural language
- **Token-Aware Context Management**: Intelligently manages context windows
- **Multiple Transport Options**: StdIO and SSE-based communication

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure your environment variables in `.env`:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   GROQ_API_KEY=your_groq_api_key
   CONVERSATION_DB_PATH=./conversations.db
   MAX_CONTEXT_TOKENS=8000
   DEFAULT_LLM_PROVIDER=gemini  # or "groq"
   ```

3. Run the standard client:
   ```
   python client.py path/to/server_script.py
   ```

4. Or run the SSE-based client:
   ```
   python client_sse.py http://localhost:8081/sse
   ```

## Supported LLM Providers

### Gemini
- Default model: `gemini-2.0-flash-001`
- Function calling support
- Fast response times

### Groq
- Default model: `llama-3-70b-8192`
- Function calling support
- Extremely low latency

## Usage

The client accepts natural language queries and determines whether to execute tools or provide direct responses:

```
MCP Client Started! Type 'quit' to exit.

Query: Calculate 25 + 17
42

Query: What's the weather in New York?
[Tool execution for weather data...]
The current temperature in New York is 72°F with partly cloudy skies.
```

## Architecture

Built with a modular design that separates:
- LLM provider interfaces
- Conversation storage and management
- Tool execution pipelines
- Transport mechanisms (StdIO, SSE)

See `notes/Chapter1-MCP-Client.md` and `notes/Chapter2-MCP-Client-SSE.md` for detailed architecture documentation.
