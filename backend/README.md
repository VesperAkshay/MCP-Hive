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
