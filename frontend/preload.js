const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('overlayAPI', {
  version: '0.1.0'
});
