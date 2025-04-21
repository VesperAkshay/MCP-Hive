# Chapter 2: Building an MCP Client with Server-Sent Events (SSE)

*Author: Student Name*  
*Date: May 3, 2025*  
*Course: Advanced AI Integration Systems*

---

## 1. Introduction to SSE-Based MCP Client

Building upon our previous work with the standard MCP client in Chapter 1, we've now extended our implementation to support Server-Sent Events (SSE) as a transport mechanism. This enables our client to communicate with web-based MCP servers, opening up new integration possibilities.

### 1.1 What is SSE?

Server-Sent Events (SSE) is a web technology where a browser receives automatic updates from a server via an HTTP connection. Unlike WebSockets, SSE is a one-directional protocol (server to client), making it ideal for streaming data from servers to clients with less overhead.

Key characteristics of SSE:
- Uses standard HTTP
- Text-based protocol
- Automatic reconnection
- Built-in event IDs
- Efficient for server-to-client streaming

### 1.2 Why Add SSE Support?

Adding SSE support to our MCP client provides several advantages:

1. **Web Integration**: Enables our client to connect to web servers
2. **Firewall Friendly**: Uses standard HTTP, which passes through most firewalls
3. **Simplicity**: Simpler than WebSockets for one-way communication
4. **Compatibility**: Works with standard web infrastructure
5. **Streaming**: Ideal for real-time updates and streaming responses

## 2. SSE Client Architecture

### 2.1 Component Overview

The SSE-based MCP client architecture consists of these key components:

1. **SSE Transport Layer**: Handles Server-Sent Events communication
2. **MCP Protocol Handler**: Processes MCP messages over SSE
3. **Multi-LLM Integration**: Same provider interfaces as the standard client
4. **Conversation Manager**: Reuses our SQLite-based conversation system
5. **Tool Execution Pipeline**: Same tool execution flow as the standard client

### 2.2 Architecture Overview

The architecture of our SSE-based MCP Client implementation consists of the following components:

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  User Query   │────►│   MCP Client  │────►│  Web Server   │
└───────────────┘     └───────────────┘     └───────────────┘
                             │                      │
                             │                      │
                     ┌───────────────┐              │
                     │  SSE Client   │◄─────────────┘
                     │   Transport   │
                     └───────────────┘
                             │
                             ▼
                      ┌───────────────┐     ┌───────────────┐
                      │  LLM Provider │     │   MCP Tools   │
                      │   Interface   │     └───────────────┘
                      └───────────────┘            ▲
                             │                     │
          ┌──────────────────┴──────────────┐      │
          ▼                                 ▼      │
┌───────────────┐                   ┌───────────────┐
│    Gemini     │                   │     Groq      │
│    Provider   │                   │    Provider   │
└───────────────┘                   └───────────────┘
          │                                 │
          └──────────────────┬──────────────┘
                             ▼
                      ┌───────────────┐
                      │ Conversation  │
                      │    Manager    │
                      └───────────────┘
                             │
                             ▼
                      ┌───────────────┐
                      │    SQLite     │
                      │   Database    │
                      └───────────────┘
```

### Key Component Differences from StdIO Client:

1. **Web Transport Layer**:
   - SSE Client Transport replaces StdIO Transport
   - HTTP-based communication instead of process pipes
   - URL-based server connections instead of file paths
   - Automatic reconnection capabilities
   - Browser-compatible transport protocol

2. **Server Integration**:
   - Connects to web servers instead of local processes
   - Uses standard HTTP protocol
   - Compatible with cloud-based deployments
   - Supports server-side authentication
   - Enables firewall-friendly communications

3. **Connection Management**:
   - Manages HTTP persistent connections
   - Handles SSE event streaming
   - Processes server-initiated messages
   - Maintains asynchronous two-way communication
   - Implements resource cleanup for web connections

4. **Message Processing**:
   - Parses SSE event format
   - Converts between HTTP requests/responses and MCP messages
   - Maintains sequence and ordering of events
   - Handles connection errors and retries
   - Processes event IDs and reconnection states

### 2.3 Implementation Details

The SSE client implementation follows the same modular design as our standard client, with modified transport mechanisms:

```python
async def connect_to_sse_server(self, server_url: str):
    """Establish connection to the MCP server using SSE and prepare tools for LLMs."""
    # Open an SSE connection to the server
    self._streams_context = sse_client(url=server_url)
    streams = await self._streams_context.__aenter__()
    
    # Create an MCP session using the SSE connection
    self._session_context = ClientSession(*streams)
    self.session = await self._session_context.__aenter__()
    
    # Initialize the MCP session
    await self.session.initialize()
    
    # Retrieve available tools and list them
    response = await self.session.list_tools()
    tools = response.tools
    
    print("\nConnected to server with tools:", [tool.name for tool in tools])
    
    # Convert MCP tools for each provider
    for provider_name, provider in self.providers.items():
        provider.convert_tools(tools)
```

### 2.3 Differences from Standard Client

While we maintained the same core functionality, there are several key differences in the SSE implementation:

| Feature | StdIO Client | SSE Client |
|---------|--------------|------------|
| Transport | Standard I/O streams | HTTP with SSE |
| Connection Method | Process spawning | HTTP request |
| URL Format | File path | HTTP URL |
| Server Type | Local process | Web server |
| Reconnection | Manual | Automatic |
| Compatibility | Local systems | Web systems |

## 3. SSE Client Usage

### 3.1 Starting the Client

To use the SSE client, you need:
1. A running SSE-compatible MCP server
2. The server's URL endpoint

```bash
# Start an SSE-compatible MCP server
python test_server_sse.py

# In another terminal or environment
python client_sse.py http://localhost:8081/sse
```

### 3.2 Command-Line Arguments

The SSE client accepts a single required command-line argument: the URL of the SSE server endpoint.

```python
async def main():
    """
    Main entry point for the MCP SSE client application.
    Requires server URL as command line argument.
    """
    if len(sys.argv) < 2:
        print("Usage: python client_sse.py <server_url>")
        print("Example: python client_sse.py http://localhost:8000/mcp-sse")
        sys.exit(1)
    
    server_url = sys.argv[1]
    client = MCPClient()
    
    try:
        await client.connect_to_sse_server(server_url)
        await client.chat_loop()
    finally:
        await client.cleanup()
```

### 3.3 Resource Management

The SSE client carefully manages its resources, particularly the SSE connection and streams:

```python
async def cleanup(self):
    """Clean up resources by properly closing the SSE session and stream contexts."""
    # Close database connection
    self.conversation_manager.close()
    
    # Close SSE session contexts
    if self._session_context:
        await self._session_context.__aexit__(None, None, None)
    if self._streams_context:
        await self._streams_context.__aexit__(None, None, None)
```

## 4. SSE Server Implementation

To test our SSE client, we also implemented a simple SSE-compatible MCP server:

### 4.1 Server Components

The server consists of these key components:

1. **SSE Transport Adapter**: Converts MCP messages to SSE events
2. **HTTP Server**: Handles HTTP connections and routing
3. **MCP Server Instance**: Core MCP server implementation
4. **Tool Registry**: Available tools for the MCP server

### 4.2 Server Implementation Details

```python
def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )
```

## 5. Integration with Multi-LLM Architecture

### 5.1 Maintaining Provider Independence

Our SSE client preserves the multi-LLM provider architecture from the standard client:

1. **Same Provider Interface**: Uses the same `LLMProviderInterface` abstraction
2. **Same Provider Implementations**: Reuses `GeminiProvider` and `GroqProvider` classes
3. **Same Tool Conversion**: Uses identical tool conversion logic
4. **Runtime Provider Switching**: Maintains ability to switch providers during operation

### 5.2 Provider Switching Command

The SSE client preserves the provider switching command:

```
Query: use provider groq
Switched to groq provider

Query: What is the capital of France?
Paris is the capital of France.
```

### 5.3 SQLite Integration

The conversation history database remains identical between the standard and SSE clients, with the same schema and token-aware management.

## 6. Future Enhancements

Several potential enhancements could be made to our SSE client:

1. **WebSocket Transport**: Add WebSocket support for bidirectional communication
2. **Authentication**: Add token-based authentication for secure connections
3. **Multiple Concurrent Connections**: Support parallel server connections
4. **Connection Pooling**: Implement connection reuse and pooling
5. **Server Discovery**: Add automatic server discovery mechanisms
6. **Cross-Origin Support**: Enhance CORS support for browser integration

## 7. Conclusion

By implementing an SSE-based transport mechanism for our MCP client, we've significantly expanded its integration capabilities. This client can now connect to web servers and cloud-based MCP implementations, while maintaining the full functionality of our original design.

The modular architecture proved its value during this enhancement, as we were able to swap out just the transport layer while preserving all other components (providers, conversation manager, and tool execution pipeline).

This SSE-compatible client represents an important step toward building a fully web-integrated AI assistant platform. 