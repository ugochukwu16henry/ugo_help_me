const { app, BrowserWindow, globalShortcut, ipcMain, Menu, Tray, nativeImage, screen } = require('electron');
const path = require('path');

let mainWindow;
let pickerWindow = null;
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
  const primaryDisplay = screen.getPrimaryDisplay();
  const { x, y, width, height } = primaryDisplay.bounds;

  mainWindow = new BrowserWindow({
    x,
    y,
    width,
    height,
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

function allDisplaysBounds(displays) {
  const left = Math.min(...displays.map((d) => d.bounds.x));
  const top = Math.min(...displays.map((d) => d.bounds.y));
  const right = Math.max(...displays.map((d) => d.bounds.x + d.bounds.width));
  const bottom = Math.max(...displays.map((d) => d.bounds.y + d.bounds.height));
  return {
    x: left,
    y: top,
    width: right - left,
    height: bottom - top
  };
}

function displayIndex(displays, displayId) {
  const index = displays.findIndex((display) => display.id === displayId);
  return index >= 0 ? index + 1 : 1;
}

function openFocusPicker() {
  return new Promise((resolve) => {
    if (pickerWindow && !pickerWindow.isDestroyed()) {
      pickerWindow.close();
    }

    const displays = screen.getAllDisplays();
    const virtualBounds = allDisplaysBounds(displays);

    pickerWindow = new BrowserWindow({
      x: virtualBounds.x,
      y: virtualBounds.y,
      width: virtualBounds.width,
      height: virtualBounds.height,
      frame: false,
      transparent: true,
      alwaysOnTop: true,
      skipTaskbar: true,
      movable: false,
      resizable: false,
      fullscreenable: false,
      webPreferences: {
        preload: path.join(__dirname, 'focusPickerPreload.js'),
        contextIsolation: true,
        nodeIntegration: false
      }
    });

    pickerWindow.setAlwaysOnTop(true, 'screen-saver');
    pickerWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    pickerWindow.loadFile(path.join(__dirname, 'renderer', 'focus-picker.html'));

    const closePicker = (result) => {
      if (pickerWindow && !pickerWindow.isDestroyed()) {
        pickerWindow.close();
      }
      pickerWindow = null;
      resolve(result);
    };

    ipcMain.once('overlay:focus-picker-cancel', () => closePicker(null));
    ipcMain.once('overlay:focus-picker-selected', (_event, payload) => {
      const left = Number(payload?.left || 0);
      const top = Number(payload?.top || 0);
      const width = Number(payload?.width || 0);
      const height = Number(payload?.height || 0);

      if (width < 5 || height < 5) {
        closePicker(null);
        return;
      }

      const display = screen.getDisplayNearestPoint({ x: left + 1, y: top + 1 });
      const monitorIndex = displayIndex(displays, display.id);
      const relativeLeft = Math.max(0, left - display.bounds.x);
      const relativeTop = Math.max(0, top - display.bounds.y);

      closePicker({
        monitorIndex,
        left: relativeLeft,
        top: relativeTop,
        width: Math.min(width, display.bounds.width - relativeLeft),
        height: Math.min(height, display.bounds.height - relativeTop)
      });
    });

    pickerWindow.on('closed', () => {
      pickerWindow = null;
      resolve(null);
    });
  });
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
  ipcMain.handle('overlay:pick-focus', async () => {
    const wasVisible = Boolean(mainWindow && mainWindow.isVisible());
    if (mainWindow && wasVisible) {
      mainWindow.hide();
    }
    const result = await openFocusPicker();
    if (mainWindow && wasVisible) {
      mainWindow.show();
      applyInteractionMode();
      refreshTrayMenu();
    }
    return result;
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
