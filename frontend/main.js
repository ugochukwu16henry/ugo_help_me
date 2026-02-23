const { app, BrowserWindow, globalShortcut, ipcMain, Menu, Tray, nativeImage } = require('electron');
const path = require('path');

let mainWindow;
let interactiveMode = false;
let tray = null;
let isQuitting = false;
const startHidden = true;

const singleInstanceLock = app.requestSingleInstanceLock();
if (!singleInstanceLock) {
  app.quit();
}

const runtimeDataPath = path.join(app.getPath('temp'), 'ugo-overlay-runtime');
app.setPath('userData', runtimeDataPath);
app.setPath('sessionData', runtimeDataPath);

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
  refreshTrayMenu();
}

function toggleVisibility() {
  if (!mainWindow) {
    return;
  }

  if (mainWindow.isVisible()) {
    mainWindow.hide();
    refreshTrayMenu();
    return;
  }

  mainWindow.show();
  mainWindow.focus();
  applyInteractionMode();
  refreshTrayMenu();
}

function createTray() {
  const icon = nativeImage.createFromDataURL(
    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAQAAAC1+jfqAAAAKElEQVR4AWNABf7//z8DGfAfxP8MDAwM/4fB8J+B4T8GBgaG/wxkAAAEAw0AbQ1R6QAAAABJRU5ErkJggg=='
  );
  tray = new Tray(icon);
  tray.setToolTip('UGO Overlay');
  tray.on('click', () => {
    toggleVisibility();
  });
  refreshTrayMenu();
}

function refreshTrayMenu() {
  if (!tray) {
    return;
  }

  const visible = Boolean(mainWindow && mainWindow.isVisible());
  const contextMenu = Menu.buildFromTemplate([
    {
      label: visible ? 'Hide Overlay' : 'Show Overlay',
      click: () => toggleVisibility()
    },
    {
      label: interactiveMode ? 'Lock Controls' : 'Unlock Controls',
      click: () => toggleInteractionMode()
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);
  tray.setContextMenu(contextMenu);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 310,
    frame: false,
    transparent: true,
    show: false,
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

  if (!startHidden) {
    mainWindow.show();
  }

  mainWindow.on('close', (event) => {
    if (isQuitting) {
      return;
    }
    event.preventDefault();
    mainWindow.hide();
    refreshTrayMenu();
  });

  mainWindow.on('show', refreshTrayMenu);
  mainWindow.on('hide', refreshTrayMenu);
}

app.whenReady().then(() => {
  ipcMain.handle('overlay:get-interaction', () => interactiveMode);
  ipcMain.handle('overlay:set-interaction', (_event, enabled) => {
    interactiveMode = Boolean(enabled);
    applyInteractionMode();
    return interactiveMode;
  });
  ipcMain.handle('overlay:toggle-visibility', () => {
    toggleVisibility();
    return Boolean(mainWindow && mainWindow.isVisible());
  });

  globalShortcut.register('CommandOrControl+Shift+I', () => {
    toggleInteractionMode();
  });
  globalShortcut.register('CommandOrControl+Shift+H', () => {
    toggleVisibility();
  });

  createWindow();
  createTray();

  app.on('second-instance', () => {
    if (!mainWindow) {
      return;
    }
    if (!mainWindow.isVisible()) {
      mainWindow.show();
    }
    mainWindow.focus();
    applyInteractionMode();
    refreshTrayMenu();
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (isQuitting && process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});
