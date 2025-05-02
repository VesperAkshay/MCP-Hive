// DOM Elements
const statusIndicator = document.getElementById('status-indicator');
const providerList = document.getElementById('provider-list');
const serverList = document.getElementById('server-list');
const switchProviderBtn = document.getElementById('switch-provider-btn');
const restartBackendBtn = document.getElementById('restart-backend-btn');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');

// Global state
let backendUrl = null;
let selectedProvider = null;
let providers = [];
let isConnected = false;
let currentConversationId = null;

// Handle backend URL received from main process
window.api.receive('backend-url', (url) => {
  backendUrl = url;
  updateStatus('connecting', 'Connecting...');
  
  console.log('Backend URL received:', url);
  initializeApp();
});

// Handle backend error received from main process
window.api.receive('backend-error', (errorMessage) => {
  updateStatus('error', 'Error');
  addSystemMessage(`Backend error: ${errorMessage}`);
  disableUI();
  
  console.error('Backend error:', errorMessage);
});

// Initialize the application
async function initializeApp() {
  try {
    // Check if backend is healthy
    const healthResponse = await fetch(`${backendUrl}/health`);
    if (!healthResponse.ok) {
      throw new Error('Backend health check failed');
    }
    
    const healthData = await healthResponse.json();
    console.log('Health check:', healthData);
    
    // Update status
    updateStatus('connected', 'Connected');
    isConnected = true;
    
    // Enable UI
    enableUI();
    
    // Fetch providers and servers
    await fetchProviders();
    await fetchServers();
    
    // Start a new conversation
    currentConversationId = generateConversationId();
    
  } catch (error) {
    console.error('Failed to initialize app:', error);
    updateStatus('error', 'Error');
    addSystemMessage(`Failed to connect to the backend: ${error.message}`);
    disableUI();
  }
}

// Fetch available LLM providers
async function fetchProviders() {
  try {
    const response = await fetch(`${backendUrl}/providers`);
    const data = await response.json();
    
    providers = data.providers || [];
    selectedProvider = data.current;
    
    // Update the UI
    renderProviderList();
    
    console.log('Providers:', providers);
    console.log('Current provider:', selectedProvider);
    
  } catch (error) {
    console.error('Failed to fetch providers:', error);
    addSystemMessage('Failed to fetch LLM providers');
  }
}

// Fetch connected MCP servers
async function fetchServers() {
  try {
    const response = await fetch(`${backendUrl}/servers`);
    const data = await response.json();
    
    const servers = data.servers || {};
    
    // Update the UI
    renderServerList(servers);
    
    console.log('Servers:', servers);
    
  } catch (error) {
    console.error('Failed to fetch servers:', error);
    addSystemMessage('Failed to fetch MCP servers');
  }
}

// Render the provider list
function renderProviderList() {
  providerList.innerHTML = '';
  
  if (providers.length === 0) {
    const li = document.createElement('li');
    li.className = 'text-sm italic text-muted-foreground';
    li.textContent = 'No providers available';
    providerList.appendChild(li);
    return;
  }
  
  providers.forEach(provider => {
    const li = document.createElement('li');
    
    if (provider === selectedProvider) {
      li.className = 'rounded bg-accent px-2 py-1 text-sm font-medium';
    } else {
      li.className = 'rounded px-2 py-1 text-sm hover:bg-muted/50 cursor-pointer';
    }
    
    li.textContent = provider;
    li.addEventListener('click', () => selectProvider(provider));
    providerList.appendChild(li);
  });
  
  // Enable the switch button if a provider is selected
  switchProviderBtn.disabled = !selectedProvider;
}

// Render the server list
function renderServerList(servers) {
  serverList.innerHTML = '';
  
  const serverNames = Object.keys(servers);
  
  if (serverNames.length === 0) {
    const li = document.createElement('li');
    li.className = 'text-sm italic text-muted-foreground';
    li.textContent = 'No servers connected';
    serverList.appendChild(li);
    return;
  }
  
  serverNames.forEach(serverName => {
    const serverInfo = servers[serverName];
    
    const li = document.createElement('li');
    li.className = 'mb-2 rounded bg-card p-2 text-sm shadow-sm';
    
    // Create card structure for server info
    const card = document.createElement('div');
    
    // Server name with transport type
    const nameContainer = document.createElement('div');
    nameContainer.className = 'flex justify-between items-center mb-1';
    
    const nameSpan = document.createElement('span');
    nameSpan.className = 'font-semibold';
    nameSpan.textContent = serverName;
    
    const transportBadge = document.createElement('span');
    transportBadge.className = 'text-xs bg-secondary px-1.5 py-0.5 rounded-full';
    transportBadge.textContent = serverInfo.transport;
    
    nameContainer.appendChild(nameSpan);
    nameContainer.appendChild(transportBadge);
    
    // Tools count
    const toolsCount = document.createElement('div');
    toolsCount.className = 'text-xs text-muted-foreground';
    toolsCount.textContent = `${serverInfo.tools.length} tools available`;
    
    card.appendChild(nameContainer);
    card.appendChild(toolsCount);
    li.appendChild(card);
    
    serverList.appendChild(li);
  });
}

// Select a provider
function selectProvider(provider) {
  selectedProvider = provider;
  renderProviderList();
}

// Switch to selected provider
async function switchProvider() {
  if (!selectedProvider || !isConnected) return;
  
  try {
    const response = await fetch(`${backendUrl}/providers/${selectedProvider}`, {
      method: 'POST'
    });
    
    const data = await response.json();
    addSystemMessage(data.message);
    
    console.log('Provider switched:', data);
    
  } catch (error) {
    console.error('Failed to switch provider:', error);
    addSystemMessage(`Failed to switch provider: ${error.message}`);
  }
}

// Send a chat message
async function sendChatMessage() {
  const query = chatInput.value.trim();
  if (!query || !isConnected) return;
  
  // Clear input
  chatInput.value = '';
  
  // Add message to UI
  addUserMessage(query);
  
  // Disable input during processing
  chatInput.disabled = true;
  sendBtn.disabled = true;
  
  try {
    const response = await fetch(`${backendUrl}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query,
        conversation_id: currentConversationId
      })
    });
    
    const data = await response.json();
    
    // Add response to UI
    addAssistantMessage(data.response || '(No response)');
    
    console.log('Chat response:', data);
    
  } catch (error) {
    console.error('Failed to send chat message:', error);
    addSystemMessage(`Failed to send message: ${error.message}`);
  } finally {
    // Re-enable input
    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

// Add a user message to the chat
function addUserMessage(message) {
  const messageEl = document.createElement('div');
  messageEl.className = 'chat-message-user';
  messageEl.textContent = message;
  chatMessages.appendChild(messageEl);
  
  // Scroll to bottom
  scrollChatToBottom();
}

// Add an assistant message to the chat
function addAssistantMessage(message) {
  const messageEl = document.createElement('div');
  messageEl.className = 'chat-message-assistant';
  messageEl.textContent = message;
  chatMessages.appendChild(messageEl);
  
  // Scroll to bottom
  scrollChatToBottom();
}

// Add a system message to the chat
function addSystemMessage(message) {
  const messageEl = document.createElement('div');
  messageEl.className = 'chat-message-system';
  messageEl.textContent = message;
  chatMessages.appendChild(messageEl);
  
  // Scroll to bottom
  scrollChatToBottom();
}

// Scroll the chat container to the bottom
function scrollChatToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Update the status indicator
function updateStatus(status, text) {
  statusIndicator.textContent = text;
  statusIndicator.className = `status-badge status-badge-${status}`;
}

// Enable UI elements
function enableUI() {
  chatInput.disabled = false;
  sendBtn.disabled = false;
  switchProviderBtn.disabled = !selectedProvider;
}

// Disable UI elements
function disableUI() {
  chatInput.disabled = true;
  sendBtn.disabled = true;
  switchProviderBtn.disabled = true;
}

// Generate a random conversation ID
function generateConversationId() {
  return `conv_${Math.random().toString(36).substring(2, 15)}`;
}

// Event listeners
switchProviderBtn.addEventListener('click', switchProvider);
restartBackendBtn.addEventListener('click', restartBackend);
sendBtn.addEventListener('click', sendChatMessage);

chatInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendChatMessage();
  }
});

// Restart the backend
async function restartBackend() {
  try {
    updateStatus('connecting', 'Restarting...');
    addSystemMessage('Restarting backend...');
    disableUI();
    
    const result = await window.api.restartBackend();
    
    if (result.success) {
      addSystemMessage(`Backend restarted on port ${result.port}`);
      setTimeout(initializeApp, 1000); // Wait a bit for the server to initialize
    } else {
      updateStatus('error', 'Error');
      addSystemMessage(`Failed to restart backend: ${result.error}`);
    }
    
  } catch (error) {
    console.error('Failed to restart backend:', error);
    updateStatus('error', 'Error');
    addSystemMessage(`Failed to restart backend: ${error.message}`);
  }
} 

// Initialize server config modal
let serverConfigModal;

// Create modal instance when DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
  serverConfigModal = new ServerConfigModal();
});

// Server management button
document.getElementById('manage-servers-btn').addEventListener('click', () => {
  if (serverConfigModal) {
    serverConfigModal.open();
  }
});

// Update the refreshServerList function to load servers from the configuration
async function refreshServerList() {
  const serverList = document.getElementById('server-list');
  
  try {
    // Get servers from the backend API
    const response = await fetch(`${backendUrl}/servers`);
    const data = await response.json();
    
    // Clear the list
    serverList.innerHTML = '';
    
    if (data.servers && Object.keys(data.servers).length > 0) {
      // Add each server to the list
      for (const [name, info] of Object.entries(data.servers)) {
        const listItem = document.createElement('li');
        listItem.className = 'p-2 text-sm bg-white rounded shadow-sm mb-1';
        
        const toolCount = info.tools ? info.tools.length : 0;
        
        listItem.innerHTML = `
          <div class="font-medium">${name}</div>
          <div class="text-xs text-muted-foreground">
            ${info.transport || 'Unknown'} | ${toolCount} tools
          </div>
        `;
        
        serverList.appendChild(listItem);
      }
    } else {
      // No servers connected
      const listItem = document.createElement('li');
      listItem.className = 'text-sm italic text-muted-foreground';
      listItem.textContent = 'No servers connected';
      serverList.appendChild(listItem);
    }
  } catch (error) {
    console.error('Error fetching servers:', error);
    serverList.innerHTML = '<li class="text-sm italic text-red-500">Error loading servers</li>';
  }
}

// Add server config reload after backend restart
document.getElementById('restart-backend-btn').addEventListener('click', async () => {
  const button = document.getElementById('restart-backend-btn');
  button.disabled = true;
  button.textContent = 'Restarting...';
  
  try {
    const result = await window.api.restartBackend();
    
    if (result.success) {
      updateStatus('connected', 'Backend restarted successfully');
      backendUrl = `http://localhost:${result.port}`;
      
      // Refresh providers and servers after restart
      await refreshProviderList();
      await refreshServerList();
      
      // If we have a server config modal, refresh its data
      if (serverConfigModal) {
        await serverConfigModal.loadServers();
      }
      
    } else {
      updateStatus('error', `Failed to restart backend: ${result.error}`);
    }
  } catch (error) {
    console.error('Error restarting backend:', error);
    updateStatus('error', 'Error restarting backend');
  } finally {
    button.disabled = false;
    button.textContent = 'Restart Backend';
  }
}); 