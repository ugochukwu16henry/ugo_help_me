const { app, BrowserWindow, globalShortcut, ipcMain } = require('electron');
const path = require('path');

let mainWindow;
let interactiveMode = false;

function applyInteractionMode() {
  if (!mainWindow) {
    return;
  }

  mainWindow.setIgnoreMouseEvents(!interactiveMode, { forward: true });
  mainWindow.webContents.send('interaction-changed', interactiveMode);
}

function toggleInteractionMode() {
  interactiveMode = !interactiveMode;
  applyInteractionMode();
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 310,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.setContentProtection(true);
  mainWindow.setAlwaysOnTop(true, 'screen-saver');
  applyInteractionMode();

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

app.whenReady().then(() => {
  ipcMain.handle('overlay:get-interaction', () => interactiveMode);
  ipcMain.handle('overlay:set-interaction', (_event, enabled) => {
    interactiveMode = Boolean(enabled);
    applyInteractionMode();
    return interactiveMode;
  });

  globalShortcut.register('CommandOrControl+Shift+I', () => {
    toggleInteractionMode();
  });

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});
