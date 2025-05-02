# MCP-Hive Desktop Application

The Electron-based desktop application for MCP-Hive with packaged Python backend.

## Overview

This desktop application provides a user interface for interacting with the MCP-Hive backend, which has been packaged as an executable to eliminate the need for Python installation or dependencies on the user's machine.

## Build Process

### Prerequisites

- Node.js and npm
- Python 3.10+ with pip (for building the backend)
- PyInstaller (`pip install pyinstaller`)

### Building Steps

1. Install dependencies:
   ```
   npm install
   ```

2. Build the backend executable:
   ```
   npm run build:backend
   ```
   This will run the Python script that packages the backend as an executable and copies it to the resources directory.

3. Package the Electron app:
   ```
   npm run build:app
   ```
   This will bundle the app with the executable backend.

4. Alternatively, run the complete build process:
   ```
   npm run build
   ```
   This will execute both of the above steps in sequence.

## Development

For development purposes, you can run the app without packaging:

```
npm start
```

This will start the Electron app in development mode with DevTools enabled.

## Application Structure

- `main.js` - The main Electron process
- `preload.js` - Preload script for secure IPC communication
- `renderer/` - Frontend UI components and pages
- `config-manager.js` - Handles MCP server configuration
- `resources/` - Contains the packaged backend executable and configuration files (created during build)

## Configuration

The application uses several configuration files:

1. `.env` file (in the Hive directory) - Contains API keys and server settings
2. `Mcphive_config.json` - Contains MCP server configurations

The application will create these files with default values if they don't exist.

## Packaging Options

You can customize the packaging options in the `build` section of `package.json`:

- `appId` - The application ID
- `productName` - The name of the application
- `directories.output` - The output directory for the packaged app
- `extraResources` - Additional files to include in the package
- `win/mac/linux` - Platform-specific build configurations

## Features

- Modern UI for interacting with the MCP-Hive backend
- Switch between multiple LLM providers (Gemini, Groq, etc.)
- Manage MCP server configurations directly from the UI
- Built-in backend server management
- Cross-platform support (Windows, macOS, Linux)

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