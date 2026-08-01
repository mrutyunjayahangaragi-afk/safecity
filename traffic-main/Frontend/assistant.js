// AI Personal Safety Assistant - Frontend Integration

let assistantSessionId = null;
let assistantPingInterval = null;
let isVoiceEnabled = true;
let synth = window.speechSynthesis;

const assistantHtml = `
<div id="ai-assistant-widget">
  <div class="ai-header" id="ai-header-drag">
    <div class="ai-header-left">
      <div class="ai-avatar">🤖</div>
      <div>
        <div class="ai-title">SafeRoute AI</div>
        <div class="ai-status">Monitoring Journey</div>
      </div>
    </div>
    <div class="ai-controls">
      <button class="ai-btn" onclick="toggleVoice()" id="ai-voice-btn" title="Toggle Voice">🔊</button>
      <button class="ai-btn" onclick="toggleAssistantBody()" title="Minimize">▼</button>
    </div>
  </div>
  <div class="ai-body" id="ai-body">
    <div class="ai-message">Hello. I am your Personal Safety Assistant. I will continuously monitor your trip.</div>
  </div>
</div>

<div id="ai-checkin-modal">
  <div class="checkin-card">
    <div class="checkin-title">Are you safe?</div>
    <div class="checkin-desc">We detected an unusual situation. Please confirm your status.</div>
    <div class="checkin-buttons">
      <button class="btn-safe" onclick="respondCheckin('safe')">✅ I'm Safe</button>
      <button class="btn-help" onclick="respondCheckin('need_help')">⚠️ Need Help</button>
      <button class="btn-sos" onclick="respondCheckin('emergency')">🚨 Emergency (SOS)</button>
    </div>
  </div>
</div>
`;

function injectAssistantUI() {
    const div = document.createElement('div');
    div.innerHTML = assistantHtml;
    document.body.appendChild(div);
}

function speak(text) {
    if (!isVoiceEnabled || !synth) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.1;
    utterance.pitch = 1.0;
    synth.speak(utterance);
}

function toggleVoice() {
    isVoiceEnabled = !isVoiceEnabled;
    const btn = document.getElementById('ai-voice-btn');
    btn.textContent = isVoiceEnabled ? '🔊' : '🔇';
    if(isVoiceEnabled) speak("Voice alerts enabled.");
}

function toggleAssistantBody() {
    const body = document.getElementById('ai-body');
    body.style.display = body.style.display === 'none' ? 'flex' : 'none';
}

function addAssistantMessage(text, type='info') {
    const body = document.getElementById('ai-body');
    if(!body) return;
    const msg = document.createElement('div');
    msg.className = 'ai-message ' + type;
    msg.textContent = text;
    body.appendChild(msg);
    body.scrollTop = body.scrollHeight;
    
    // Only speak warnings or dangers
    if(type === 'warning' || type === 'danger' || type === 'greeting') {
        speak(text);
    }
}

async function startAssistant(userId, lat, lng) {
    if(assistantSessionId) return; // Already running
    
    document.getElementById('ai-assistant-widget').classList.add('active');
    
    try {
        const res = await fetch('http://localhost:8000/assistant/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({user_id: userId, lat: lat, lng: lng})
        });
        const data = await res.json();
        if(data.session_id) {
            assistantSessionId = data.session_id;
            addAssistantMessage(data.greeting || "Your journey has started. I am monitoring your safety.", 'greeting');
            
            // Start Ping Loop
            assistantPingInterval = setInterval(pingAssistant, 15000); // every 15s for demo
        }
    } catch(e) {
        console.error("Failed to start assistant:", e);
    }
}

async function stopAssistant() {
    if(!assistantSessionId) return;
    clearInterval(assistantPingInterval);
    document.getElementById('ai-assistant-widget').classList.remove('active');
    try {
        await fetch(`http://localhost:8000/assistant/stop?session_id=${assistantSessionId}`, { method: 'POST' });
    } catch(e) {}
    assistantSessionId = null;
    addAssistantMessage("Journey ended. Stay safe!");
}

async function pingAssistant() {
    if(!assistantSessionId || !window.userLatLng) return;
    
    const speed = window.userSpeed || 0; // Speed in km/h if available from geolocation
    
    try {
        const res = await fetch('http://localhost:8000/assistant/ping', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: assistantSessionId,
                user_id: _userId(), // Assumes _userId() from index.html
                lat: window.userLatLng.lat,
                lng: window.userLatLng.lng,
                speed: speed,
                context_overrides: {}
            })
        });
        const data = await res.json();
        
        if (data.recommendations && data.recommendations.length > 0) {
            data.recommendations.forEach(r => addAssistantMessage(r.text, 'info'));
        }
        
        if (data.detected_events && data.detected_events.length > 0) {
            data.detected_events.forEach(e => addAssistantMessage(e.description, e.severity === 'high' ? 'danger' : 'warning'));
        }
        
        if (data.requires_checkin) {
            triggerCheckin();
        }
        
    } catch(e) {
        console.error("Assistant Ping Error:", e);
    }
}

function triggerCheckin() {
    document.getElementById('ai-checkin-modal').classList.add('active');
    speak("Unusual situation detected. Are you safe? Please confirm.");
}

async function respondCheckin(status) {
    document.getElementById('ai-checkin-modal').classList.remove('active');
    
    if(status === 'safe') {
        addAssistantMessage("Check-in complete. Glad you are safe.");
    } else if (status === 'emergency') {
        addAssistantMessage("Emergency Auto-SOS Triggered!", "danger");
        if(window.triggerSOS) window.triggerSOS(); // Call existing SOS
    } else {
        addAssistantMessage("Escalating to Trusted Contacts.", "warning");
    }
    
    try {
        await fetch('http://localhost:8000/assistant/checkin', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ session_id: assistantSessionId, status: status })
        });
    } catch(e) {}
}

document.addEventListener('DOMContentLoaded', () => {
    injectAssistantUI();
});
