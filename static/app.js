/* ── NETAI Chatbot Frontend ───────────────────────────────────────────── */

const API_BASE = '/api/v1';
let currentConversationId = null;
let isLoading = false;

/* ── Initialization ──────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', async () => {
    await checkHealth();
    await loadConversations();
    autoResizeTextarea();
});

async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();

        const dot = document.getElementById('statusDot');
        const text = document.getElementById('statusText');
        const modelInfo = document.getElementById('modelInfo');

        if (data.status === 'healthy') {
            dot.className = 'status-dot connected';
            text.textContent = 'Connected';
        } else {
            dot.className = 'status-dot error';
            text.textContent = 'Degraded';
        }

        modelInfo.textContent = `v${data.version} • ${data.telemetry_records} telemetry records`;
        if (data.llm_available) {
            modelInfo.textContent += ' • LLM ready';
        }
    } catch (e) {
        document.getElementById('statusDot').className = 'status-dot error';
        document.getElementById('statusText').textContent = 'Disconnected';
    }
}

/* ── Chat Functions ──────────────────────────────────────────────────── */

async function sendMessage() {
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    if (!message || isLoading) return;

    isLoading = true;
    document.getElementById('sendBtn').disabled = true;

    // Clear welcome message
    const welcome = document.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    // Add user message to UI
    appendMessage('user', message);
    input.value = '';
    input.style.height = 'auto';

    // Show typing indicator
    const typingEl = showTypingIndicator();

    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                conversation_id: currentConversationId,
                include_context: true,
            }),
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || 'Chat request failed');
        }

        currentConversationId = data.conversation_id;
        typingEl.remove();
        appendMessage('assistant', data.message);

        // Update conversation list
        await loadConversations();
    } catch (e) {
        typingEl.remove();
        appendMessage('assistant', `❌ Error: ${e.message}. Please try again.`);
    } finally {
        isLoading = false;
        document.getElementById('sendBtn').disabled = false;
        input.focus();
    }
}

function sendQuickMessage(text) {
    document.getElementById('userInput').value = text;
    sendMessage();
}

function appendMessage(role, content) {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const avatar = role === 'user' ? '👤' : '🌐';
    const formattedContent = formatMarkdown(content);

    div.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">${formattedContent}</div>
    `;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.id = 'typingIndicator';
    div.innerHTML = `
        <div class="message-avatar">🌐</div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
}

function formatMarkdown(text) {
    // Simple markdown to HTML conversion
    let html = text
        // Code blocks
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Headers
        .replace(/^### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        // Lists
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
        // Paragraphs
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    // Wrap orphan <li> in <ul>
    html = html.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
    html = html.replace(/<\/ul>\s*<ul>/g, '');

    return `<p>${html}</p>`;
}

/* ── Conversation Management ─────────────────────────────────────────── */

async function newConversation() {
    currentConversationId = null;
    document.getElementById('messages').innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">🌐</div>
            <h2>Welcome to NETAI</h2>
            <p>I'm your AI-powered network diagnostics assistant. Ask me about network performance, anomalies, or diagnostics.</p>
            <div class="quick-actions">
                <button onclick="sendQuickMessage('Show me the current network health summary')">📊 Network Health</button>
                <button onclick="sendQuickMessage('Are there any active anomalies on the network?')">⚠️ Check Anomalies</button>
                <button onclick="sendQuickMessage('Analyze the path between UCSD and Starlight')">🔍 Path Analysis</button>
                <button onclick="sendQuickMessage('What is the current throughput between TACC and NERSC?')">📈 Throughput Check</button>
            </div>
        </div>
    `;
    document.getElementById('chatTitle').textContent = 'NETAI Diagnostics Assistant';
    highlightConversation(null);
}

async function loadConversations() {
    try {
        const res = await fetch(`${API_BASE}/chat/conversations`);
        const convs = await res.json();

        const list = document.getElementById('conversationsList');
        list.innerHTML = '';

        for (const conv of convs) {
            const div = document.createElement('div');
            div.className = `conv-item ${conv.id === currentConversationId ? 'active' : ''}`;
            div.textContent = conv.title;
            div.onclick = () => loadConversation(conv.id, conv.title);
            list.appendChild(div);
        }
    } catch (e) {
        console.error('Failed to load conversations:', e);
    }
}

async function loadConversation(id, title) {
    currentConversationId = id;
    document.getElementById('chatTitle').textContent = title || 'Conversation';
    highlightConversation(id);

    try {
        const res = await fetch(`${API_BASE}/chat/conversations/${id}/messages`);
        const messages = await res.json();

        const container = document.getElementById('messages');
        container.innerHTML = '';

        for (const msg of messages) {
            if (msg.role !== 'system') {
                appendMessage(msg.role, msg.content);
            }
        }
    } catch (e) {
        console.error('Failed to load conversation:', e);
    }
}

function highlightConversation(id) {
    document.querySelectorAll('.conv-item').forEach(el => {
        el.classList.toggle('active', false);
    });
}

/* ── Side Panel ──────────────────────────────────────────────────────── */

async function showAnomalies() {
    const panel = document.getElementById('sidePanel');
    const app = document.querySelector('.app');
    const content = document.getElementById('panelContent');
    document.getElementById('panelTitle').textContent = 'Network Anomalies';

    content.innerHTML = '<p style="color: var(--text-secondary)">Loading...</p>';
    app.classList.add('panel-open');

    try {
        const res = await fetch(`${API_BASE}/diagnostics/anomalies`);
        const anomalies = await res.json();

        if (anomalies.length === 0) {
            content.innerHTML = '<p style="color: var(--text-secondary); padding: 20px; text-align:center;">✅ No anomalies detected</p>';
            return;
        }

        content.innerHTML = anomalies.map(a => `
            <div class="anomaly-card ${a.severity}">
                <span class="severity ${a.severity}">${a.severity}</span>
                <div class="description">${a.description}</div>
                <div class="hosts">${a.src_host} → ${a.dst_host}</div>
            </div>
        `).join('');
    } catch (e) {
        content.innerHTML = `<p style="color: var(--red)">Failed to load anomalies</p>`;
    }
}

async function showHosts() {
    const app = document.querySelector('.app');
    const content = document.getElementById('panelContent');
    document.getElementById('panelTitle').textContent = 'Monitored Hosts';

    content.innerHTML = '<p style="color: var(--text-secondary)">Loading...</p>';
    app.classList.add('panel-open');

    try {
        const res = await fetch(`${API_BASE}/diagnostics/telemetry/hosts`);
        const data = await res.json();

        if (!data.host_pairs || data.host_pairs.length === 0) {
            content.innerHTML = '<p style="color: var(--text-secondary); padding: 20px; text-align:center;">No hosts found</p>';
            return;
        }

        content.innerHTML = data.host_pairs.map(p => `
            <div class="host-pair">
                <strong>${p.src_host}</strong> → <strong>${p.dst_host}</strong>
                <div class="metrics">Metrics: ${p.metric_types}</div>
            </div>
        `).join('');
    } catch (e) {
        content.innerHTML = `<p style="color: var(--red)">Failed to load hosts</p>`;
    }
}

function closeSidePanel() {
    document.querySelector('.app').classList.remove('panel-open');
}

/* ── Utilities ───────────────────────────────────────────────────────── */

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResizeTextarea() {
    const textarea = document.getElementById('userInput');
    textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    });
}
