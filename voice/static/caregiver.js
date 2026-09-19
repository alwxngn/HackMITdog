import {$, api, connect, showError} from './common.js';
let session, channel, online = false, sending = false, state;
try { session = JSON.parse(sessionStorage.getItem('lantern-caregiver')); } catch { /* fresh session */ }
function controls() {
  $('send').disabled = !online || !state?.phone_ready || sending || ['pending', 'speaking'].includes(state?.utterance?.state);
}
function render(message) {
  if (message.type !== 'snapshot') return;
  state = message;
  $('connection').textContent = message.phone_ready ? '● Phone ready' : message.phone_online ? '○ Tap Start on the phone' : '○ Phone offline';
  $('mode').textContent = `${message.capabilities.tts === 'browser' ? 'Phone voice' : 'ElevenLabs voice'} · Scripted conversation`;
  $('checkin-title').textContent = `Say hello to ${message.profile.patient}`;
  const statuses = {sent: 'Sent · waiting for phone playback', speaking: 'Lantern is speaking…', delivered: 'Delivered · waiting for a reply', responded: 'Reply received', interrupted: 'Message interrupted on the phone', failed: 'Audio did not play. Check the phone.', unavailable: 'Phone disconnected before delivery was confirmed.'};
  $('delivery').textContent = message.checkin ? statuses[message.checkin.status] || message.checkin.status : 'Your check-in will start a conversation.';
  $('attention').hidden = !message.checkin?.needs_attention;
  const events = message.events.filter(e => ['say', 'transcript'].includes(e.type));
  if (events.length) {
    $('timeline').replaceChildren(...events.map(e => {
      const entry = document.createElement('div'); entry.className = 'entry';
      const meta = document.createElement('div'); meta.className = 'entry-meta';
      meta.textContent = `${e.type === 'say' ? 'Lantern · prepared response' : message.profile.patient + ' · reply'} · ${new Date(e.ts * 1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}`;
      const text = document.createElement('p'); text.textContent = e.payload.text;
      entry.append(meta, text); return entry;
    }));
  }
  controls();
}
function start() {
  $('setup').hidden = true; $('workspace').hidden = false;
  const link = new URL('/phone', location.origin);
  link.hash = new URLSearchParams({session: session.session_id, token: session.phone_token});
  $('phone-link').value = link.href; $('open-phone').href = link.href;
  $('local-warning').hidden = !['localhost', '127.0.0.1'].includes(location.hostname);
  channel = connect({session_id: session.session_id, token: session.caregiver_token}, 'caregiver', render, connected => {
    online = connected;
    if (!connected) $('connection').textContent = 'Reconnecting…';
    controls();
  });
}
$('create-form').onsubmit = async (event) => {
  event.preventDefault(); showError();
  const button = event.submitter; button.disabled = true;
  try {
    session = await (await api('/api/sessions', null, {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({patient:$('patient').value, caregiver:$('caregiver').value})})).json();
    sessionStorage.setItem('lantern-caregiver', JSON.stringify(session)); start();
  } catch (error) { showError(error.message); } finally { button.disabled = false; }
};
$('checkin-form').onsubmit = async (event) => {
  event.preventDefault(); showError(); sending = true; controls();
  try {
    await api(`/api/sessions/${session.session_id}/checkins`, session.caregiver_token, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text:$('message').value})});
    $('message').value = '';
  } catch (error) { showError(error.message); } finally { sending = false; controls(); }
};
$('copy').onclick = async () => {
  try { await navigator.clipboard.writeText($('phone-link').value); $('copy').textContent = 'Copied'; }
  catch { $('phone-link').select(); showError('Select and copy the pairing link above.'); }
};
$('new-session').onclick = () => { channel?.close(); sessionStorage.removeItem('lantern-caregiver'); location.reload(); };
if (session?.session_id && session?.caregiver_token && session?.phone_token) start();
