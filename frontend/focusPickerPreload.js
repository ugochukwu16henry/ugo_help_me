const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('focusPickerAPI', {
  complete: (selection) => ipcRenderer.send('overlay:focus-picker-selected', selection),
  cancel: () => ipcRenderer.send('overlay:focus-picker-cancel')
});
