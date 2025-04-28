"""Conversation history management with SQLite storage."""

import sqlite3
import json
import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConversationManager:
    """Manages conversation history using SQLite database with token-aware truncation."""
    
    def __init__(self, db_path=":memory:", max_tokens=8000):
        """
        Initialize the conversation manager with SQLite and tree structure.
        
        Args:
            db_path: Path to SQLite database file (default: in-memory)
            max_tokens: Maximum number of tokens to maintain in context
        """
        self.max_tokens = max_tokens
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.current_conversation_id = None
        self._setup_database()
        self._run_migrations()
    
    def _setup_database(self):
        """Create necessary database tables if they don't exist."""
        # Conversations table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            created_at INTEGER,
            last_updated INTEGER
        )
        ''')
        
        # Messages table with tree structure (parent_id for hierarchy)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            parent_id INTEGER,
            role TEXT,
            content TEXT,
            token_count INTEGER,
            timestamp INTEGER,
            type TEXT,
            tool_name TEXT,
            tool_args TEXT,
            tool_result TEXT,
            is_summarized INTEGER DEFAULT 0,
            llm_provider TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id),
            FOREIGN KEY (parent_id) REFERENCES messages (id)
        )
        ''')
        
        self.conn.commit()
    
    def _run_migrations(self):
        """Run database migrations to update schema when needed."""
        # This is a placeholder for future migrations
        pass
    
    def start_new_conversation(self, title=None):
        """Create a new conversation in the database."""
        timestamp = int(time.time())
        title = title or f"Conversation {timestamp}"
        
        self.cursor.execute(
            "INSERT INTO conversations (title, created_at, last_updated) VALUES (?, ?, ?)",
            (title, timestamp, timestamp)
        )
        self.conn.commit()
        
        self.current_conversation_id = self.cursor.lastrowid
        return self.current_conversation_id
    
    def _estimate_token_count(self, text):
        """
        Estimate the number of tokens in a string.
        Simple approximation - actual tokenizers would be more accurate.
        """
        # Very rough estimation: ~4 characters per token for English text
        if not text:
            return 0
        return len(text) // 4 + 1
    
    def add_message(self, role, content, parent_id=None, tool_name=None, tool_args=None, 
                   tool_result=None, llm_provider=None):
        """
        Add a message to the current conversation tree.
        
        Args:
            role: Message role (user, model, tool)
            content: Message content
            parent_id: Parent message ID (for tree structure)
            tool_name: Name of tool if message is a tool call
            tool_args: Tool arguments if applicable
            tool_result: Tool execution result if applicable
            llm_provider: Which LLM provider was used (gemini, groq)
        
        Returns:
            ID of the inserted message
        """
        if not self.current_conversation_id:
            self.start_new_conversation()
        
        timestamp = int(time.time())
        
        # Determine message type
        if tool_name:
            msg_type = "tool_call" if not tool_result else "tool_result"
        else:
            msg_type = "text"
        
        # Estimate token count
        token_count = self._estimate_token_count(content or "")
        if tool_args:
            token_count += self._estimate_token_count(json.dumps(tool_args))
        if tool_result:
            token_count += self._estimate_token_count(json.dumps(tool_result))
        
        # Store in database
        self.cursor.execute(
            """
            INSERT INTO messages 
            (conversation_id, parent_id, role, content, token_count, timestamp, type, 
             tool_name, tool_args, tool_result, llm_provider) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.current_conversation_id, 
                parent_id, 
                role, 
                content, 
                token_count, 
                timestamp, 
                msg_type, 
                tool_name, 
                json.dumps(tool_args) if tool_args else None, 
                json.dumps(tool_result) if tool_result else None,
                llm_provider
            )
        )
        self.conn.commit()
        
        # Update conversation last_updated timestamp
        self.cursor.execute(
            "UPDATE conversations SET last_updated = ? WHERE id = ?",
            (timestamp, self.current_conversation_id)
        )
        self.conn.commit()
        
        return self.cursor.lastrowid

    def _get_path_to_message(self, message_id):
        """Get the path from root to a specific message (for tree traversal)."""
        path = []
        current_id = message_id
        
        while current_id:
            self.cursor.execute(
                "SELECT id, parent_id FROM messages WHERE id = ?", 
                (current_id,)
            )
            row = self.cursor.fetchone()
            if not row:
                break
                
            path.append(row['id'])
            current_id = row['parent_id']
        
        return list(reversed(path))
    
    def get_conversation_for_context(self, latest_message_id=None, include_all_paths=False):
        """
        Retrieve messages for context window while respecting token budget.
        Uses tree structure to prioritize the current conversation path.
        
        Args:
            latest_message_id: ID of the latest message to use as reference point
            include_all_paths: Whether to include all paths in the tree or just the current path
            
        Returns:
            List of messages as raw database rows (not formatted for any specific LLM)
        """
        if not self.current_conversation_id:
            return []
        
        # Get the most recent message if not specified
        if not latest_message_id:
            self.cursor.execute(
                "SELECT id FROM messages WHERE conversation_id = ? ORDER BY timestamp DESC LIMIT 1", 
                (self.current_conversation_id,)
            )
            result = self.cursor.fetchone()
            if result:
                latest_message_id = result['id']
            else:
                return []  # No messages
        
        # Get the path to the latest message
        current_path = self._get_path_to_message(latest_message_id)
        
        # Gather all messages, prioritizing the current path
        all_messages = []
        token_budget = self.max_tokens
        
        # First add messages in the current path
        if current_path:
            placeholders = ', '.join('?' for _ in current_path)
            self.cursor.execute(
                f"""
                SELECT * FROM messages 
                WHERE id IN ({placeholders})
                ORDER BY timestamp ASC
                """, 
                current_path
            )
            path_messages = self.cursor.fetchall()
            
            # Add these messages first (they're the highest priority)
            for msg in path_messages:
                all_messages.append(msg)
                token_budget -= msg['token_count']
        
        # If we want to include other branches and have remaining token budget
        if include_all_paths and token_budget > 0:
            # Get messages not in the current path, ordered by recency
            if current_path:
                placeholders = ', '.join('?' for _ in current_path)
                self.cursor.execute(
                    f"""
                    SELECT * FROM messages 
                    WHERE conversation_id = ? AND id NOT IN ({placeholders})
                    ORDER BY timestamp DESC
                    LIMIT 100  # Reasonable limit to avoid processing too many messages
                    """, 
                    [self.current_conversation_id] + current_path
                )
            else:
                self.cursor.execute(
                    """
                    SELECT * FROM messages 
                    WHERE conversation_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 100
                    """, 
                    (self.current_conversation_id,)
                )
                
            other_messages = self.cursor.fetchall()
            
            # Add as many as fit in the token budget
            for msg in other_messages:
                if token_budget - msg['token_count'] >= 0:
                    all_messages.append(msg)
                    token_budget -= msg['token_count']
                else:
                    break
        
        return sorted(all_messages, key=lambda x: x['timestamp'])
    
    def format_messages_for_gemini(self, messages):
        """Convert database messages to Gemini API format."""
        gemini_messages = []
        
        for msg in messages:
            if msg['type'] == 'text':
                # Regular text message
                gemini_messages.append({
                    'role': msg['role'],
                    'parts': [{'text': msg['content']}]
                })
            elif msg['type'] == 'tool_call':
                # Tool call message
                function_call = {
                    'name': msg['tool_name'],
                    'args': json.loads(msg['tool_args']) if msg['tool_args'] else {}
                }
                
                gemini_messages.append({
                    'role': msg['role'],
                    'parts': [{'function_call': function_call}]
                })
            elif msg['type'] == 'tool_result':
                # Tool result message
                function_response = {
                    'name': msg['tool_name'],
                    'response': json.loads(msg['tool_result']) if msg['tool_result'] else {}
                }
                
                gemini_messages.append({
                    'role': 'tool',
                    'parts': [{'function_response': function_response}]
                })
        
        return gemini_messages
    
    def format_messages_for_groq(self, messages):
        """Convert database messages to Groq API format."""
        groq_messages = []
        
        for msg in messages:
            if msg['type'] == 'text':
                # Regular text message
                role = "assistant" if msg['role'] == "model" else msg['role']
                groq_messages.append({
                    "role": role,
                    "content": msg['content']
                })
            elif msg['type'] == 'tool_call':
                # Tool call message (from assistant)
                if msg['role'] == 'model':
                    # Structure for assistant's tool call
                    groq_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": f"call_{msg['id']}",
                            "type": "function",
                            "function": {
                                "name": msg['tool_name'],
                                "arguments": json.dumps(json.loads(msg['tool_args']) if msg['tool_args'] else {})
                            }
                        }]
                    })
            elif msg['type'] == 'tool_result':
                # Tool result message (from tool)
                groq_messages.append({
                    "role": "tool",
                    "content": json.dumps(json.loads(msg['tool_result']) if msg['tool_result'] else {}),
                    "tool_call_id": f"call_{msg['parent_id']}"
                })
        
        return groq_messages
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close() 