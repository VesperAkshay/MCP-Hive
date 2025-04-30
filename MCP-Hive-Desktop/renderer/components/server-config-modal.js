/**
 * MCP Server Configuration Modal
 * Provides UI for viewing, adding, editing, and deleting MCP server configurations
 */
class ServerConfigModal {
  constructor() {
    this.isOpen = false;
    this.currentMode = 'add'; // 'add' or 'edit'
    this.currentServerName = '';
    this.serverList = {};
    
    this.createModal();
    this.setupEventListeners();
  }
  
  /**
   * Create the modal HTML
   */
  createModal() {
    // Create modal container
    this.modalContainer = document.createElement('div');
    this.modalContainer.className = 'modal-container';
    this.modalContainer.style.display = 'none';
    
    // Modal content
    this.modalContainer.innerHTML = `
      <div class="modal-backdrop"></div>
      <div class="modal-content">
        <div class="modal-header">
          <h3 id="modal-title">MCP Server Configuration</h3>
          <button id="modal-close-btn" class="modal-close-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
            </svg>
          </button>
        </div>
        
        <div class="modal-body">
          <!-- Server List View -->
          <div id="server-list-view">
            <div class="server-list-header">
              <h4>Configured Servers</h4>
              <button id="add-server-btn" class="btn btn-primary">Add Server</button>
            </div>
            
            <div id="server-table-container" class="server-table-container">
              <table class="server-table">
                <thead>
                  <tr>
                    <th>Server Name</th>
                    <th>Type</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody id="server-table-body">
                  <!-- Server entries will be added here -->
                </tbody>
              </table>
            </div>
          </div>
          
          <!-- Server Edit View -->
          <div id="server-edit-view" style="display: none;">
            <form id="server-form">
              <div class="form-group">
                <label for="server-name">Server Name</label>
                <input type="text" id="server-name" name="server-name" required>
                <div class="help-text">Unique identifier for this server</div>
              </div>
              
              <div class="form-group">
                <label>Server Type</label>
                <div class="radio-group">
                  <label>
                    <input type="radio" name="server-type" value="sse" checked>
                    SSE (Server-Sent Events)
                  </label>
                  <label>
                    <input type="radio" name="server-type" value="command">
                    Command (Subprocess)
                  </label>
                </div>
              </div>
              
              <!-- SSE Configuration -->
              <div id="sse-config">
                <div class="form-group">
                  <label for="sse-url">SSE URL</label>
                  <input type="text" id="sse-url" name="sse-url" placeholder="http://localhost:8081/sse">
                </div>
              </div>
              
              <!-- Command Configuration -->
              <div id="command-config" style="display: none;">
                <div class="form-group">
                  <label for="command-exe">Command</label>
                  <input type="text" id="command-exe" name="command-exe" placeholder="python">
                </div>
                
                <div class="form-group">
                  <label for="command-args">Arguments (one per line)</label>
                  <textarea id="command-args" name="command-args" placeholder="server.py&#10;--port&#10;8081" rows="5"></textarea>
                </div>
              </div>
              
              <div class="form-actions">
                <button type="button" id="cancel-server-btn" class="btn btn-secondary">Cancel</button>
                <button type="submit" id="save-server-btn" class="btn btn-primary">Save Server</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `;
    
    // Add to document
    document.body.appendChild(this.modalContainer);
    
    // Add CSS
    const style = document.createElement('style');
    style.textContent = `
      .modal-container {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 50;
      }
      .modal-backdrop {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0, 0, 0, 0.5);
      }
      .modal-content {
        position: relative;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 90%;
        max-width: 600px;
        max-height: 80vh;
        background-color: #fff;
        border-radius: 6px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        display: flex;
        flex-direction: column;
      }
      .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem;
        border-bottom: 1px solid #e2e8f0;
      }
      .modal-header h3 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 600;
      }
      .modal-close-btn {
        background: none;
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0.25rem;
        border-radius: 0.25rem;
      }
      .modal-close-btn:hover {
        background-color: #f1f5f9;
      }
      .modal-body {
        padding: 1rem;
        overflow-y: auto;
      }
      .server-list-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
      }
      .server-list-header h4 {
        margin: 0;
        font-size: 1rem;
        font-weight: 500;
      }
      .server-table-container {
        max-height: 300px;
        overflow-y: auto;
        border: 1px solid #e2e8f0;
        border-radius: 0.375rem;
      }
      .server-table {
        width: 100%;
        border-collapse: collapse;
      }
      .server-table th, .server-table td {
        padding: 0.75rem 1rem;
        text-align: left;
        border-bottom: 1px solid #e2e8f0;
      }
      .server-table th {
        background-color: #f8fafc;
        font-weight: 500;
        font-size: 0.875rem;
      }
      .server-actions {
        display: flex;
        gap: 0.5rem;
      }
      .form-group {
        margin-bottom: 1rem;
      }
      .form-group label {
        display: block;
        font-size: 0.875rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
      }
      .help-text {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 0.25rem;
      }
      .form-group input[type="text"], .form-group textarea {
        width: 100%;
        padding: 0.5rem;
        border: 1px solid #e2e8f0;
        border-radius: 0.375rem;
        font-size: 0.875rem;
      }
      .radio-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }
      .radio-group label {
        display: flex;
        align-items: center;
        font-weight: normal;
        margin-bottom: 0;
      }
      .radio-group input[type="radio"] {
        margin-right: 0.5rem;
      }
      .form-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        margin-top: 1.5rem;
      }
      .btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        border: none;
      }
      .btn-primary {
        background-color: #5c64ec;
        color: white;
      }
      .btn-primary:hover {
        background-color: #4f56c5;
      }
      .btn-secondary {
        background-color: #e2e8f0;
        color: #475569;
      }
      .btn-secondary:hover {
        background-color: #cbd5e1;
      }
      .btn-danger {
        background-color: #f43f5e;
        color: white;
      }
      .btn-danger:hover {
        background-color: #e11d48;
      }
      .btn-icon {
        padding: 0.25rem;
        border-radius: 0.25rem;
      }
    `;
    document.head.appendChild(style);
  }
  
  /**
   * Setup event listeners for the modal
   */
  setupEventListeners() {
    // Close modal
    document.getElementById('modal-close-btn').addEventListener('click', () => this.close());
    document.querySelector('.modal-backdrop').addEventListener('click', () => this.close());
    
    // Switch between server type configs
    const serverTypeRadios = document.querySelectorAll('input[name="server-type"]');
    serverTypeRadios.forEach(radio => {
      radio.addEventListener('change', () => this.toggleServerTypeConfig());
    });
    
    // Add server button
    document.getElementById('add-server-btn').addEventListener('click', () => this.showAddServerForm());
    
    // Cancel button
    document.getElementById('cancel-server-btn').addEventListener('click', () => this.showServerList());
    
    // Form submission
    document.getElementById('server-form').addEventListener('submit', (e) => this.handleFormSubmit(e));
  }
  
  /**
   * Toggle the server type configuration based on the selected radio button
   */
  toggleServerTypeConfig() {
    const serverType = document.querySelector('input[name="server-type"]:checked').value;
    
    if (serverType === 'sse') {
      document.getElementById('sse-config').style.display = 'block';
      document.getElementById('command-config').style.display = 'none';
    } else {
      document.getElementById('sse-config').style.display = 'none';
      document.getElementById('command-config').style.display = 'block';
    }
  }
  
  /**
   * Show the add server form
   */
  showAddServerForm() {
    this.currentMode = 'add';
    this.currentServerName = '';
    
    document.getElementById('modal-title').textContent = 'Add MCP Server';
    document.getElementById('server-name').value = '';
    document.getElementById('server-name').disabled = false;
    document.querySelector('input[name="server-type"][value="sse"]').checked = true;
    document.getElementById('sse-url').value = '';
    document.getElementById('command-exe').value = '';
    document.getElementById('command-args').value = '';
    
    this.toggleServerTypeConfig();
    
    document.getElementById('server-list-view').style.display = 'none';
    document.getElementById('server-edit-view').style.display = 'block';
  }
  
  /**
   * Show the edit server form
   */
  showEditServerForm(serverName) {
    this.currentMode = 'edit';
    this.currentServerName = serverName;
    
    const serverConfig = this.serverList[serverName];
    
    document.getElementById('modal-title').textContent = 'Edit MCP Server';
    document.getElementById('server-name').value = serverName;
    document.getElementById('server-name').disabled = true;
    
    if (serverConfig.type === 'sse') {
      document.querySelector('input[name="server-type"][value="sse"]').checked = true;
      document.getElementById('sse-url').value = serverConfig.url || '';
    } else {
      document.querySelector('input[name="server-type"][value="command"]').checked = true;
      document.getElementById('command-exe').value = serverConfig.command || '';
      document.getElementById('command-args').value = serverConfig.args ? serverConfig.args.join('\n') : '';
    }
    
    this.toggleServerTypeConfig();
    
    document.getElementById('server-list-view').style.display = 'none';
    document.getElementById('server-edit-view').style.display = 'block';
  }
  
  /**
   * Show the server list view
   */
  showServerList() {
    document.getElementById('server-list-view').style.display = 'block';
    document.getElementById('server-edit-view').style.display = 'none';
  }
  
  /**
   * Handle form submission for adding/editing a server
   */
  async handleFormSubmit(event) {
    event.preventDefault();
    
    const serverName = document.getElementById('server-name').value.trim();
    const serverType = document.querySelector('input[name="server-type"]:checked').value;
    
    let serverConfig = {};
    
    if (serverType === 'sse') {
      serverConfig = {
        type: 'sse',
        url: document.getElementById('sse-url').value.trim()
      };
    } else {
      serverConfig = {
        command: document.getElementById('command-exe').value.trim(),
        args: document.getElementById('command-args').value
          .split('\n')
          .map(arg => arg.trim())
          .filter(arg => arg)
      };
    }
    
    try {
      let result;
      
      if (this.currentMode === 'add') {
        result = await window.api.addMcpServer(serverName, serverConfig);
      } else {
        result = await window.api.updateMcpServer(serverName, serverConfig);
      }
      
      if (result.success) {
        await this.loadServers();
        this.showServerList();
      } else {
        alert(`Failed to ${this.currentMode} server: ${result.error}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    }
  }
  
  /**
   * Load the MCP servers from the configuration
   */
  async loadServers() {
    try {
      const result = await window.api.getMcpServers();
      
      if (result.success) {
        this.serverList = result.servers;
        this.populateServerTable();
      } else {
        console.error('Failed to load servers:', result.error);
      }
    } catch (error) {
      console.error('Error loading servers:', error);
    }
  }
  
  /**
   * Populate the server table with the loaded servers
   */
  populateServerTable() {
    const tableBody = document.getElementById('server-table-body');
    tableBody.innerHTML = '';
    
    if (Object.keys(this.serverList).length === 0) {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td colspan="3" class="text-center">
          No servers configured. Click "Add Server" to create one.
        </td>
      `;
      tableBody.appendChild(row);
      return;
    }
    
    for (const [serverName, serverConfig] of Object.entries(this.serverList)) {
      const row = document.createElement('tr');
      
      const type = serverConfig.type || (serverConfig.command ? 'command' : 'sse');
      
      row.innerHTML = `
        <td>${serverName}</td>
        <td>${type}</td>
        <td class="server-actions">
          <button class="btn btn-secondary btn-icon edit-server" data-server="${serverName}">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
              <path d="m15 5 4 4"/>
            </svg>
          </button>
          <button class="btn btn-danger btn-icon delete-server" data-server="${serverName}">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 6h18"/>
              <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>
              <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
            </svg>
          </button>
        </td>
      `;
      
      tableBody.appendChild(row);
    }
    
    // Add event listeners for edit and delete buttons
    document.querySelectorAll('.edit-server').forEach(button => {
      button.addEventListener('click', () => {
        const serverName = button.getAttribute('data-server');
        this.showEditServerForm(serverName);
      });
    });
    
    document.querySelectorAll('.delete-server').forEach(button => {
      button.addEventListener('click', async () => {
        const serverName = button.getAttribute('data-server');
        
        if (confirm(`Are you sure you want to delete the server "${serverName}"?`)) {
          try {
            const result = await window.api.deleteMcpServer(serverName);
            
            if (result.success) {
              await this.loadServers();
            } else {
              alert(`Failed to delete server: ${result.error}`);
            }
          } catch (error) {
            alert(`Error: ${error.message}`);
          }
        }
      });
    });
  }
  
  /**
   * Open the server configuration modal
   */
  async open() {
    if (this.isOpen) return;
    
    this.isOpen = true;
    this.modalContainer.style.display = 'block';
    
    await this.loadServers();
    this.showServerList();
  }
  
  /**
   * Close the server configuration modal
   */
  close() {
    if (!this.isOpen) return;
    
    this.isOpen = false;
    this.modalContainer.style.display = 'none';
  }
}

// Export the modal class
window.ServerConfigModal = ServerConfigModal; 