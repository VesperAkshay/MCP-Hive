# MCP-Hive

A modular, scalable Model Control Protocol (MCP) client that connects LLMs with executable tools, supporting multiple transports and LLM providers.

## Features

- **Modular Architecture**: Clean separation of concerns with well-defined components
- **Multiple LLM Providers**: Support for Google's Gemini and Groq LLMs
- **Multiple Transport Methods**: Support for both StdIO and SSE-based MCP transports
- **Tool Execution Pipeline**: Seamless execution of server-side tools through natural language
- **Persistent Conversation History**: SQLite database with token-aware context management
- **Web Server Interface**: FastAPI-based web server with WebSocket support for real-time interactions
- **CLI Interface**: Command-line interface for interactive conversations

## Architecture

The MCP-Hive backend is organized into the following modules:

- **core**: Main client implementation and business logic
- **config**: Configuration management
- **database**: Conversation history and persistence
- **providers**: LLM providers (Gemini, Groq)
- **server**: Web server and API
- **tools**: MCP server connection and tool execution
- **transports**: MCP transport implementations (StdIO, SSE)
- **utils**: Utility functions

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/MCP-Hive.git
   cd MCP-Hive
   ```

2. Create a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   GROQ_API_KEY=your_groq_api_key
   CONVERSATION_DB_PATH=./conversations.db
   MAX_CONTEXT_TOKENS=8000
   DEFAULT_LLM_PROVIDER=gemini
   ```

## Configuration

Create a `Mcphive_config.json` file to configure your MCP servers:

```json
{
  "mcpServers": {
    "calculator_server": {
      "type": "sse",
      "url": "http://localhost:8081/sse"
    },
    "weather_server": {
      "command": "python",
      "args": ["backend/test_server.py"]
    },
    "filesystem": {
      "command": "python",
      "args": ["backend/filesystem_server.py"]
    }
  }
}
```

## Usage

### CLI Mode

Run the client in CLI mode:

```
python mcp_hive.py
```

### Web Server Mode

Run the client as a web server:

```
python mcp_hive.py --server --port 8000
```

Then access the web interface at http://localhost:8000

## API Endpoints

- `GET /`: Web interface
- `GET /health`: Health check
- `GET /providers`: List available LLM providers
- `POST /providers/{provider_name}`: Switch active provider
- `GET /servers`: List connected MCP servers
- `POST /chat`: Process a chat message
- `WebSocket /ws`: Real-time chat endpoint

## License

[Your chosen license]

## Contributors

[Your name] 