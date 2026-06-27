// ── Selectors ────────────────────────────────────────────────────────────────
const uploadBox     = document.getElementById('uploadBox');
const fileInput     = document.getElementById('fileInput');
const fileList      = document.getElementById('fileList');
const uploadBtn     = document.getElementById('uploadBtn');
const uploadActions = document.getElementById('uploadActions');
const progressWrap  = document.getElementById('progressWrap');
const progressFill  = document.getElementById('progressFill');
const progressText  = document.getElementById('progressText');
const alertBox      = document.getElementById('alertBox');
const gotoChat      = document.getElementById('gotoChat');

let selectedFiles = [];

// ── Drag & Drop ──────────────────────────────────────────────────────────────
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('dragover');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('dragover');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('dragover');
    handleFiles([...e.dataTransfer.files]);
});

uploadBox.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', () => {
    handleFiles([...fileInput.files]);
});

// ── Handle Selected Files ────────────────────────────────────────────────────
function handleFiles(files) {
    const allowed = ['application/pdf', 'text/plain',
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

    files.forEach(file => {
        if (!allowed.includes(file.type)) {
            showAlert(`❌ Unsupported file: ${file.name}`, 'error');
            return;
        }
        if (!selectedFiles.find(f => f.name === file.name)) {
            selectedFiles.push(file);
        }
    });

    renderFileList();
}

// ── Render File List ─────────────────────────────────────────────────────────
function renderFileList() {
    fileList.innerHTML = '';

    selectedFiles.forEach((file, index) => {
        const icon = file.name.endsWith('.pdf')  ? '📄'
                   : file.name.endsWith('.docx') ? '📝' : '📃';

        const size = (file.size / 1024).toFixed(1) + ' KB';

        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <div class="file-name">
                <span>${icon}</span>
                <span>${file.name}</span>
                <span style="color:var(--text-muted); font-size:0.8rem;">${size}</span>
            </div>
            <button class="file-remove" onclick="removeFile(${index})">✕</button>
        `;
        fileList.appendChild(item);
    });

    uploadActions.style.display = selectedFiles.length > 0 ? 'block' : 'none';
}

// ── Remove File ──────────────────────────────────────────────────────────────
function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
}

// ── Upload Files ─────────────────────────────────────────────────────────────
uploadBtn.addEventListener('click', async () => {
    if (selectedFiles.length === 0) return;

    const formData = new FormData();
    selectedFiles.forEach(file => formData.append('documents', file));

    // Show progress
    uploadActions.style.display  = 'none';
    progressWrap.style.display   = 'block';
    alertBox.style.display       = 'none';
    gotoChat.style.display       = 'none';

    animateProgress();

    try {
        const response = await fetch('/api/documents/upload/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: formData,
        });

        const data = await response.json();

        stopProgress();

        if (data.success) {
            progressFill.style.width = '100%';
            progressText.textContent = '✅ Done!';
            showAlert(`✅ ${data.message}`, 'success');
            gotoChat.style.display = 'block';
            selectedFiles = [];
            renderFileList();
        } else {
            showAlert(`❌ ${data.error}`, 'error');
            progressWrap.style.display = 'none';
            uploadActions.style.display = 'block';
        }

    } catch (err) {
        stopProgress();
        showAlert('❌ Upload failed. Is the server running?', 'error');
        uploadActions.style.display = 'block';
    }
});

// ── Progress Animation ───────────────────────────────────────────────────────
let progressInterval;

function animateProgress() {
    let width = 0;
    const messages = [
        'Reading document...',
        'Extracting text from pages...',
        'Creating searchable chunks...',
        'Uploading to AI index...',
        'Almost ready...',
    ];
    let msgIndex = 0;
    progressInterval = setInterval(() => {
        if (width < 85) {
            width += Math.random() * 2;
            progressFill.style.width = Math.min(width, 85) + '%';
            progressText.textContent = messages[msgIndex % messages.length];
            msgIndex++;
        }
    }, 1500);
}

function stopProgress() {
    clearInterval(progressInterval);
}

// ── Alert ────────────────────────────────────────────────────────────────────
function showAlert(message, type) {
    alertBox.textContent  = message;
    alertBox.className    = `alert ${type}`;
    alertBox.style.display = 'block';
}

// ── CSRF Token ───────────────────────────────────────────────────────────────
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