# MCP-Hive Backend

## Overview
This repository contains the Python backend services for the MCP-Hive project. It's designed to function as an API service that enables integration with LLM models (specifically Google's Gemini) using the Model Control Protocol (MCP).

## Features
- MCP (Model Control Protocol) client implementation
- Integration with Google's Gemini AI models
- SQLite-based conversation management and persistence
- Asynchronous processing with asyncio
- Tool/function calling capabilities
- Environment configuration management

## Tech Stack
- Python 3.12+
- Google Generative AI SDK
- MCP (Model Control Protocol)
- SQLite for conversation storage
- dotenv for environment management
- LangChain for AI framework components

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
   - Add your Google API key: `GOOGLE_API_KEY=your_api_key_here`

### Running the Service

Run the main client:
```
python client.py
```

For testing with a simple MCP server:
```
python test_server.py
```

## Project Structure
- `client.py` - Main MCP client implementation with conversation management
- `test_server.py` - Simple MCP server for testing
- `main.py` - Basic entry point
- `conversations.db` - SQLite database for storing conversations
- `.env` - Environment configuration

## MCP Integration
The backend uses the Model Control Protocol (MCP) to interact with AI services, enabling:
- Structured function calling
- Conversation management
- Context awareness
- Tool integration

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

3. Run the client:
   ```
   python client.py path/to/server_script.py
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

See `notes/Chapter1-MCP-Client.md` for detailed architecture documentation.
