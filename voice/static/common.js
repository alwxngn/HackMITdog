export const $ = (id) => document.getElementById(id);
export const BASE = location.pathname.startsWith('/voice/') ? '/voice' : '';
export function showError(message = '') { $('error').textContent = message; $('error').hidden = !message; }
export async function api(path, token, options = {}) {
  const response = await fetch(`${BASE}${path}`, {...options, headers: {
    ...(token ? {Authorization: `Bearer ${token}`} : {}), ...options.headers,
  }});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}). Check your input.`);
  }
  return response;
}
export function connect(session, role, onMessage, onConnection) {
  let socket, timer, reconnect, closed = false;
  const open = () => {
    socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}${BASE}/ws/${session.session_id}/${role}`);
    socket.onopen = () => {
      socket.send(JSON.stringify({token: session.token}));
      timer = setInterval(() => { if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({type: 'ping'})); }, 15000);
    };
    socket.onmessage = ({data}) => {
      const message = JSON.parse(data);
      if (message.type === 'snapshot') onConnection(true);
      onMessage(message);
    };
    socket.onclose = (event) => {
      clearInterval(timer);
      onConnection(false);
      if (event.code === 4403 || event.code === 4409 || event.code === 1008) {
        showError(event.code === 4409 ? 'This session already has a phone connected. Close it before pairing another.' : 'Session unavailable. Create a new session from the caregiver page.');
        return;
      }
      if (!closed) reconnect = setTimeout(open, 2000);
    };
    socket.onerror = () => { /* onclose handles reconnection. */ };
  };
  open();
  return {
    send: (message) => {
      if (socket.readyState !== WebSocket.OPEN) throw new Error('Disconnected. Wait for the connection to return.');
      socket.send(JSON.stringify(message));
    },
    close: () => { closed = true; clearTimeout(reconnect); clearInterval(timer); socket.close(); },
  };
}
