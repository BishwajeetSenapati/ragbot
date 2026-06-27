// ── State ─────────────────────────────────────────────────────────────────────
let currentSessionId = null;
let selectedDocIds   = [];
let allSelected      = true;

// ── Selectors (assigned after DOM loads) ──────────────────────────────────────
let chatMessages, questionInput, sendBtn, newChatBtn;
let sessionList, typingIndicator, clearChatBtn, chatHeader;
let selectAllBtn, docSelectorList;

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    chatMessages    = document.getElementById('chatMessages');
    questionInput   = document.getElementById('questionInput');
    sendBtn         = document.getElementById('sendBtn');
    newChatBtn      = document.getElementById('newChatBtn');
    sessionList     = document.getElementById('sessionList');
    typingIndicator = document.getElementById('typingIndicator');
    clearChatBtn    = document.getElementById('clearChatBtn');
    chatHeader      = document.getElementById('chatHeader');
    selectAllBtn    = document.getElementById('selectAllBtn');
    docSelectorList = document.getElementById('docSelectorList');

    // Event listeners
    clearChatBtn.addEventListener('click', clearChatHistory);
    newChatBtn.addEventListener('click', startNewSession);
    sendBtn.addEventListener('click', sendMessage);

    selectAllBtn.addEventListener('click', () => {
        allSelected = !allSelected;
        document.querySelectorAll('.doc-checkbox').forEach(cb => {
            cb.checked = allSelected;
        });
        updateSelectedDocs();
        selectAllBtn.textContent = allSelected ? 'All' : 'None';
    });

    questionInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    questionInput.addEventListener('input', () => {
        questionInput.style.height = 'auto';
        questionInput.style.height = questionInput.scrollHeight + 'px';
    });

    // Load data
    await loadSessions();
    await loadDocumentSelector();
    await startNewSession();
});

// ── Document Selector ─────────────────────────────────────────────────────────
async function loadDocumentSelector() {
    try {
        const res  = await fetch('/api/documents/');
        const data = await res.json();

        docSelectorList.innerHTML = '';

        if (data.documents.length === 0) {
            docSelectorList.innerHTML = '<p class="sidebar-empty">No documents yet.</p>';
            selectedDocIds = [];
            return;
        }

        // Default: all selected
        selectedDocIds = data.documents
            .filter(d => d.status === 'ready')
            .map(d => String(d.id));

        data.documents.forEach(doc => {
            if (doc.status !== 'ready') return;

            const item = document.createElement('div');
            item.className = 'doc-select-item';

            const icon = doc.file_type === 'pdf'  ? '📄'
                       : doc.file_type === 'docx' ? '📝' : '📃';

            // Truncate long filenames
            const shortName = doc.name.length > 22
                ? doc.name.substring(0, 22) + '...'
                : doc.name;

            item.innerHTML = `
                <label class="doc-select-label" title="${escapeAttr(doc.name)}">
                    <input
                        type="checkbox"
                        class="doc-checkbox"
                        value="${doc.id}"
                        checked
                    />
                    <span>${icon} ${escapeHTML(shortName)}</span>
                </label>
            `;

            item.querySelector('.doc-checkbox')
                .addEventListener('change', updateSelectedDocs);
            docSelectorList.appendChild(item);
        });

    } catch (err) {
        console.error('Failed to load document selector:', err);
    }
}

function updateSelectedDocs() {
    const checkboxes = document.querySelectorAll('.doc-checkbox:checked');
    selectedDocIds   = [...checkboxes].map(cb => cb.value);
    console.log('Selected docs:', selectedDocIds);
}

// ── Sessions ──────────────────────────────────────────────────────────────────
async function loadSessions() {
    try {
        const res  = await fetch('/api/sessions/list/');
        const data = await res.json();

        sessionList.innerHTML = '';

        if (data.sessions.length === 0) {
            sessionList.innerHTML = '<p class="sidebar-empty">No chats yet.</p>';
            return;
        }

        data.sessions.forEach(session => {
            const item = document.createElement('div');
            item.className = 'session-item';
            item.dataset.sessionId = session.session_id;

            if (session.session_id === currentSessionId) {
                item.classList.add('active');
            }

            item.innerHTML = `
                <span class="session-title">${escapeHTML(session.title)}</span>
                <button class="session-delete" title="Delete chat">🗑</button>
            `;

            item.querySelector('.session-title').addEventListener('click', () => {
                loadSession(session.session_id);
            });

            item.querySelector('.session-delete').addEventListener('click', (e) => {
                e.stopPropagation();
                deleteSession(session.session_id);
            });

            sessionList.appendChild(item);
        });

    } catch (err) {
        console.error('Failed to load sessions:', err);
    }
}

async function startNewSession() {
    try {
        const res  = await fetch('/api/sessions/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });
        const data = await res.json();
        currentSessionId = data.session_id;
        chatHeader.style.display = 'flex';

        chatMessages.innerHTML = `
            <div class="welcome-msg">
                <h2>👋 New Chat Started</h2>
                <p>Ask me anything about your uploaded documents.</p>
            </div>
        `;

        await loadSessions();

    } catch (err) {
        console.error('Failed to create session:', err);
    }
}

async function loadSession(sessionId) {
    try {
        currentSessionId = sessionId;
        chatHeader.style.display = 'flex';

        const res  = await fetch(`/api/sessions/${sessionId}/messages/`);
        const data = await res.json();

        chatMessages.innerHTML = '';

        if (data.messages.length === 0) {
            chatMessages.innerHTML = `
                <div class="welcome-msg">
                    <h2>👋 Empty Chat</h2>
                    <p>Ask me anything about your uploaded documents.</p>
                </div>
            `;
        } else {
            data.messages.forEach(msg =>
                renderMessage(msg.role, msg.content, msg.sources)
            );
            scrollToBottom();
        }

        highlightActiveSession(sessionId);

    } catch (err) {
        console.error('Failed to load session:', err);
    }
}

function highlightActiveSession(sessionId) {
    document.querySelectorAll('.session-item').forEach(item => {
        item.classList.toggle('active', item.dataset.sessionId === sessionId);
    });
}

// ── Delete Session ────────────────────────────────────────────────────────────
async function deleteSession(sessionId) {
    if (!confirm('Delete this entire chat? This cannot be undone.')) return;

    try {
        const res  = await fetch(`/api/sessions/${sessionId}/delete/`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });
        const data = await res.json();

        if (data.success) {
            if (sessionId === currentSessionId) {
                await startNewSession();
            } else {
                await loadSessions();
            }
        } else {
            alert('Failed to delete: ' + data.error);
        }

    } catch (err) {
        alert('Delete failed. Is the server running?');
    }
}

// ── Clear Chat History ────────────────────────────────────────────────────────
async function clearChatHistory() {
    if (!currentSessionId) return;
    if (!confirm('Clear all messages in this chat? This cannot be undone.')) return;

    try {
        const res  = await fetch(`/api/sessions/${currentSessionId}/clear/`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });
        const data = await res.json();

        if (data.success) {
            chatMessages.innerHTML = `
                <div class="welcome-msg">
                    <h2>🧹 Chat Cleared</h2>
                    <p>Ask me anything about your uploaded documents.</p>
                </div>
            `;
            await loadSessions();
        } else {
            alert('Failed to clear: ' + data.error);
        }

    } catch (err) {
        alert('Clear failed. Is the server running?');
    }
}

// ── Send Message ──────────────────────────────────────────────────────────────
async function sendMessage() {
    const question = questionInput.value.trim();
    if (!question || !currentSessionId) return;

    questionInput.value = '';
    questionInput.style.height = 'auto';

    const welcome = chatMessages.querySelector('.welcome-msg');
    if (welcome) welcome.remove();

    renderMessage('user', question, []);
    scrollToBottom();

    typingIndicator.style.display = 'flex';
    sendBtn.disabled = true;

    try {
        const res = await fetch('/api/ask/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken':  getCookie('csrftoken'),
            },
            body: JSON.stringify({
                question:   question,
                session_id: currentSessionId,
                doc_ids:    selectedDocIds,
            }),
        });

        const data = await res.json();

        typingIndicator.style.display = 'none';
        sendBtn.disabled = false;

        if (data.answer) {
            renderMessage('assistant', data.answer, data.sources || []);
            scrollToBottom();
            await loadSessions();
        } else {
            renderMessage('assistant', `❌ ${data.error}`, []);
        }

    } catch (err) {
        typingIndicator.style.display = 'none';
        sendBtn.disabled = false;
        renderMessage('assistant', '❌ Failed to get a response. Is the server running?', []);
    }
}

// ── Render Message ────────────────────────────────────────────────────────────
function renderMessage(role, content, sources) {
    const msg = document.createElement('div');
    msg.className = `message ${role}`;

    const time = new Date().toLocaleTimeString([], {
        hour: '2-digit', minute: '2-digit'
    });

    let sourcesHTML = '';
    if (role === 'assistant' && sources && sources.length > 0) {
        const cards = sources.map(s => `
            <div class="source-card">
                <strong>📄 Page ${s.page}</strong>
                ${escapeHTML(s.snippet)}
            </div>
        `).join('');

        sourcesHTML = `
            <div class="sources">
                <button class="sources-toggle" onclick="toggleSources(this)">
                    📚 ${sources.length} source(s)
                </button>
                <div class="sources-list">${cards}</div>
            </div>
        `;
    }

    const copyBtnHTML = role === 'assistant'
        ? `<button class="copy-btn" onclick="copyAnswer(this)">📋 Copy</button>`
        : '';

    msg.innerHTML = `
        <div class="bubble" data-raw-text="${escapeAttr(content)}">${escapeHTML(content)}</div>
        ${copyBtnHTML}
        <div class="message-time">${time}</div>
        ${sourcesHTML}
    `;

    chatMessages.appendChild(msg);
}

// ── Toggle Sources ────────────────────────────────────────────────────────────
function toggleSources(btn) {
    const list = btn.nextElementSibling;
    list.classList.toggle('open');
    btn.textContent = list.classList.contains('open')
        ? '📚 Hide sources'
        : `📚 ${list.children.length} source(s)`;
}

// ── Copy Answer ───────────────────────────────────────────────────────────────
function copyAnswer(btn) {
    const bubble = btn.previousElementSibling;
    const text   = bubble.dataset.rawText;

    navigator.clipboard.writeText(text).then(() => {
        const original  = btn.textContent;
        btn.textContent = '✅ Copied!';
        setTimeout(() => { btn.textContent = original; }, 1500);
    });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHTML(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/\n/g, '<br>');
}

function escapeAttr(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        document.cookie.split(';').forEach(cookie => {
            const c = cookie.trim();
            if (c.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(c.substring(name.length + 1));
            }
        });
    }
    return cookieValue;
}