/**
 * Electron main process for Asset Companion Desktop
 */
const { app, BrowserWindow } = require("electron");
const path = require("path");

// Default API URL (can be configured via environment variable)
const API_PORT = process.env.API_PORT || 8000;
const API_URL = process.env.API_URL || `http://localhost:${API_PORT}`;

let mainWindow = null;

/**
 * Create the main application window
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: "Asset Companion",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
    icon: path.join(__dirname, "assets", "icon.png"), // Optional: add icon
    show: false, // Don't show until ready
  });

  // Load the renderer
  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  // Show window when ready to prevent visual flash
  mainWindow.once("ready-to-show", () => {
    mainWindow.show();

    // Inject API URL into renderer
    mainWindow.webContents.executeJavaScript(`
      window.API_URL = "${API_URL}";
    `);
  });

  // Handle window closed
  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  // Open DevTools in development
  if (process.env.NODE_ENV === "development") {
    mainWindow.webContents.openDevTools();
  }
}

// App event handlers
app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    // On macOS, re-create window when dock icon is clicked
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  // On macOS, keep app running even when all windows are closed
  if (process.platform !== "darwin") {
    app.quit();
  }
});

// Security: Prevent new window creation
app.on("web-contents-created", (event, contents) => {
  contents.on("new-window", (event, navigationUrl) => {
    event.preventDefault();
  });
});
