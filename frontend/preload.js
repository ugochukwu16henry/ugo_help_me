const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('overlayAPI', {
  version: '0.1.0',
  getInteractionMode: () => ipcRenderer.invoke('overlay:get-interaction'),
  setInteractionMode: (enabled) => ipcRenderer.invoke('overlay:set-interaction', enabled),
  toggleVisibility: () => ipcRenderer.invoke('overlay:toggle-visibility'),
  pickFocusArea: () => ipcRenderer.invoke('overlay:pick-focus'),
  onInteractionChanged: (handler) => {
    ipcRenderer.on('interaction-changed', (_event, enabled) => handler(Boolean(enabled)));
  }
});
