# Chapter 1: Building an MCP Client with Multi-LLM Support

*Author: Akshay Patel*  
*Date: April 19, 2025*  
*Course: Advanced AI Integration Systems*

---

## 1. Introduction to MCP Client Architecture

The MCP (Multi-modal Capability Protocol) client we've built establishes a communication bridge between user queries and server-side tools while leveraging multiple LLM providers for natural language understanding. This document provides detailed notes on the system we've developed.

### 1.1 Core Components

Our MCP client system consists of the following key components:

1. **MCP Client Session**: Manages communication with the MCP server
2. **Multi-LLM Integration**: Supports multiple LLM providers (Gemini and Groq)
3. **Conversation Manager**: Uses SQLite database for persistent, token-aware conversation tracking
4. **Tool Execution Pipeline**: Handles the full lifecycle of tool calls and responses
5. **Provider Interface**: Abstract interface for different LLM providers

## 1.2 Architecture Overview

The architecture of our StdIO-based MCP Client implementation consists of several interconnected components:

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  User Query   │────►│   MCP Client  │────►│  MCP Server   │
└───────────────┘     └───────────────┘     └───────────────┘
                             │                      │
                             ▼                      ▼
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

### Key Components and Data Flow:

1. **User Query Flow**:
   - User submits natural language query
   - MCP Client processes query with active LLM provider
   - Provider determines if tool execution is needed
   - Tool calls are processed through MCP Server
   - Results are returned to user

2. **Provider Architecture**:
   - Abstract LLM Provider Interface defines common behavior
   - Concrete implementations for Gemini and Groq
   - Each provider converts MCP tools to provider-specific format
   - Runtime provider switching capability

3. **Data Storage**:
   - Conversation Manager maintains interaction history
   - SQLite backend with tree structure for conversations
   - Token-aware context management
   - Persistent storage between sessions

4. **Communication Layer**:
   - StdIO-based bidirectional communication with MCP server
   - Serialized JSON messages between client and server
   - Asynchronous processing model with asyncio

## 2. Database-Backed Conversation System

### 2.1 SQLite Database Schema

We implemented a SQLite-based conversation manager with the following structure:

```sql
-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    created_at INTEGER,
    last_updated INTEGER
)

-- Messages table with tree structure
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER,
    parent_id INTEGER,  -- For tree structure
    role TEXT,          -- 'user', 'model', or 'tool'
    content TEXT,       -- Actual message content
    token_count INTEGER,
    timestamp INTEGER,
    type TEXT,          -- 'text', 'tool_call', or 'tool_result'
    tool_name TEXT,
    tool_args TEXT,
    tool_result TEXT,
    is_summarized INTEGER DEFAULT 0,
    llm_provider TEXT,  -- Which LLM provider was used (gemini, groq)
    FOREIGN KEY (conversation_id) REFERENCES conversations (id),
    FOREIGN KEY (parent_id) REFERENCES messages (id)
)
```

### 2.2 Tree-Based Conversation Structure

Unlike a simple list-based conversation history, we've implemented a tree structure that:

- Tracks parent-child relationships between messages
- Maintains conversation branches (useful for exploring different tool paths)
- Uses message IDs to create a linked structure in the database
- Enables context-aware retrieval focusing on the current conversation path

### 2.3 Token-Aware Context Management

To stay within LLM context limits:

- We estimate token counts for each message
- Track cumulative token usage along conversation paths
- Prioritize messages in the active path for context construction
- Use a configurable maximum token budget (default: 8000 tokens)

### 2.4 Database Configuration and Persistence

By default, the database operates in-memory and doesn't persist between program runs. To enable conversation persistence:

1. **Set Environment Variables**: 
   ```
   CONVERSATION_DB_PATH=./conversations.db
   MAX_CONTEXT_TOKENS=8000
   ```

2. **Database Location**:
   - When using `:memory:` (default), database exists only in RAM during runtime
   - When specifying a file path, database persists across sessions
   - The database file is created automatically on first run
   - All conversations, messages, and tool call history are preserved

3. **Implementation Details**:
   ```python
   # In MCPClient.__init__
   db_path = os.getenv("CONVERSATION_DB_PATH", ":memory:")
   max_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", "8000"))
   self.conversation_manager = ConversationManager(db_path, max_tokens)
   ```

4. **Benefits of Persistence**:
   - Long-term conversation history retention
   - Analysis of past interactions
   - Ability to resume conversations after program restarts
   - Building more complex conversational applications with memory

### 2.5 Evolution of Our Implementation

Our conversation management system has evolved significantly through different iterations:

#### Initial Implementation (Version 1.0)
In our first version, we used a simple list-based approach to store conversation history:

```python
# Initial naive implementation
conversation_history = [user_prompt_content]  # Simple list
```

This approach had several limitations:
- Memory usage grew unbounded as conversations lengthened
- No persistence between sessions
- No ability to handle complex multi-turn reasoning
- Limited to linear conversation flow
- Crashed when handling multiple sequential tool calls

#### List with Multi-Tool Support (Version 1.5)
We enhanced the implementation to support multiple tool calls in sequence:

```python
# Added support for sequential tool calls
while True:
    has_function_call = False
    # Process response looking for tool calls
    # ...
    if not has_function_call:
        break  # Exit when no more tool calls
```

This solved the immediate crashes but still had fundamental limitations:
- Still used in-memory storage only
- No context management for long conversations
- No persistence between program runs
- Linear conversation structure

#### Current Implementation (Version 2.0)
Our current database-backed implementation addresses all previous limitations:
- Uses SQLite for persistent storage
- Implements a tree structure for branching conversations
- Provides token-aware context management
- Handles complex object serialization
- Supports configurable token budgets
- Prioritizes the current conversation path

#### Latest Enhancement (Version 3.0)
We've now added support for multiple LLM providers:
- Abstracted LLM provider interactions into a common interface
- Added support for both Google's Gemini and Groq's LLMs
- Implemented provider-specific formatting for each LLM
- Added runtime switching between providers
- Enhanced database schema to track which provider handled which messages

## 3. Multi-LLM Provider Architecture

### 3.1 Provider Interface Design

We've implemented a modular LLM provider system with a common interface:

```python
class LLMProviderInterface:
    """Base interface for different LLM providers"""
    
    def __init__(self):
        self.function_declarations = None
    
    async def initialize(self):
        """Initialize the LLM provider"""
        pass
    
    async def process_query(self, query, conversation_history, mcp_client):
        """Process a query using this LLM provider"""
        raise NotImplementedError("Subclasses must implement process_query")
    
    def convert_tools(self, mcp_tools):
        """Convert MCP tools to provider-specific format"""
        raise NotImplementedError("Subclasses must implement convert_tools")
```

This interface allows us to:
- Add new providers with minimal code changes
- Switch between providers at runtime
- Handle provider-specific quirks in isolated implementations

### 3.2 Supported LLM Providers

#### 3.2.1 Google Gemini

Gemini is characterized by:
- Strong multi-modal capabilities
- Progressive function calling with real-time reasoning
- Unique content and part structures for responses

The Gemini provider implementation:
- Uses the `google-generativeai` Python library
- Converts MCP tools to Gemini's FunctionDeclaration format
- Formats conversation history to match Gemini's Content/Part structure
- Parses tool call responses from Gemini's function_call objects

#### 3.2.2 Groq

Groq is characterized by:
- Extremely low latency responses
- OpenAI-compatible API
- Support for Chat Completion style interactions

The Groq provider implementation:
- Uses the `groq` Python library
- Converts MCP tools to OpenAI-compatible tool format
- Formats conversation history as chat messages
- Parses tool call responses from Groq's tool_calls objects

### 3.3 Provider Configuration

The client supports provider configuration via environment variables:

```python
# Initialize LLM providers
gemini_api_key = os.getenv("GEMINI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

self.providers = {}
if gemini_api_key:
    self.providers["gemini"] = GeminiProvider(gemini_api_key)
if groq_api_key:
    self.providers["groq"] = GroqProvider(groq_api_key)
    
# Set default provider
default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "gemini")
```

Users can:
- Configure multiple providers simultaneously
- Set a default provider
- Switch providers during runtime with "use provider <name>" commands

## 4. Multi-Step Tool Execution

### 4.1 Handling Sequential Tool Calls

For complex requests requiring multiple operations:

1. User query is added to the conversation history
2. The chosen LLM generates a response, potentially including a tool call
3. The tool is executed and results are stored in conversation history
4. Updated conversation is sent back to the same LLM for next steps
5. Process repeats until the LLM provides a final text response

### 4.2 Key Challenges

Several challenges were addressed:

- **API Differences**: Each LLM has different API structures and formats
- **JSON Serialization**: Tool results needed to be converted to JSON-serializable format
- **Token Management**: Keeping context within model limits for long conversations
- **Tree Navigation**: Finding the correct path through the conversation tree
- **Error Handling**: Gracefully handling tool execution failures

## 5. Message Processing Pipeline

The query processing flow follows these steps:

1. **Provider Selection**: Determine which LLM provider to use
2. **Request Initiation**: User submits a text query
3. **Conversation Storage**: Query is added to conversation database
4. **Context Retrieval**: Token-aware context is retrieved from database
5. **Provider Formatting**: Context is formatted for the specific LLM provider
6. **Initial Model Call**: Query + context sent to selected LLM
7. **Tool Call Detection**: Check if model response contains tool calls
8. **Tool Execution**: If tool call present, execute the tool
9. **Result Processing**: Format tool result and add to conversation
10. **Continued Processing**: Send updated context back to LLM
11. **Final Response**: Extract text response when no more tool calls remain

## 6. Optimizations and Future Improvements

### 6.1 Current Optimizations

- **Token-aware truncation**: Only includes messages that fit in context window
- **Tree structure**: Prioritizes current conversation path
- **JSON serialization**: Handles complex object types gracefully
- **Persistent storage**: Preserves conversations across sessions
- **Provider abstraction**: Common interface for different LLMs
- **Provider switching**: Runtime ability to change LLM providers

### 6.2 Potential Future Enhancements

- **Conversation summarization**: Compress older parts of conversation
- **Caching common tool results**: Avoid redundant tool calls
- **Enhanced token estimation**: Use actual LLM-specific tokenizers
- **Context prioritization**: Smart selection of which messages to include
- **Query clustering**: Group related queries for better context management
- **Provider fallback**: Automatic switching if a provider fails
- **Provider comparison**: Ask multiple providers and compare responses
- **Hybrid responses**: Combine responses from multiple providers

---

## Code Implementation Notes

### Main MCPClient Class

The central MCPClient class handles:

1. Initialization of LLM providers and database
2. Server connection and tool discovery
3. Query processing and tool execution
4. Conversation management and context building
5. Provider selection and switching

### Provider Classes

Each LLM provider is implemented as a separate class that:

1. Handles provider-specific authentication
2. Converts tools to provider-specific formats
3. Formats conversation history for that provider
4. Processes responses in provider-specific ways

### ConversationManager Class

The ConversationManager handles conversation persistence and retrieval:

- `add_message()`: Adds a message to the conversation tree
- `get_conversation_for_context()`: Retrieves context-appropriate messages
- `format_messages_for_gemini()`: Formats messages for Gemini API
- `format_messages_for_groq()`: Formats messages for Groq API
- `_get_path_to_message()`: Finds path from root to specific message

### Environment Configuration

The system supports configuration via environment variables:

- `GEMINI_API_KEY`: Authentication for Gemini API
- `GROQ_API_KEY`: Authentication for Groq API
- `GEMINI_MODEL`: Which Gemini model to use
- `GROQ_MODEL`: Which Groq model to use
- `DEFAULT_LLM_PROVIDER`: Default provider to use
- `CONVERSATION_DB_PATH`: Location of SQLite database
- `MAX_CONTEXT_TOKENS`: Token budget for conversations

---

*Note: This implementation demonstrates advanced concepts in AI-assisted systems including multiple LLM integration, database persistence, token-aware context management, and tree-based conversation tracking.* 