const statusEl = document.getElementById('status');
const answerEl = document.getElementById('answer');
const transcriptTextEl = document.getElementById('transcriptText');
const ocrTextEl = document.getElementById('ocrText');
const ocrStatusEl = document.getElementById('ocrStatus');
const hintEl = document.getElementById('hint');

const toggleInteractionBtn = document.getElementById('toggleInteractionBtn');
const toggleVisibilityBtn = document.getElementById('toggleVisibilityBtn');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const questionInput = document.getElementById('questionInput');
const askBtn = document.getElementById('askBtn');
const clearAnswerBtn = document.getElementById('clearAnswerBtn');
const uploadInput = document.getElementById('uploadInput');
const uploadBtn = document.getElementById('uploadBtn');
const buildRagBtn = document.getElementById('buildRagBtn');
const modeSelect = document.getElementById('modeSelect');
const monitorSelect = document.getElementById('monitorSelect');
const ratioInput = document.getElementById('ratioInput');
const leftInput = document.getElementById('leftInput');
const topInput = document.getElementById('topInput');
const widthInput = document.getElementById('widthInput');
const heightInput = document.getElementById('heightInput');
const applyFocusBtn = document.getElementById('applyFocusBtn');
const pickFocusBtn = document.getElementById('pickFocusBtn');
const docSummary = document.getElementById('docSummary');
const docList = document.getElementById('docList');
const refreshDocsBtn = document.getElementById('refreshDocsBtn');
const applyDocsBtn = document.getElementById('applyDocsBtn');
const deleteDocsBtn = document.getElementById('deleteDocsBtn');
const askFromOcrBtn = document.getElementById('askFromOcrBtn');

const wsUrl = 'ws://127.0.0.1:8765/ws/overlay';
const apiBase = 'http://127.0.0.1:8765';

function parseErrorText(text, fallback) {
  const raw = String(text || '').trim();
  if (!raw) {
    return fallback;
  }

  try {
    const json = JSON.parse(raw);
    if (typeof json.detail === 'string' && json.detail.trim()) {
      return json.detail.trim();
    }
    if (Array.isArray(json.detail) && json.detail.length > 0) {
      return String(json.detail[0]?.msg || fallback);
    }
  } catch {
    // not JSON, keep raw fallback below
  }

  return raw.length > 180 ? `${raw.slice(0, 180)}...` : raw;
}

function statusWithError(prefix, error) {
  const message = parseErrorText(error?.message || '', 'Unknown error');
  statusEl.textContent = `${prefix}: ${message}`;
}

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
    throw new Error(parseErrorText(text, `Request failed (${response.status})`));
  }

  return response.json();
}

async function uploadFiles(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file, file.name);
  }

  const response = await fetch(`${apiBase}/rag/upload`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(parseErrorText(text, `Upload failed (${response.status})`));
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

function renderDocList(available, selected) {
  const selectedSet = new Set(selected || []);
  docList.innerHTML = '';

  if (!available || available.length === 0) {
    docSummary.textContent = 'No documents found in backend/data/my_docs';
    return;
  }

  docSummary.textContent = `${selectedSet.size || available.length}/${available.length} selected`;

  for (const name of available) {
    const label = document.createElement('label');
    label.className = 'doc-item';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = name;
    checkbox.checked = selectedSet.size === 0 ? true : selectedSet.has(name);

    const text = document.createElement('span');
    text.textContent = name;

    label.appendChild(checkbox);
    label.appendChild(text);
    docList.appendChild(label);
  }
}

async function refreshDocuments() {
  const data = await apiRequest('/rag/documents');
  const available = Array.isArray(data.available) ? data.available : [];
  const selected = Array.isArray(data.selected) ? data.selected : [];
  renderDocList(available, selected);
}

async function refreshOcrStatus() {
  try {
    const status = await apiRequest('/screen/ocr/status');
    const running = Boolean(status.running);
    const ready = Boolean(status.engine_ready);
    const processed = Number(status.frames_processed || 0);
    const seen = Number(status.frames_seen || 0);
    const lastError = status.last_error ? `, error: ${status.last_error}` : '';
    ocrStatusEl.textContent = `OCR status: ${running ? 'running' : 'stopped'} • engine ${ready ? 'ready' : 'not ready'} • frames ${processed}/${seen}${lastError}`;

    const latestText = String(status.last_text || '').trim();
    if (latestText) {
      ocrTextEl.textContent = latestText;
    }
  } catch (error) {
    ocrStatusEl.textContent = `OCR status: unavailable (${parseErrorText(error?.message || '', 'error')})`;
  }
}

function getSelectedDocNames() {
  return Array.from(docList.querySelectorAll('input[type="checkbox"]:checked')).map((input) => input.value);
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
    } catch (error) {
      statusWithError('Failed to generate answer', error);
    }
  });

  clearAnswerBtn.addEventListener('click', () => {
    answerEl.textContent = '';
    statusEl.textContent = 'Answer cleared';
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
      const pendingFiles = Array.from(uploadInput.files || []);
      if (pendingFiles.length > 0) {
        const uploadResult = await uploadFiles(pendingFiles);
        uploadInput.value = '';
        const uploadedCount = Array.isArray(uploadResult.uploaded) ? uploadResult.uploaded.length : 0;
        statusEl.textContent = `Uploaded ${uploadedCount} file(s), building RAG...`;
      }

      const result = await apiRequest('/rag/build', 'POST');
      statusEl.textContent = `RAG built: ${result.indexed_chunks} chunks`;
      await refreshDocuments();
    } catch (error) {
      statusWithError('RAG build failed', error);
    }
  });

  uploadBtn.addEventListener('click', async () => {
    const files = Array.from(uploadInput.files || []);
    if (files.length === 0) {
      statusEl.textContent = 'Choose files first';
      return;
    }

    try {
      const result = await uploadFiles(files);
      uploadInput.value = '';
      const uploaded = Array.isArray(result.uploaded) ? result.uploaded : [];
      const rejected = Array.isArray(result.rejected) ? result.rejected : [];
      await refreshDocuments();
      statusEl.textContent = `Uploaded ${uploaded.length} file(s)${rejected.length ? `, rejected ${rejected.length}` : ''}`;
    } catch (error) {
      statusWithError('Upload failed', error);
    }
  });

  applyFocusBtn.addEventListener('click', async () => {
    try {
      await applyFocusFromInputs();
    } catch (error) {
      statusWithError('Failed to apply focus', error);
    }
  });

  pickFocusBtn.addEventListener('click', async () => {
    try {
      statusEl.textContent = 'Select region on screen...';
      const selected = await window.overlayAPI.pickFocusArea();
      if (!selected) {
        statusEl.textContent = 'Focus selection cancelled';
        return;
      }

      modeSelect.value = 'custom';
      monitorSelect.value = String(selected.monitorIndex || 1);
      leftInput.value = String(Math.max(0, Number(selected.left || 0)));
      topInput.value = String(Math.max(0, Number(selected.top || 0)));
      widthInput.value = String(Math.max(1, Number(selected.width || 1)));
      heightInput.value = String(Math.max(1, Number(selected.height || 1)));

      await applyFocusFromInputs();
      statusEl.textContent = 'Focus region selected and applied';
    } catch (error) {
      statusWithError('Failed to pick focus area', error);
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

    await refreshDocuments();
    await refreshOcrStatus();
  } catch {
    statusEl.textContent = 'Backend control API unavailable';
  }

  setInterval(() => {
    refreshOcrStatus();
  }, 2000);

  refreshDocsBtn.addEventListener('click', async () => {
    try {
      await refreshDocuments();
      statusEl.textContent = 'Document list refreshed';
    } catch (error) {
      statusWithError('Failed to refresh documents', error);
    }
  });

  applyDocsBtn.addEventListener('click', async () => {
    try {
      const selectedDocs = getSelectedDocNames();
      const result = await apiRequest('/rag/documents/select', 'POST', {
        selected_docs: selectedDocs
      });
      const available = Array.isArray(result.available) ? result.available : [];
      const selected = Array.isArray(result.selected) ? result.selected : [];
      renderDocList(available, selected);
      statusEl.textContent = `Applied docs: ${selected.length}`;
    } catch (error) {
      statusWithError('Failed to apply document selection', error);
    }
  });

  deleteDocsBtn.addEventListener('click', async () => {
    try {
      const selectedDocs = getSelectedDocNames();
      if (selectedDocs.length === 0) {
        statusEl.textContent = 'Select document(s) to delete';
        return;
      }

      const result = await apiRequest('/rag/documents/delete', 'POST', {
        selected_docs: selectedDocs
      });

      const available = Array.isArray(result.available) ? result.available : [];
      const selected = Array.isArray(result.selected) ? result.selected : [];
      const deleted = Array.isArray(result.deleted) ? result.deleted : [];

      renderDocList(available, selected);
      statusEl.textContent = `Deleted ${deleted.length} document(s)`;
    } catch (error) {
      statusWithError('Failed to delete documents', error);
    }
  });

  askFromOcrBtn.addEventListener('click', async () => {
    try {
      const result = await apiRequest('/screen/ocr/ask', 'POST');
      if (result.answer) {
        answerEl.textContent = result.answer;
      }
      statusEl.textContent = 'Generated answer from OCR';
    } catch (error) {
      statusWithError('Failed to answer from OCR', error);
    }
  });
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
        return;
      }

      if (payload.type === 'transcript') {
        transcriptTextEl.textContent = payload.message;
        if (payload.source === 'screen') {
          const cleaned = String(payload.message || '').replace(/^\[screen\]\s*/i, '').trim();
          if (cleaned) {
            ocrTextEl.textContent = cleaned;
          }
        }
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
