const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// IPC with the main process through the 'api' object
contextBridge.exposeInMainWorld('api', {
  // Receive messages from main process
  receive: (channel, func) => {
    const validChannels = ['backend-url', 'backend-error'];
    if (validChannels.includes(channel)) {
      // Remove event listener if it exists to avoid duplicates
      ipcRenderer.removeAllListeners(channel);
      
      // Add new listener
      ipcRenderer.on(channel, (event, ...args) => func(...args));
    }
  },
  
  // Call main process methods
  restartBackend: async () => {
    return await ipcRenderer.invoke('restart-backend');
  },
  
  // MCP Server configuration methods
  getMcpServers: async () => {
    return await ipcRenderer.invoke('get-mcp-servers');
  },
  
  addMcpServer: async (name, config) => {
    return await ipcRenderer.invoke('add-mcp-server', { name, config });
  },
  
  updateMcpServer: async (name, config) => {
    return await ipcRenderer.invoke('update-mcp-server', { name, config });
  },
  
  deleteMcpServer: async (name) => {
    return await ipcRenderer.invoke('delete-mcp-server', { name });
  }
}); 