// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', loadDocuments);

// ── Load Documents ────────────────────────────────────────────────────────────
async function loadDocuments() {
    try {
        const res  = await fetch('/api/documents/');
        const data = await res.json();

        renderStats(data.documents);
        renderDocuments(data.documents);

    } catch (err) {
        console.error('Failed to load documents:', err);
    }
}

// ── Render Stats ──────────────────────────────────────────────────────────────
function renderStats(docs) {
    document.getElementById('totalDocs').textContent   = docs.length;
    document.getElementById('totalChunks').textContent = docs.reduce((a, d) => a + d.chunk_count, 0);
    document.getElementById('readyDocs').textContent   = docs.filter(d => d.status === 'ready').length;
}

// ── Render Documents ──────────────────────────────────────────────────────────
function renderDocuments(docs) {
    const list  = document.getElementById('docsList');
    const empty = document.getElementById('docsEmpty');

    // Clear old cards but keep empty state
    list.querySelectorAll('.doc-card').forEach(c => c.remove());

    if (docs.length === 0) {
        empty.style.display = 'block';
        return;
    }

    empty.style.display = 'none';

    docs.forEach(doc => {
        const icon   = doc.file_type === 'pdf'  ? '📄'
                     : doc.file_type === 'docx' ? '📝' : '📃';

        const status = doc.status === 'ready'      ? '<span class="badge ready">✅ Ready</span>'
                     : doc.status === 'processing' ? '<span class="badge processing">⏳ Processing</span>'
                     : '<span class="badge failed">❌ Failed</span>';

        const size   = doc.size > 1024 * 1024
                     ? (doc.size / (1024 * 1024)).toFixed(1) + ' MB'
                     : (doc.size / 1024).toFixed(1) + ' KB';

        const card = document.createElement('div');
        card.className  = 'doc-card';
        card.dataset.id = doc.id;

        const summaryHTML = doc.summary
    ? `
        <button class="summary-toggle" onclick="toggleSummary(this)">
            📝 View Summary
        </button>
        <div class="summary-text">${escapeHTML(doc.summary)}</div>
    `
    : '';

card.innerHTML = `
    <div class="doc-icon">${icon}</div>
    <div class="doc-info">
        <div class="doc-name">${doc.name}</div>
        <div class="doc-meta">
            ${size} &nbsp;·&nbsp;
            ${doc.chunk_count} chunks &nbsp;·&nbsp;
            ${doc.uploaded_at}
        </div>
        ${summaryHTML}
    </div>
    <div class="doc-right">
        ${status}
        <button class="btn-delete" onclick="deleteDocument(${doc.id}, this)">
            🗑 Delete
        </button>
    </div>
`;

        list.appendChild(card);
    });
}

// ── Delete Document ───────────────────────────────────────────────────────────
async function deleteDocument(docId, btn) {
    if (!confirm('Are you sure you want to delete this document?')) return;

    btn.disabled    = true;
    btn.textContent = 'Deleting...';

    try {
        const res = await fetch(`/api/documents/${docId}/`, {
            method:  'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });

        const data = await res.json();

        if (data.success) {
            // Remove card from UI
            const card = document.querySelector(`.doc-card[data-id="${docId}"]`);
            card.style.opacity    = '0';
            card.style.transition = 'opacity 0.3s';
            setTimeout(() => {
                card.remove();
                loadDocuments(); // refresh stats
            }, 300);
        } else {
            alert('Failed to delete: ' + data.error);
            btn.disabled    = false;
            btn.textContent = '🗑 Delete';
        }

    } catch (err) {
        alert('Delete failed. Is the server running?');
        btn.disabled    = false;
        btn.textContent = '🗑 Delete';
    }
}

// ── CSRF ──────────────────────────────────────────────────────────────────────
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

// ── Toggle Summary ────────────────────────────────────────────────────────────
function toggleSummary(btn) {
    const summaryDiv = btn.nextElementSibling;
    summaryDiv.classList.toggle('open');
    btn.textContent = summaryDiv.classList.contains('open')
        ? '📝 Hide Summary'
        : '📝 View Summary';
}

// ── Escape HTML ───────────────────────────────────────────────────────────────
function escapeHTML(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}