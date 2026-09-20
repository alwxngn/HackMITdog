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
const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
function send(message) { try { channel.send(message); } catch (error) { showError(error.message); } }
function update() {
  $('start').disabled = !connected;
  $('start').hidden = active;
  $('controls').hidden = !active;
  $('record').disabled = !connected || busy;
  $('send-reply').disabled = !connected || !snapshot?.checkin || busy || recording;
  $('record').textContent = recording ? 'Finish and send reply' : 'Speak to Lantern';
}
function playback(state, id = utterance?.utterance_id) {
  if (id && connected) send({type:'playback', utterance_id:id, state});
}
function autoListen() {
  if (!active || recording || busy) return;
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
  captureVersion++;
  if (recorder?.state === 'recording') { recorder.onstop = null; recorder.stop(); }
  recognition?.abort(); recognition = null; releaseMic(); recording = false; busy = false;
}
function submitTranscript(text, checkinId, turnId) {
  if (!text.trim()) { showError('No words were recognized. Please try again or type a reply.'); return; }
  if (!connected || !active || (snapshot?.checkin && checkinId && checkinId !== snapshot.checkin.checkin_id)) {
    showError('The session changed before your reply could be sent. Please try again.'); return;
  }
  send({type:'transcript', text:text.slice(0, 2000), turn_id:turnId, checkin_id:checkinId});
  $('activity').textContent = 'Reply sent';
}
async function startRecording() {
  showError(); stopSpeaking();
  if (!window.isSecureContext) { showError('Microphone access needs HTTPS. Open the secure pairing link.'); return; }
  const checkinId = snapshot?.checkin?.checkin_id || '', turnId = crypto.randomUUID(), version = ++captureVersion;
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
        releaseMic(); recording = false; busy = true; update(); $('activity').textContent = 'Listening to your reply…';
        try {
          const response = await api(`/api/sessions/${session.session_id}/transcribe`, session.token, {
            method:'POST', headers:{'Content-Type':mimeType}, body:new Blob(chunks, {type:mimeType}),
          });
          const data = await response.json();
          if (version === captureVersion) submitTranscript(data.text, checkinId, turnId);
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
      clearTimeout(recordTimer);
      if (version !== captureVersion) return;
      recording = false; busy = false; recognition = null;
      submitTranscript(text, checkinId, turnId); update();
    };
    try { recognition.start(); recording = true; } catch (error) { showError(error.message); }
  }
  if (recording) {
    $('activity').textContent = 'Listening. Take your time.';
    recordTimer = setTimeout(finishRecording, 5000);
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
      $('mode').textContent = `${message.capabilities.stt === 'deepgram' ? 'Deepgram recording' : 'Browser recognition (where supported)'} · ${message.capabilities.tts === 'elevenlabs' ? 'ElevenLabs voice' : 'Phone voice'} · Scripted replies. Audio is captured only when you tap Talk.`;
      update();
    } else if (message.type === 'say') {
      if (active) { cancelCapture(); play(message.payload); }
      else playback('failed', message.payload.utterance_id);
    } else if (message.type === 'error') showError(message.message);
  }, isConnected => {
    connected = isConnected; $('connection').textContent = connected ? '● Connected' : '○ Reconnecting';
    if (!connected) { active = false; cancelCapture(); stopSpeaking(false); $('activity').textContent = 'Connection lost. Tap Start after reconnecting.'; }
    update();
  });
}
