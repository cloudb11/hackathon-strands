const API = "http://localhost:8000";

// Track session for multi-turn conversation memory
let currentSessionId = null;

async function uploadFiles() {
    const files = document.getElementById("file-input").files;
    const status = document.getElementById("upload-status");
    status.textContent = "Uploading...";
    for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        await fetch(`${API}/ingest`, { method: "POST", body: form });
    }
    status.textContent = `✅ ${files.length} file(s) ingested`;
}

async function askQuestion() {
    const input = document.getElementById("question");
    const q = input.value.trim();
    if (!q) return;
    addMessage("You", q);
    input.value = "";
    addMessage("AI", "Thinking...", "thinking");
    try {
        console.log("[DEBUG] Sending session_id:", currentSessionId);
        const res = await fetch(`${API}/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question: q,
                session_id: currentSessionId  // Send session for conversation continuity
            })
        });
        const data = await res.json();
        console.log("[DEBUG] Received response:", data);
        console.log("[DEBUG] Received session_id:", data.session_id);
        removeThinking();
        addMessage("AI", data.answer);
        // Store session_id from response for subsequent messages
        if (data.session_id) {
            currentSessionId = data.session_id;
            console.log("[DEBUG] Stored currentSessionId:", currentSessionId);
        }
    } catch (err) {
        removeThinking();
        addMessage("AI", "⚠️ Error: " + err.message);
    }
}

function newSession() {
    currentSessionId = null;
    const div = document.getElementById("messages");
    div.innerHTML = "";
    addMessage("AI", "New conversation started. How can I help you?");
}

function addMessage(sender, text, id = "") {
    const div = document.getElementById("messages");
    const msg = document.createElement("div");
    msg.className = "msg";
    if (id) msg.id = id;
    msg.textContent = sender + ": " + text;
    div.appendChild(msg);
    div.scrollTop = div.scrollHeight;
}

function removeThinking() {
    const el = document.getElementById("thinking");
    if (el) el.remove();
}

