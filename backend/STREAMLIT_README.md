# MCP-Hive Streamlit App

This Streamlit application provides a user-friendly web interface for the MCP-Hive unified client. It allows you to connect to multiple MCP servers, select LLM providers, and interact with the tools they provide.

## Features

- Connect to multiple MCP servers defined in your `Mcphive_config.json`
- Choose between Gemini and Groq as your LLM provider
- Interactive chat interface with the agent
- View tool calls and their results visually
- Start new conversations as needed

## Prerequisites

- Python 3.9+
- All dependencies installed from `requirements.txt`
- Valid API keys in your `.env` file for the LLM providers
- Properly configured `Mcphive_config.json` file

## How to Run

### Option 1: Using the run script

The simplest way to start the app is to use the provided run script:

```bash
python run_streamlit.py
```

### Option 2: Run Streamlit directly

Alternatively, you can run Streamlit directly:

```bash
streamlit run streamlit_app.py
```

## Using the App

1. **Initialize the Client**: Click the "Initialize Client" button to set up the MCP client
2. **Connect to Servers**: Click on the server buttons to connect to your configured MCP servers
3. **Set LLM Provider**: Select your preferred LLM provider from the dropdown and click "Set Provider"
4. **Start a Conversation**: Type your query in the text area and click "Send"
5. **View Responses**: See the agent's responses, tool calls, and tool results in the main panel
6. **Start a New Conversation**: Click "New Conversation" to clear the history and start fresh

## Configuration

The app uses the `Mcphive_config.json` file for server configurations. Make sure this file is properly set up with your MCP servers.

## Troubleshooting

- **Connection Issues**: If you have trouble connecting to an MCP server, check your configuration file and make sure the server is running
- **LLM Provider Errors**: Ensure your `.env` file has the correct API keys for the LLM providers you want to use
- **Tool Execution Errors**: Some tools may require specific permissions or configurations; check the error messages for details

## Example Query Flow

1. User asks: "What files are in the current directory?"
2. The agent recognizes this needs the filesystem tool
3. A tool call is displayed showing the tool being used
4. The tool result shows the list of files
5. The agent provides a final response summarizing the information 