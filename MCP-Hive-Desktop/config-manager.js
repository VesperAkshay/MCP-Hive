const fs = require('fs');
const path = require('path');
const log = require('electron-log');
const isDev = require('electron-is-dev');

class ConfigManager {
  constructor() {
    // Determine the path to the Hive folder
    this.resourcesPath = isDev 
      ? path.join(__dirname, '../Hive') 
      : path.join(process.resourcesPath, 'Hive');
    
    this.configPath = path.join(this.resourcesPath, 'Mcphive_config.json');
    
    log.info(`Config path: ${this.configPath}`);
    
    // Create default config if it doesn't exist
    this.ensureConfigExists();
  }
  
  /**
   * Ensure the configuration file exists, creating it with default values if necessary
   */
  ensureConfigExists() {
    try {
      if (!fs.existsSync(this.configPath)) {
        log.info('Creating default Mcphive_config.json');
        
        const defaultConfig = {
          mcpServers: {
            calculator_server: {
              type: "sse",
              url: "http://localhost:8081/sse"
            },
            filesystem: {
              command: "npx",
              args: [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                "."
              ]
            }
          }
        };
        
        fs.writeFileSync(this.configPath, JSON.stringify(defaultConfig, null, 2), 'utf8');
        log.info('Default configuration file created');
      }
    } catch (error) {
      log.error('Error ensuring config exists:', error);
      throw error;
    }
  }
  
  /**
   * Read the configuration file
   * @returns {Object} The configuration object
   */
  readConfig() {
    try {
      this.ensureConfigExists();
      const configJson = fs.readFileSync(this.configPath, 'utf8');
      return JSON.parse(configJson);
    } catch (error) {
      log.error('Error reading config:', error);
      throw error;
    }
  }
  
  /**
   * Write the configuration file
   * @param {Object} config - The configuration object to write
   */
  writeConfig(config) {
    try {
      fs.writeFileSync(this.configPath, JSON.stringify(config, null, 2), 'utf8');
      log.info('Configuration file updated');
    } catch (error) {
      log.error('Error writing config:', error);
      throw error;
    }
  }
  
  /**
   * Get all MCP servers from the configuration
   * @returns {Object} All MCP servers
   */
  getAllServers() {
    const config = this.readConfig();
    return config.mcpServers || {};
  }
  
  /**
   * Add a new MCP server to the configuration
   * @param {string} name - The name of the server
   * @param {Object} serverConfig - The server configuration
   * @returns {boolean} Success status
   */
  addServer(name, serverConfig) {
    try {
      const config = this.readConfig();
      
      if (!config.mcpServers) {
        config.mcpServers = {};
      }
      
      config.mcpServers[name] = serverConfig;
      this.writeConfig(config);
      return true;
    } catch (error) {
      log.error('Error adding server:', error);
      return false;
    }
  }
  
  /**
   * Update an existing MCP server in the configuration
   * @param {string} name - The name of the server
   * @param {Object} serverConfig - The updated server configuration
   * @returns {boolean} Success status
   */
  updateServer(name, serverConfig) {
    return this.addServer(name, serverConfig);
  }
  
  /**
   * Delete an MCP server from the configuration
   * @param {string} name - The name of the server to delete
   * @returns {boolean} Success status
   */
  deleteServer(name) {
    try {
      const config = this.readConfig();
      
      if (!config.mcpServers || !config.mcpServers[name]) {
        return false;
      }
      
      delete config.mcpServers[name];
      this.writeConfig(config);
      return true;
    } catch (error) {
      log.error('Error deleting server:', error);
      return false;
    }
  }
}

module.exports = ConfigManager; 