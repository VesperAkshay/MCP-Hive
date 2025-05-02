# MCP-Hive

A desktop application for the Model Control Protocol (MCP) with an integrated Python backend packaged as an executable.

## Overview

MCP-Hive is a desktop application that integrates with various AI model providers through the Model Control Protocol. The application consists of:

1. An Electron-based frontend for the user interface
2. A Python backend (packaged as an executable) for handling the AI model connections and processing

## Building and Packaging

### Prerequisites

- Node.js and npm
- Python 3.10+ with pip
- PyInstaller (`pip install pyinstaller`)
- Git

### Installation Steps

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/MCP-Hive.git
   cd MCP-Hive
   ```

2. Install Python dependencies for the backend:
   ```
   cd Hive
   pip install -r requirements.txt
   cd ..
   ```

3. Install Node.js dependencies for the frontend:
   ```
   cd MCP-Hive-Desktop
   npm install
   cd ..
   ```

### Building the Executable Backend

The backend is packaged as an executable using PyInstaller:

```
cd Hive
python build_executable.py
cd ..
```

This script:
- Builds the Python backend as a standalone executable
- Copies the executable and necessary resources to the Electron resources directory

### Building the Electron App with Packaged Backend

After building the backend, build the complete Electron app:

```
cd MCP-Hive-Desktop
npm run build
```

This command:
1. Runs the backend build script first (`npm run build:backend`)
2. Packages the Electron app with the executable backend (`npm run build:app`)

The packaged application will be available in the `MCP-Hive-Desktop/dist` directory.

## Development

For development, you can run the app without packaging:

```
cd MCP-Hive-Desktop
npm start
```

This will start the Electron app and use the executable backend if available, or fall back to using the Python interpreter if needed.

## Configuration

### API Keys

Set up your AI provider API keys in the `.env` file in the `Hive` directory:

```
GOOGLE_API_KEY=your_google_api_key_here
GROQ_API_KEY=your_groq_api_key_here
DEFAULT_LLM_PROVIDER=gemini
```

### MCP Servers

Configure MCP servers through the application's settings interface or by directly editing the `Mcphive_config.json` file.

## License

[MIT License](LICENSE.md) 