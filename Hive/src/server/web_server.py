"""FastAPI web server implementation for MCP-Hive."""

import logging
import uvicorn
import asyncio
from typing import Set, Dict, Any

from fastapi import FastAPI, WebSocket, Request, BackgroundTasks, HTTPException, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

class MCPWebServer:
    """FastAPI web server for the MCP client"""
    
    def __init__(self, mcp_client):
        """
        Initialize the web server.
        
        Args:
            mcp_client: MCP client instance
        """
        self.mcp_client = mcp_client
        self.app = FastAPI(title="MCP-Hive API", description="API for the MCP-Hive backend")
        self.connected_websockets: Set[WebSocket] = set()
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify exact domains
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register FastAPI routes."""
        
        @self.app.get("/")
        async def get_home():
            """Return basic HTML page with client UI."""
            return HTMLResponse(self._get_home_html())
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "ok", "providers": list(self.mcp_client.providers.keys())}
        
        @self.app.get("/providers")
        async def get_providers():
            """List available LLM providers."""
            return {
                "providers": list(self.mcp_client.providers.keys()),
                "current": self.mcp_client.current_provider_name
            }
        
        @self.app.post("/providers/{provider_name}")
        async def set_provider(provider_name: str):
            """Set active LLM provider."""
            result = await self.mcp_client.set_provider(provider_name)
            return {"message": result}
        
        @self.app.get("/servers")
        async def get_servers():
            """List connected MCP servers."""
            server_info = {}
            for name, server in self.mcp_client.servers.items():
                tools = [{"name": tool.name, "description": tool.description} 
                         for tool in server.tools]
                server_info[name] = {
                    "transport": server.transport_type,
                    "tools": tools
                }
            
            return {"servers": server_info}
        
        @self.app.post("/chat")
        async def chat(request: Request, background_tasks: BackgroundTasks):
            """Process a chat message."""
            data = await request.json()
            query = data.get("query")
            conversation_id = data.get("conversation_id")
            
            if not query:
                return JSONResponse(
                    status_code=400,
                    content={"error": "No query provided"}
                )
            
            # Process the query
            result = await self.mcp_client.process_query(query, conversation_id)
            
            # Broadcast the result to WebSocket clients if requested
            if data.get("broadcast", False) and self.connected_websockets:
                background_tasks.add_task(self._broadcast_response, result)
            
            return result
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time chat."""
            await websocket.accept()
            self.connected_websockets.add(websocket)
            
            try:
                while True:
                    # Receive message from client
                    data = await websocket.receive_json()
                    query = data.get("query")
                    conversation_id = data.get("conversation_id")
                    
                    if not query:
                        await websocket.send_json({"error": "No query provided"})
                        continue
                    
                    # Process the query
                    result = await self.mcp_client.process_query(query, conversation_id)
                    
                    # Send response back to this client
                    await websocket.send_json(result)
                    
                    # Broadcast to other clients if requested
                    if data.get("broadcast", False):
                        await self._broadcast_response(result, exclude=websocket)
            
            except WebSocketDisconnect:
                self.connected_websockets.remove(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if websocket in self.connected_websockets:
                    self.connected_websockets.remove(websocket)
    
    async def _broadcast_response(self, result, exclude=None):
        """Broadcast a response to all connected WebSocket clients."""
        disconnected_ws = set()
        for ws in self.connected_websockets:
            if ws != exclude:
                try:
                    await ws.send_json(result)
                except Exception:
                    disconnected_ws.add(ws)
        
        # Remove disconnected WebSockets
        self.connected_websockets -= disconnected_ws
    
    def _get_home_html(self):
        """Return basic HTML for the home page."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>MCP-Hive Client</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    line-height: 1.6;
                }
                h1 {
                    color: #333;
                    text-align: center;
                }
                .chat-container {
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    padding: 20px;
                    margin-top: 20px;
                    height: 400px;
                    overflow-y: auto;
                    background-color: #f9f9f9;
                }
                .message {
                    margin-bottom: 10px;
                    padding: 10px;
                    border-radius: 5px;
                }
                .user {
                    background-color: #e6f7ff;
                    margin-left: 20%;
                    text-align: right;
                }
                .bot {
                    background-color: #f0f0f0;
                    margin-right: 20%;
                }
                .input-container {
                    display: flex;
                    margin-top: 20px;
                }
                #user-input {
                    flex-grow: 1;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    margin-right: 10px;
                }
                button {
                    padding: 10px 20px;
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                }
                button:hover {
                    background-color: #45a049;
                }
                .provider-container {
                    display: flex;
                    justify-content: center;
                    margin-top: 20px;
                    gap: 10px;
                }
                .provider-button {
                    padding: 5px 10px;
                    background-color: #f0f0f0;
                    color: #333;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    cursor: pointer;
                }
                .provider-button.active {
                    background-color: #4CAF50;
                    color: white;
                }
            </style>
        </head>
        <body>
            <h1>MCP-Hive Client</h1>
            <div class="provider-container" id="providers"></div>
            <div class="chat-container" id="chat-box"></div>
            <div class="input-container">
                <input type="text" id="user-input" placeholder="Type your message...">
                <button onclick="sendMessage()">Send</button>
            </div>

            <script>
                let conversationId = null;
                let currentProvider = '';
                
                // Connect WebSocket
                const socket = new WebSocket(`ws://${window.location.host}/ws`);
                
                socket.onopen = () => {
                    console.log('WebSocket connected');
                    addBotMessage('Connected to server. Type a message to begin!');
                    loadProviders();
                };
                
                socket.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.error) {
                        addBotMessage(`Error: ${data.error}`);
                    } else {
                        addBotMessage(data.response);
                        conversationId = data.conversation_id;
                    }
                };
                
                socket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    addBotMessage('Error connecting to server. Please try again later.');
                };
                
                socket.onclose = () => {
                    console.log('WebSocket disconnected');
                    addBotMessage('Disconnected from server.');
                };
                
                async function loadProviders() {
                    try {
                        const response = await fetch('/providers');
                        const data = await response.json();
                        
                        const providersContainer = document.getElementById('providers');
                        providersContainer.innerHTML = '';
                        
                        data.providers.forEach(provider => {
                            const button = document.createElement('button');
                            button.textContent = provider;
                            button.className = 'provider-button';
                            if (provider === data.current) {
                                button.classList.add('active');
                                currentProvider = provider;
                            }
                            button.onclick = () => setProvider(provider);
                            providersContainer.appendChild(button);
                        });
                    } catch (error) {
                        console.error('Error loading providers:', error);
                    }
                }
                
                async function setProvider(provider) {
                    try {
                        const response = await fetch(`/providers/${provider}`, {
                            method: 'POST'
                        });
                        const data = await response.json();
                        
                        // Update active provider button
                        document.querySelectorAll('.provider-button').forEach(button => {
                            button.classList.remove('active');
                            if (button.textContent === provider) {
                                button.classList.add('active');
                                currentProvider = provider;
                            }
                        });
                        
                        addBotMessage(data.message);
                    } catch (error) {
                        console.error('Error setting provider:', error);
                    }
                }
                
                function sendMessage() {
                    const input = document.getElementById('user-input');
                    const message = input.value.trim();
                    
                    if (message) {
                        addUserMessage(message);
                        
                        // Send through WebSocket
                        socket.send(JSON.stringify({
                            query: message,
                            conversation_id: conversationId
                        }));
                        
                        input.value = '';
                    }
                }
                
                function addUserMessage(text) {
                    const chatBox = document.getElementById('chat-box');
                    const message = document.createElement('div');
                    message.className = 'message user';
                    message.textContent = text;
                    chatBox.appendChild(message);
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
                
                function addBotMessage(text) {
                    const chatBox = document.getElementById('chat-box');
                    const message = document.createElement('div');
                    message.className = 'message bot';
                    message.textContent = text;
                    chatBox.appendChild(message);
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
                
                // Allow sending message with Enter key
                document.getElementById('user-input').addEventListener('keypress', function(event) {
                    if (event.key === 'Enter') {
                        sendMessage();
                    }
                });
            </script>
        </body>
        </html>
        """
    
    async def run(self, host="0.0.0.0", port=8000):
        """Run the web server using asyncio."""
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        return await server.serve() 