const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const isDev = require('electron-is-dev');
const { spawn } = require('child_process');
const log = require('electron-log');
const fs = require('fs');
const ConfigManager = require('./config-manager');

// Configure logging
log.transports.file.level = 'info';
log.transports.console.level = 'debug';

// Global reference to main window
let mainWindow;
// Global reference to Python process
let pythonProcess = null;
// Port for the backend server
const backendPort = 8000;
// Configuration manager
const configManager = new ConfigManager();

function createWindow() {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'assets', 'Hive-Icon.ico'),
    title: "MCP Hive Desktop"
  });

  // Load the index.html
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  // Open DevTools in development mode
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  // Emitted when the window is closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Start the Python backend server
async function startPythonBackend() {
  return new Promise((resolve, reject) => {
    try {
      // Get the path to the resources folder
      const resourcesPath = isDev 
        ? path.join(__dirname, '../Hive') 
        : path.join(process.resourcesPath, 'Hive');
      
      log.info(`Resources path: ${resourcesPath}`);
      
      // Path to the executable backend
      const backendExe = process.platform === 'win32' 
        ? path.join(resourcesPath, 'mcp_hive_backend.exe') 
        : path.join(resourcesPath, 'mcp_hive_backend');
      
      // Create a sample .env file if it doesn't exist
      const envPath = path.join(resourcesPath, '.env');
      if (!fs.existsSync(envPath)) {
        log.info('Creating sample .env file');
        const sampleEnvContent = `# API Keys for LLM Providers (Replace with your actual keys)
GROQ_API_KEY=your_groq_api_key_here

# Default provider
DEFAULT_LLM_PROVIDER=groq

# Server settings
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
`;
        fs.writeFileSync(envPath, sampleEnvContent);
      }
      
      // Read the .env file to use as environment variables
      const envContent = fs.readFileSync(envPath, 'utf8');
      const envVars = {};
      
      // Parse each line of the .env file
      envContent.split('\n').forEach(line => {
        // Skip comments and empty lines
        if (line.trim().startsWith('#') || line.trim() === '') return;
        
        // Extract key and value
        const [key, ...valueParts] = line.split('=');
        if (key && valueParts.length > 0) {
          const value = valueParts.join('='); // Handle values that might contain = signs
          envVars[key.trim()] = value.trim();
        }
      });
      
      log.info('Loaded environment variables from .env file');
      
      // Make sure the config file exists before starting the backend
      configManager.ensureConfigExists();
      
      log.info(`Starting backend executable: ${backendExe} --server --port ${backendPort}`);
      
      // Spawn the backend executable process with the environment variables from .env
      pythonProcess = spawn(backendExe, ['--server', '--port', backendPort.toString()], {
        cwd: resourcesPath,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, ...envVars },
        windowsHide: true // Hide the console window on Windows
      });
      
      // Handle stdout
      pythonProcess.stdout.on('data', (data) => {
        const output = data.toString().trim();
        log.info(`Backend stdout: ${output}`);
        
        // Check if server is running
        if (output.includes('Application startup complete') || 
            output.includes('Running on http://') ||
            output.includes('Server started on port')) {
          resolve(backendPort);
        }
      });
      
      // Handle stderr
      pythonProcess.stderr.on('data', (data) => {
        const output = data.toString().trim();
        log.error(`Backend stderr: ${output}`);
      });
      
      // Handle process exit
      pythonProcess.on('exit', (code) => {
        log.info(`Backend process exited with code ${code}`);
        pythonProcess = null;
        
        if (code !== 0) {
          if (mainWindow) {
            mainWindow.webContents.send('backend-error', `Backend server crashed with code ${code}`);
          }
        }
      });
      
      // Set a timeout in case the server doesn't start
      setTimeout(() => {
        if (pythonProcess) {
          resolve(backendPort); // Assume it's running even if we didn't see the message
        } else {
          reject(new Error('Backend server failed to start'));
        }
      }, 10000);
      
    } catch (error) {
      log.error('Failed to start backend:', error);
      reject(error);
    }
  });
}

// When Electron has finished initialization
app.whenReady().then(async () => {
  try {
    // Start the Python backend
    const port = await startPythonBackend();
    log.info(`Backend started on port ${port}`);
    
    // Create the main window
    createWindow();
    
    // Send the backend URL to the renderer
    if (mainWindow) {
      mainWindow.webContents.on('did-finish-load', () => {
        mainWindow.webContents.send('backend-url', `http://localhost:${port}`);
      });
    }
    
    // Re-create window on macOS when clicking on dock icon
    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  } catch (error) {
    log.error('Failed during app startup:', error);
    dialog.showErrorBox('Startup Error', `Failed to start the application: ${error.message}`);
    app.quit();
  }
});

// Kill the Python process when the app is about to quit
app.on('before-quit', () => {
  if (pythonProcess) {
    log.info('Killing Python backend process');
    pythonProcess.kill();
    pythonProcess = null;
  }
});

// Quit when all windows are closed, except on macOS
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC handlers
ipcMain.handle('restart-backend', async () => {
  try {
    if (pythonProcess) {
      pythonProcess.kill();
      pythonProcess = null;
    }
    
    const port = await startPythonBackend();
    return { success: true, port };
  } catch (error) {
    log.error('Failed to restart backend:', error);
    return { success: false, error: error.message };
  }
});

// MCP Server configuration handlers
ipcMain.handle('get-mcp-servers', async () => {
  try {
    const servers = configManager.getAllServers();
    return { success: true, servers };
  } catch (error) {
    log.error('Failed to get MCP servers:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('add-mcp-server', async (event, { name, config }) => {
  try {
    const success = configManager.addServer(name, config);
    return { success };
  } catch (error) {
    log.error('Failed to add MCP server:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('update-mcp-server', async (event, { name, config }) => {
  try {
    const success = configManager.updateServer(name, config);
    return { success };
  } catch (error) {
    log.error('Failed to update MCP server:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('delete-mcp-server', async (event, { name }) => {
  try {
    const success = configManager.deleteServer(name);
    return { success };
  } catch (error) {
    log.error('Failed to delete MCP server:', error);
    return { success: false, error: error.message };
  }
}); 