const statusEl = document.getElementById('status');
const answerEl = document.getElementById('answer');
const hintEl = document.getElementById('hint');

const toggleInteractionBtn = document.getElementById('toggleInteractionBtn');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const modeSelect = document.getElementById('modeSelect');
const monitorInput = document.getElementById('monitorInput');
const ratioInput = document.getElementById('ratioInput');
const leftInput = document.getElementById('leftInput');
const topInput = document.getElementById('topInput');
const widthInput = document.getElementById('widthInput');
const heightInput = document.getElementById('heightInput');
const applyFocusBtn = document.getElementById('applyFocusBtn');

const wsUrl = 'ws://127.0.0.1:8765/ws/overlay';
const apiBase = 'http://127.0.0.1:8765';

async function apiRequest(path, method = 'GET', body = null) {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json'
    }
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${apiBase}${path}`, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return response.json();
}

function renderInteractionMode(enabled) {
  document.body.classList.toggle('interactive', enabled);
  toggleInteractionBtn.textContent = enabled ? 'Lock' : 'Unlock';
  hintEl.textContent = enabled
    ? 'Controls unlocked. Click Lock when done.'
    : 'Press Ctrl+Shift+I to unlock controls.';
}

async function applyFocusFromInputs() {
  const mode = modeSelect.value;
  const monitor = Number(monitorInput.value || 1);

  const payload = {
    mode,
    monitor_index: monitor
  };

  if (mode === 'center') {
    payload.ratio = Number(ratioInput.value || 0.6);
  }

  if (mode === 'custom') {
    payload.left = Number(leftInput.value || 0);
    payload.top = Number(topInput.value || 0);
    payload.width = Number(widthInput.value || 1);
    payload.height = Number(heightInput.value || 1);
  }

  const result = await apiRequest('/ingestion/screen/focus', 'POST', payload);
  statusEl.textContent = `Focus updated: ${result.focus.mode}`;
}

async function bootstrapControls() {
  const initialMode = await window.overlayAPI.getInteractionMode();
  renderInteractionMode(Boolean(initialMode));

  window.overlayAPI.onInteractionChanged((enabled) => {
    renderInteractionMode(enabled);
  });

  toggleInteractionBtn.addEventListener('click', async () => {
    const current = await window.overlayAPI.getInteractionMode();
    await window.overlayAPI.setInteractionMode(!current);
  });

  startBtn.addEventListener('click', async () => {
    await apiRequest('/ingestion/start', 'POST');
    statusEl.textContent = 'Ingestion started';
  });

  stopBtn.addEventListener('click', async () => {
    await apiRequest('/ingestion/stop', 'POST');
    statusEl.textContent = 'Ingestion stopped';
  });

  applyFocusBtn.addEventListener('click', async () => {
    try {
      await applyFocusFromInputs();
    } catch {
      statusEl.textContent = 'Failed to apply focus';
    }
  });

  try {
    const focus = await apiRequest('/ingestion/screen/focus');
    modeSelect.value = focus.mode || 'center';
    monitorInput.value = String(focus.monitor_index || 1);
    if (typeof focus.ratio === 'number') {
      ratioInput.value = String(focus.ratio);
    }
    if (focus.custom_region) {
      leftInput.value = String(focus.custom_region.left);
      topInput.value = String(focus.custom_region.top);
      widthInput.value = String(focus.custom_region.width);
      heightInput.value = String(focus.custom_region.height);
    }
  } catch {
    statusEl.textContent = 'Backend control API unavailable';
  }
}

function connect() {
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    statusEl.textContent = 'Connected: overlay stream online';
  };

  ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === 'status') {
        statusEl.textContent = payload.message;
        return;
      }

      if (payload.type === 'answer') {
        answerEl.textContent = payload.message;
      }
    } catch {
      statusEl.textContent = 'Received malformed backend message';
    }
  };

  ws.onclose = () => {
    statusEl.textContent = 'Backend disconnected. Retrying...';
    setTimeout(connect, 1500);
  };

  ws.onerror = () => {
    statusEl.textContent = 'Connection error. Retrying...';
  };
}

connect();
bootstrapControls();
