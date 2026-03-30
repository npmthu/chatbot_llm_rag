'use strict';

// ── Config ────────────────────────────────────────────────────
const API_BASE = '/api';

// ── State ─────────────────────────────────────────────────────
let sessionId = null;
let isLoading = false;

// ── DOM refs ──────────────────────────────────────────────────
const messagesEl = document.getElementById('messages');
const inputEl    = document.getElementById('input');
const sendBtn    = document.getElementById('sendBtn');
const clearBtn   = document.getElementById('clearBtn');
const menuBtn    = document.getElementById('menuBtn');
const sidebar    = document.getElementById('sidebar');
const overlay    = document.getElementById('overlay');
const sidebarClose = document.getElementById('sidebarClose');
const statusDot  = document.getElementById('statusDot');
const statusLabel = document.getElementById('statusLabel');

// ── Helpers ───────────────────────────────────────────────────
function now() {
  return new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

/** Minimal markdown: bold, newlines */
function renderText(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>');
}

function scrollToBottom() {
  messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: 'smooth' });
}

// ── Render helpers ────────────────────────────────────────────
function renderWelcome() {
  messagesEl.innerHTML = `
    <div class="welcome">
      <div class="welcome-logo">NMK</div>
      <h2>Xin chào! Tôi là trợ lý AI</h2>
      <p>Tôi có thể trả lời các câu hỏi về <strong>Nguyen Minh Khang Architects</strong> —
         dịch vụ thiết kế, thi công, dự án nổi bật và thông tin liên hệ.</p>
    </div>`;
}

function appendUserMsg(text) {
  const el = document.createElement('div');
  el.className = 'msg msg--user';
  el.innerHTML = `
    <div class="msg-avatar">Bạn</div>
    <div class="msg-body">
      <div class="msg-bubble"><p>${renderText(text)}</p></div>
      <span class="msg-time">${now()}</span>
    </div>`;
  messagesEl.appendChild(el);
  scrollToBottom();
}

function appendTypingIndicator() {
  const el = document.createElement('div');
  el.className = 'msg msg--bot msg--typing';
  el.id = 'typing';
  el.innerHTML = `
    <div class="msg-avatar">NMK</div>
    <div class="msg-body">
      <div class="msg-bubble">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </div>
    </div>`;
  messagesEl.appendChild(el);
  scrollToBottom();
  return el;
}

function removeTypingIndicator() {
  const el = document.getElementById('typing');
  if (el) el.remove();
}

function buildSourcesHTML(sources) {
  if (!sources || sources.length === 0) return '';
  const items = sources.map((s, i) => `
    <div class="source-item">
      <div class="source-meta">
        <span class="source-badge">#${i + 1}</span>
        <span class="source-score">Độ phù hợp: ${(s.score * 100).toFixed(0)}%</span>
      </div>
      <div class="source-text">${s.text.substring(0, 200)}${s.text.length > 200 ? '…' : ''}</div>
    </div>`).join('');

  return `
    <div class="sources">
      <button class="sources-toggle" onclick="toggleSources(this)" aria-expanded="false">
        <span>&#128196; ${sources.length} nguồn tham khảo</span>
        <svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>
      <div class="sources-body">${items}</div>
    </div>`;
}

function appendBotMsg(text, sources, isError = false) {
  // Remove welcome screen on first real message
  const welcome = messagesEl.querySelector('.welcome');
  if (welcome) welcome.remove();

  const el = document.createElement('div');
  el.className = 'msg msg--bot';
  el.innerHTML = `
    <div class="msg-avatar">NMK</div>
    <div class="msg-body">
      <div class="msg-bubble${isError ? ' msg-bubble--error' : ''}"><p>${renderText(text)}</p></div>
      ${buildSourcesHTML(sources)}
      <span class="msg-time">${now()}</span>
    </div>`;
  messagesEl.appendChild(el);
  scrollToBottom();
}

// ── Sources toggle ────────────────────────────────────────────
window.toggleSources = function (btn) {
  const body = btn.nextElementSibling;
  const open = body.classList.toggle('open');
  btn.classList.toggle('open', open);
  btn.setAttribute('aria-expanded', String(open));
};

// ── Send message ──────────────────────────────────────────────
async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || isLoading) return;

  // Remove welcome if still showing
  const welcome = messagesEl.querySelector('.welcome');
  if (welcome) welcome.remove();

  isLoading = true;
  sendBtn.disabled = true;
  inputEl.value = '';
  autoResize();

  appendUserMsg(text);
  appendTypingIndicator();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text, session_id: sessionId }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    sessionId = data.session_id;

    removeTypingIndicator();
    appendBotMsg(data.answer, data.sources);
  } catch (err) {
    removeTypingIndicator();
    appendBotMsg(`Đã xảy ra lỗi: ${err.message}`, null, true);
  } finally {
    isLoading = false;
    sendBtn.disabled = inputEl.value.trim().length === 0;
    inputEl.focus();
  }
}

// ── Health check ──────────────────────────────────────────────
async function checkHealth() {
  statusDot.className = 'status-dot loading';
  statusLabel.textContent = 'Đang kết nối...';
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    statusDot.className = 'status-dot ok';
    statusLabel.textContent = `${data.llm_model} · ${data.collection}`;
  } catch {
    statusDot.className = 'status-dot error';
    statusLabel.textContent = 'Không kết nối được';
  }
}

// ── Auto-resize textarea ──────────────────────────────────────
function autoResize() {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
}

// ── Sidebar ───────────────────────────────────────────────────
function openSidebar()  { sidebar.classList.add('open'); overlay.classList.add('open'); }
function closeSidebar() { sidebar.classList.remove('open'); overlay.classList.remove('open'); }

// ── Event listeners ───────────────────────────────────────────
sendBtn.addEventListener('click', sendMessage);

inputEl.addEventListener('input', () => {
  autoResize();
  sendBtn.disabled = inputEl.value.trim().length === 0;
});

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

clearBtn.addEventListener('click', () => {
  sessionId = null;
  renderWelcome();
});

menuBtn.addEventListener('click', openSidebar);
sidebarClose.addEventListener('click', closeSidebar);
overlay.addEventListener('click', closeSidebar);

// Suggestion chips
document.querySelectorAll('.suggestion-chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    inputEl.value = chip.dataset.q;
    autoResize();
    sendBtn.disabled = false;
    closeSidebar();
    sendMessage();
  });
});

// ── Init ──────────────────────────────────────────────────────
renderWelcome();
checkHealth();
inputEl.focus();
