const statusEl = document.getElementById('status');
const answerEl = document.getElementById('answer');
const hintEl = document.getElementById('hint');

const toggleInteractionBtn = document.getElementById('toggleInteractionBtn');
const toggleVisibilityBtn = document.getElementById('toggleVisibilityBtn');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const questionInput = document.getElementById('questionInput');
const askBtn = document.getElementById('askBtn');
const buildRagBtn = document.getElementById('buildRagBtn');
const modeSelect = document.getElementById('modeSelect');
const monitorSelect = document.getElementById('monitorSelect');
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
    ? 'Controls unlocked. Ctrl+Shift+H hide/show overlay.'
    : 'Ctrl+Shift+H hide/show overlay • Ctrl+Shift+I unlock controls.';
}

async function applyFocusFromInputs() {
  const mode = modeSelect.value;
  const monitor = Number(monitorSelect.value || 1);

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

function monitorLabel(monitor) {
  const index = monitor.index ?? 1;
  const width = monitor.width ?? 0;
  const height = monitor.height ?? 0;
  const left = monitor.left ?? 0;
  const top = monitor.top ?? 0;
  return `#${index} ${width}x${height} @ (${left},${top})`;
}

async function populateMonitors(selectedIndex = 1) {
  const data = await apiRequest('/ingestion/screen/monitors');
  const monitors = Array.isArray(data.monitors) ? data.monitors : [];

  monitorSelect.innerHTML = '';

  if (monitors.length === 0) {
    const fallback = document.createElement('option');
    fallback.value = '1';
    fallback.textContent = '#1 (default)';
    monitorSelect.appendChild(fallback);
    monitorSelect.value = '1';
    return;
  }

  for (const monitor of monitors) {
    const option = document.createElement('option');
    option.value = String(monitor.index);
    option.textContent = monitorLabel(monitor);
    monitorSelect.appendChild(option);
  }

  const hasTarget = monitors.some((monitor) => monitor.index === selectedIndex);
  monitorSelect.value = String(hasTarget ? selectedIndex : monitors[0].index);
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

  toggleVisibilityBtn.addEventListener('click', async () => {
    try {
      await window.overlayAPI.toggleVisibility();
    } catch {
      statusEl.textContent = 'Failed to toggle overlay visibility';
    }
  });

  startBtn.addEventListener('click', async () => {
    await apiRequest('/ingestion/start', 'POST');
    statusEl.textContent = 'Ingestion started';
  });

  stopBtn.addEventListener('click', async () => {
    await apiRequest('/ingestion/stop', 'POST');
    statusEl.textContent = 'Ingestion stopped';
  });

  askBtn.addEventListener('click', async () => {
    const question = (questionInput.value || '').trim();
    if (!question) {
      statusEl.textContent = 'Enter a question first';
      return;
    }

    try {
      const result = await apiRequest('/brain/ask', 'POST', { question });
      if (result.answer) {
        answerEl.textContent = result.answer;
      }
      statusEl.textContent = 'Answer generated';
    } catch {
      statusEl.textContent = 'Failed to generate answer';
    }
  });

  questionInput.addEventListener('keydown', async (event) => {
    if (event.key !== 'Enter') {
      return;
    }
    event.preventDefault();
    askBtn.click();
  });

  buildRagBtn.addEventListener('click', async () => {
    try {
      const result = await apiRequest('/rag/build', 'POST');
      statusEl.textContent = `RAG built: ${result.indexed_chunks} chunks`;
    } catch {
      statusEl.textContent = 'RAG build failed';
    }
  });

  applyFocusBtn.addEventListener('click', async () => {
    try {
      await applyFocusFromInputs();
    } catch {
      statusEl.textContent = 'Failed to apply focus';
    }
  });

  try {
    await populateMonitors(1);

    const focus = await apiRequest('/ingestion/screen/focus');
    modeSelect.value = focus.mode || 'center';
    await populateMonitors(Number(focus.monitor_index || 1));
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
