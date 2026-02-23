const statusEl = document.getElementById('status');
const answerEl = document.getElementById('answer');

const wsUrl = 'ws://127.0.0.1:8765/ws/overlay';

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
