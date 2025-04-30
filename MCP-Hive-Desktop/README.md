# MCP Hive Desktop

Desktop application for the MCP-Hive backend, providing a modern UI for interacting with LLMs using the Model Context Protocol.

## Features

- Modern UI for interacting with the MCP-Hive backend
- Switch between multiple LLM providers (Gemini, Groq, etc.)
- Manage MCP server configurations directly from the UI
- Built-in backend server management
- Cross-platform support (Windows, macOS, Linux)

## Development

### Prerequisites

- Node.js 18+ and npm
- Python 3.10+ (for the backend)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/MCP-Hive.git
   cd MCP-Hive
   ```

2. Install dependencies:
   ```
   cd MCP-Hive-Desktop
   npm install
   ```

3. Start the Tailwind CSS watcher:
   ```
   npm run dev
   ```

4. In a separate terminal, start the application:
   ```
   npm start
   ```

## Building for Production

### Building for All Platforms

Build for all supported platforms:
```
npm run build
```

### Building for Specific Platforms

Build only for Windows:
```
npm run build:win
```

Build only for macOS:
```
npm run build:mac
```

Build only for Linux:
```
npm run build:linux
```

## MCP Server Configuration

MCP Hive Desktop now includes a built-in UI for managing the `Mcphive_config.json` file, which configures the MCP servers used by the backend.

### How to Manage MCP Servers

1. Click the "Manage" button in the "Connected Servers" section of the sidebar
2. The Server Configuration modal will appear, showing all configured servers
3. Use the "Add Server" button to add a new server
4. Use the edit and delete buttons to modify or remove existing servers
5. Restart the backend after making changes to apply them

### Server Types

Two types of MCP servers are supported:

1. **SSE (Server-Sent Events)**:
   - For servers that use HTTP Server-Sent Events
   - Specify the URL (e.g., `http://localhost:8081/sse`)

2. **Command (Subprocess)**:
   - For servers that run as a separate process
   - Specify the command (e.g., `python`) and arguments (e.g., `server.py --port 8081`)

## LLM Provider Configuration

LLM provider API keys are configured in the `.env` file, which is automatically created in the Hive folder when you first run the application.

Example `.env` file:
```
GOOGLE_API_KEY=your_google_api_key_here
GROQ_API_KEY=your_groq_api_key_here
DEFAULT_LLM_PROVIDER=gemini
```

## License

MIT 