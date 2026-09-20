import {$, api, connect, showError, BASE} from './common.js';
const params = new URLSearchParams(location.hash.slice(1));
let session;
try {
  session = params.get('session') && params.get('token') ? {session_id:params.get('session'), token:params.get('token')} : JSON.parse(sessionStorage.getItem('lantern-phone'));
  if (session) sessionStorage.setItem('lantern-phone', JSON.stringify(session));
  history.replaceState(null, '', `${BASE}/phone`); // Keep the pairing secret out of copied page URLs.
} catch { /* Invalid storage is handled below. */ }
let channel, connected = false, active = false, snapshot, audioContext, source, utterance, playbackVersion = 0;
let fetchController, recorder, recognition, micStream, recording = false, busy = false, recordTimer, speechTimer, captureVersion = 0;
let captureMode = 'checkin';
const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
function send(message) {
  try { channel.send(message); return true; }
  catch (error) { showError(error.message); return false; }
}
function update() {
  $('start').disabled = !connected;
  $('start').hidden = active;
  $('controls').hidden = !active;
  $('record').disabled = !connected || !snapshot?.checkin || busy || (recording && captureMode !== 'checkin');
  $('send-reply').disabled = !connected || !snapshot?.checkin || busy || recording;
  $('record').textContent = recording && captureMode === 'checkin' ? 'Finish and send reply' : 'Reply to check-in';
  $('robot-record').disabled = !connected || !active || busy || (recording && captureMode !== 'robot');
  $('robot-record').textContent = recording && captureMode === 'robot' ? 'Finish and send request' : 'Speak a robot request';
  for (const id of ['robot-send', 'robot-yes', 'robot-no']) $(id).disabled = !connected || !active || busy || recording;
}
function playback(state, id = utterance?.utterance_id) {
  if (id && connected) send({type:'playback', utterance_id:id, state});
}
function autoListen() {
  if (!active || recording || busy || !snapshot?.checkin) return;
  void startRecording();
}
function stopSpeaking(report = true) {
  playbackVersion++;
  clearTimeout(speechTimer);
  fetchController?.abort(); fetchController = null;
  if (source) { source.onended = null; try { source.stop(); } catch {} source = null; }
  window.speechSynthesis?.cancel();
  if (utterance && report) playback('interrupted');
  utterance = null; $('retry').hidden = true;
}
async function play(payload) {
  stopSpeaking(); utterance = payload;
  const version = playbackVersion;
  $('spoken').textContent = payload.text; $('activity').textContent = 'Preparing a reply…';
  try {
    if (snapshot.capabilities.tts === 'elevenlabs') {
      fetchController = new AbortController();
      const response = await api(`/api/sessions/${session.session_id}/speech/${payload.utterance_id}`, session.token, {method:'POST', signal:fetchController.signal});
      const buffer = await audioContext.decodeAudioData(await response.arrayBuffer());
      if (version !== playbackVersion || !active) return;
      if (audioContext.state !== 'running') throw new Error('Tap “play message” to enable phone audio.');
      source = audioContext.createBufferSource(); source.buffer = buffer; source.connect(audioContext.destination);
      source.onended = () => {
        if (version !== playbackVersion) return;
        playback('delivered', payload.utterance_id); source = null; utterance = null;
        if (payload.origin === 'checkin') autoListen();
      };
      source.start(); playback('speaking'); $('activity').textContent = 'Lantern is speaking';
    } else {
      if (!window.speechSynthesis) throw new Error('This browser has no speech playback. Try another browser.');
      const speech = new SpeechSynthesisUtterance(payload.text); speech.rate = 0.9; speech.lang = 'en-US';
      speech.onstart = () => {
        clearTimeout(speechTimer);
        if (version === playbackVersion) { playback('speaking', payload.utterance_id); $('activity').textContent = 'Lantern is speaking'; }
      };
      speech.onend = () => {
        clearTimeout(speechTimer);
        if (version !== playbackVersion) return;
        playback('delivered', payload.utterance_id); utterance = null;
        if (payload.origin === 'checkin') autoListen();
      };
      speech.onerror = () => {
        clearTimeout(speechTimer);
        if (version !== playbackVersion) return;
        playback('failed', payload.utterance_id); $('retry').hidden = false;
        showError('Audio did not play. Tap “play message” to retry.');
      };
      window.speechSynthesis.speak(speech);
      speechTimer = setTimeout(() => {
        if (version !== playbackVersion) return;
        // Some mobile browsers neither play nor dispatch an error when activation expires.
        stopSpeaking(false); utterance = payload; playback('failed', payload.utterance_id);
        $('retry').hidden = false; showError('Tap “play message” to enable audio on this phone.');
      }, 10000);
    }
  } catch (error) {
    if (version !== playbackVersion) return;
    playback('failed', payload.utterance_id); $('retry').hidden = false; showError(error.message);
  }
}
function releaseMic() {
  micStream?.getTracks().forEach(track => track.stop()); micStream = null;
  clearTimeout(recordTimer);
}
function cancelCapture() {
  if (captureMode === 'robot' && (recording || busy)) $('robot-request-status').textContent = 'Recording cancelled. Tap to try again.';
  captureVersion++;
  if (recorder?.state === 'recording') { recorder.onstop = null; recorder.stop(); }
  recognition?.abort(); recognition = null; releaseMic(); recording = false; busy = false;
}
function submitTranscript(text, checkinId, turnId, mode = 'checkin') {
  if (!text.trim()) { showError('No words were recognized. Please try again or type a reply.'); return; }
  if (!connected || !active || (mode === 'checkin' && (!checkinId || checkinId !== snapshot?.checkin?.checkin_id))) {
    showError('The session changed before your reply could be sent. Please try again.'); return;
  }
  if (!send({type:'transcript', text:text.slice(0, 2000), turn_id:turnId, checkin_id:checkinId})) {
    if (mode === 'robot') $('robot-request-status').textContent = 'Request not sent. Wait for the phone to reconnect.';
    return;
  }
  if (mode === 'robot') {
    $('robot-transcript').textContent = `You said: “${text.trim()}”`;
    $('robot-transcript').hidden = false;
    $('robot-request-status').textContent = 'Request sent. Watch robot activity for confirmation.';
  } else $('activity').textContent = 'Reply sent';
}
async function startRecording(mode = 'checkin') {
  if (!active || !connected || busy || recording || (mode === 'checkin' && !snapshot?.checkin)) return;
  captureMode = mode;
  showError(); stopSpeaking();
  if (!window.isSecureContext) { showError('Microphone access needs HTTPS. Open the secure pairing link.'); return; }
  const checkinId = mode === 'robot' ? '' : snapshot.checkin.checkin_id, turnId = crypto.randomUUID(), version = ++captureVersion;
  if (snapshot.capabilities.stt === 'deepgram') {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      showError('Audio recording is unavailable. Type a reply instead.'); return;
    }
    try {
      busy = true; update();
      const stream = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true, noiseSuppression:true, autoGainControl:true}});
      if (version !== captureVersion || !active) { stream.getTracks().forEach(t => t.stop()); return; }
      micStream = stream;
      const mimeType = ['audio/webm;codecs=opus','audio/mp4','audio/ogg;codecs=opus'].find(type => MediaRecorder.isTypeSupported(type));
      if (!mimeType) throw new Error('No supported recording format. Type a reply instead.');
      recorder = new MediaRecorder(stream, {mimeType});
      const chunks = []; recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
      recorder.onerror = () => { cancelCapture(); showError('Recording failed. Please try again.'); update(); };
      recorder.onstop = async () => {
        releaseMic(); recording = false; busy = true; update();
        $(mode === 'robot' ? 'robot-request-status' : 'activity').textContent = 'Transcribing…';
        try {
          const response = await api(`/api/sessions/${session.session_id}/transcribe`, session.token, {
            method:'POST', headers:{'Content-Type':mimeType}, body:new Blob(chunks, {type:mimeType}),
          });
          const data = await response.json();
          if (version === captureVersion) submitTranscript(data.text, checkinId, turnId, mode);
        } catch (error) { if (version === captureVersion) showError(error.message); }
        finally { if (version === captureVersion) { busy = false; update(); } }
      };
      recorder.start(); busy = false; recording = true;
    } catch (error) { releaseMic(); busy = false; showError(error.message); }
  } else {
    if (!Recognition) { showError('Browser speech recognition is unavailable. Type a reply, or configure Deepgram on the server.'); return; }
    recognition = new Recognition(); recognition.lang = 'en-US'; recognition.continuous = true; recognition.interimResults = true;
    let text = '';
    recognition.onresult = (event) => {
      text = Array.from(event.results).filter(result => result.isFinal).map(result => result[0].transcript).join(' ');
    };
    recognition.onerror = (event) => { if (event.error !== 'aborted') showError(`Microphone recognition: ${event.error}. You can type a reply instead.`); };
    recognition.onend = () => {
      if (version !== captureVersion) return;
      clearTimeout(recordTimer);
      recording = false; busy = false; recognition = null;
      submitTranscript(text, checkinId, turnId, mode); update();
    };
    try { recognition.start(); recording = true; } catch (error) { showError(error.message); }
  }
  if (recording) {
    $(mode === 'robot' ? 'robot-request-status' : 'activity').textContent = mode === 'robot' ? 'Listening… tap again to send your request.' : 'Listening. Take your time.';
    recordTimer = setTimeout(finishRecording, mode === 'robot' ? 10000 : 5000);
  }
  update();
}
function finishRecording() {
  clearTimeout(recordTimer);
  if (recorder?.state === 'recording') recorder.stop();
  else if (recognition) { busy = true; recognition.stop(); }
  update();
}
function pause() {
  active = false; cancelCapture(); stopSpeaking();
  if (connected) send({type:'paused'});
  $('activity').textContent = 'Paused. Tap Start to continue.'; update();
}
$('start').onclick = async () => {
  showError();
  try {
    // Resume in the tap handler: mobile browsers require a user gesture for audio.
    audioContext ??= new (window.AudioContext || window.webkitAudioContext)();
    const resumed = audioContext.resume();
    if (snapshot?.capabilities.tts === 'browser' && window.speechSynthesis) {
      window.speechSynthesis.speak(new SpeechSynthesisUtterance('Lantern is ready.'));
    }
    await resumed; active = true; send({type:'ready'});
    update();
  } catch (error) { showError(`Audio could not start: ${error.message}`); }
};
$('record').onclick = () => recording ? finishRecording() : startRecording();
$('robot-record').onclick = () => recording ? finishRecording() : startRecording('robot');
function sendRobotRequest(text) {
  if (!active || !connected || busy || recording) return;
  captureMode = 'robot';
  showError(); stopSpeaking();
  submitTranscript(text, '', crypto.randomUUID(), 'robot');
}
$('robot-form').onsubmit = event => {
  event.preventDefault(); sendRobotRequest($('robot-input').value); $('robot-input').value = '';
};
$('robot-yes').onclick = () => sendRobotRequest('yes');
$('robot-no').onclick = () => sendRobotRequest('no');
$('stop').onclick = () => { stopSpeaking(); $('activity').textContent = 'Speech stopped'; };
$('pause').onclick = pause;
$('retry').onclick = async () => {
  const retry = utterance;
  if (!retry) return;
  showError(); await audioContext.resume();
  // play() cancels the previous attempt, without reporting that failed attempt twice.
  utterance = null; play(retry);
};
$('reply-form').onsubmit = (event) => {
  event.preventDefault(); showError(); stopSpeaking();
  submitTranscript($('reply').value, snapshot?.checkin?.checkin_id, crypto.randomUUID()); $('reply').value = '';
};
document.addEventListener('visibilitychange', () => { if (document.hidden && active) pause(); });
if (!session?.session_id || !session?.token) {
  $('start').disabled = true; showError('Open the private phone link from the caregiver dashboard to pair Lantern.');
} else {
  channel = connect(session, 'phone', message => {
    if (message.type === 'snapshot') {
      snapshot = message;
      $('mode').textContent = `${message.capabilities.stt === 'deepgram' ? 'Deepgram recording' : 'Browser recognition (where supported)'} · ${message.capabilities.tts === 'elevenlabs' ? 'ElevenLabs voice' : 'Phone voice'} · Check-ins listen after playback. Robot requests listen only when you tap to speak.`;
      update();
    } else if (message.type === 'say') {
      if (active) { cancelCapture(); play(message.payload); }
      else playback('failed', message.payload.utterance_id);
    } else if (message.type === 'error') {
      showError(message.message);
      if (captureMode === 'robot') $('robot-request-status').textContent = message.message;
    }
  }, isConnected => {
    connected = isConnected; $('connection').textContent = connected ? '● Connected' : '○ Reconnecting';
    if (!connected) { active = false; cancelCapture(); stopSpeaking(false); $('activity').textContent = 'Connection lost. Tap Start after reconnecting.'; }
    update();
  });
}

// The mounted portal already exposes the robot's existing event stream.
// These are observed states, not optimistic claims that a request moved the dog.
if (BASE && session?.session_id && session?.token) {
  let robotSocket, reconnect;
  const showRobotState = payload => {
    const labels = {IDLE:'Ready', WALK:'Walking together', FOLLOW:'Following', CONFIRM_HOME:'Confirm return home', GUIDE_HOME:'Returning home'};
    $('robot-state').textContent = labels[payload.state] || `Robot mode: ${payload.state}`;
    $('robot-confirm').hidden = payload.state !== 'CONFIRM_HOME';
    $('robot-prompt').textContent = payload.state === 'CONFIRM_HOME' ? 'Would you still like to go home?' : '';
  };
  const openRobotStream = () => {
    const url = new URL('/ws', location.href); url.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    robotSocket = new WebSocket(url);
    robotSocket.onmessage = event => {
      let message; try { message = JSON.parse(event.data); } catch { return; }
      const payload = message.payload || {};
      if (message.type === 'snapshot' && payload.agent_state) showRobotState(payload.agent_state);
      else if (message.type === 'agent_state') showRobotState(payload);
      else if (message.type === 'say' && message.source === 'orchestrator' && payload.origin === 'policy') {
        $('robot-prompt').textContent = payload.text;
      }
      else if (message.type === 'robot_status') {
        const labels = {accepted:'Request accepted by the robot bridge', executing:'Robot is carrying out the request', done:'Robot action completed', failed:'Robot action failed', yielded:'Robot yielded to a person'};
        $('robot-state').textContent = labels[payload.state] || payload.state;
        if (payload.state === 'failed') $('robot-prompt').textContent = payload.detail || 'Please check the robot before trying again.';
      }
    };
    robotSocket.onclose = () => {
      $('robot-state').textContent = 'Robot updates disconnected. Reconnecting…';
      $('robot-confirm').hidden = true;
      reconnect = setTimeout(openRobotStream, 2000);
    };
  };
  openRobotStream();
  window.addEventListener('pagehide', () => { clearTimeout(reconnect); robotSocket.onclose = null; robotSocket.close(); });
} else $('robot-state').textContent = 'Open the paired phone link from the portal to see robot activity.';
