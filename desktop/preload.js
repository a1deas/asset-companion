/**
 * Preload script for security and API bridge
 * Runs in isolated context before renderer
 */
const { contextBridge } = require("electron");

// Expose safe APIs to renderer
contextBridge.exposeInMainWorld("electronAPI", {
  // Platform info
  platform: process.platform,

  // Version info
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  },
});
