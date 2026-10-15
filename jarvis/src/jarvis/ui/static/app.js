/**
 * J.A.R.V.I.S. Multi-Agent System - Client Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const chatContainer = document.getElementById('chat-container');
  const messagesList = document.getElementById('messages-list');
  const welcomeCard = document.getElementById('welcome-card');
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const clearChatBtn = document.getElementById('clear-chat-btn');
  const workspaceRootDisplay = document.getElementById('workspace-root-display');
  const workspaceFileList = document.getElementById('workspace-file-list');
  const refreshWorkspaceBtn = document.getElementById('refresh-workspace-btn');

  // HITL Elements
  const hitlContainer = document.getElementById('hitl-container');
  const hitlQuestion = document.getElementById('hitl-question');
  const hitlInput = document.getElementById('hitl-input');
  const hitlSubmitBtn = document.getElementById('hitl-submit-btn');
  const hitlDismissBtn = document.getElementById('hitl-dismiss-btn');

  // Logs Modal Elements
  const viewLogsBtn = document.getElementById('view-logs-btn');
  const logsModal = document.getElementById('logs-modal');
  const logsModalBackdrop = document.getElementById('logs-modal-backdrop');
  const logsContent = document.getElementById('logs-content');
  const refreshLogsBtn = document.getElementById('refresh-logs-btn');
  const closeLogsBtn = document.getElementById('close-logs-btn');

  // State
  let isExecuting = false;
  let lastTask = '';

  // Initial load
  loadWorkspace();

  // Event Listeners
  chatForm.addEventListener('submit', handleFormSubmit);
  chatInput.addEventListener('keydown', handleInputKeydown);
  chatInput.addEventListener('input', autoResizeTextarea);
  clearChatBtn.addEventListener('click', handleClearChat);
  refreshWorkspaceBtn.addEventListener('click', loadWorkspace);

  // Logs Modal Handlers
  if (viewLogsBtn) {
    viewLogsBtn.addEventListener('click', () => {
      logsModal.classList.remove('hidden');
      loadLogs();
    });
  }
  if (closeLogsBtn) {
    closeLogsBtn.addEventListener('click', () => logsModal.classList.add('hidden'));
  }
  if (logsModalBackdrop) {
    logsModalBackdrop.addEventListener('click', () => logsModal.classList.add('hidden'));
  }
  if (refreshLogsBtn) {
    refreshLogsBtn.addEventListener('click', loadLogs);
  }

  // Preset Buttons
  document.querySelectorAll('.preset-btn, .quick-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const query = btn.getAttribute('data-query');
      if (query && !isExecuting) {
        submitQuery(query);
      }
    });
  });

  // HITL Clarification Handlers
  hitlSubmitBtn.addEventListener('click', handleHitlSubmit);
  hitlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleHitlSubmit();
    }
  });
  hitlDismissBtn.addEventListener('click', () => {
    hitlContainer.classList.add('hidden');
  });

  /**
   * Handle Main Chat Form Submission
   */
  async function handleFormSubmit(e) {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query || isExecuting) return;

    chatInput.value = '';
    autoResizeTextarea();
    await submitQuery(query);
  }

  /**
   * Keydown handler for chat textarea (Enter sends, Shift+Enter new line)
   */
  function handleInputKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event('submit'));
    }
  }

  /**
   * Auto-resizes the input textarea
   */
  function autoResizeTextarea() {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
  }

  /**
   * Submit Query to API
   */
  async function submitQuery(task, humanResponse = null) {
    if (isExecuting) return;
    isExecuting = true;
    lastTask = task;
    setExecutingState(true);

    if (welcomeCard) {
      welcomeCard.style.display = 'none';
    }

    // Render User Message
    if (!humanResponse) {
      renderUserMessage(task);
    } else {
      renderUserMessage(`[Human Response]: ${humanResponse}`);
    }

    // Hide any previous HITL banner
    hitlContainer.classList.add('hidden');

    // Create Loading Assistant Bubble
    const loadingCardId = 'loading-' + Date.now();
    renderLoadingAssistant(loadingCardId);
    scrollToBottom();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: task,
          human_response: humanResponse,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Network request failed' }));
        throw new Error(errorData.detail || `Server error (${response.status})`);
      }

      const data = await response.json();
      removeElementById(loadingCardId);
      renderAssistantMessage(data);

      // If Agent needs clarification, pop up HITL Card
      if (data.needs_human_input && data.clarification_question) {
        showHitlClarification(data.clarification_question);
      }

      // Refresh workspace after agent might have created/modified files
      loadWorkspace();
    } catch (err) {
      removeElementById(loadingCardId);
      renderAssistantError(err.message);
    } finally {
      isExecuting = false;
      setExecutingState(false);
      scrollToBottom();
      chatInput.focus();
    }
  }

  /**
   * Handle HITL Clarification Submission
   */
  async function handleHitlSubmit() {
    const val = hitlInput.value.trim();
    if (!val || isExecuting) return;

    hitlInput.value = '';
    hitlContainer.classList.add('hidden');
    await submitQuery(lastTask, val);
  }

  /**
   * Display HITL Banner
   */
  function showHitlClarification(questionText) {
    hitlQuestion.textContent = questionText;
    hitlContainer.classList.remove('hidden');
    hitlInput.focus();
  }

  /**
   * Render User Message Bubble
   */
  function renderUserMessage(text) {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const msgEl = document.createElement('div');
    msgEl.className = 'message-user';
    msgEl.innerHTML = `
      <div class="user-bubble">${escapeHtml(text)}</div>
      <div class="user-meta">${timeStr}</div>
    `;
    messagesList.appendChild(msgEl);
    scrollToBottom();
  }

  /**
   * Render Assistant Loading Skeleton
   */
  function renderLoadingAssistant(id) {
    const msgEl = document.createElement('div');
    msgEl.className = 'message-assistant';
    msgEl.id = id;
    msgEl.innerHTML = `
      <div class="assistant-card">
        <div class="assistant-header">
          <div class="assistant-header-left">
            <span class="worker-badge worker-supervisor">⚡ J.A.R.V.I.S. Multi-Agent</span>
          </div>
          <span class="trials-tag">Executing...</span>
        </div>
        <div class="assistant-body">
          <div class="loading-dots">
            <span></span><span></span><span></span>
          </div>
          <span style="margin-left: 8px; font-size: 0.85rem; color: var(--text-dim);">Supervisor routing and coordinating workers...</span>
        </div>
      </div>
    `;
    messagesList.appendChild(msgEl);
  }

  /**
   * Render Assistant Response
   */
  function renderAssistantMessage(data) {
    const worker = data.worker || 'supervisor';
    const workerBadgeClass = getWorkerBadgeClass(worker);
    const workerLabel = getWorkerLabel(worker);

    const verdictClass = data.success ? 'verdict-success' : (data.needs_human_input ? 'verdict-clarify' : 'verdict-failed');
    const verdictText = data.verdict || (data.success ? 'SUCCESS' : 'FAILED');

    // Format events for trace accordion
    let traceHtml = '';
    if (data.events && data.events.length > 0) {
      const eventItems = data.events.map(ev => {
        const evType = ev.event || ev.type || 'step';
        const evData = JSON.stringify(ev.data || ev, null, 2);
        return `<div class="trace-item"><strong>[${escapeHtml(evType)}]</strong> <pre style="margin-top:4px;">${escapeHtml(evData)}</pre></div>`;
      }).join('');

      traceHtml = `
        <details class="trace-details">
          <summary class="trace-summary">
            <span>🔍 Tool Trace & Execution Events (${data.events.length})</span>
            <span>▾</span>
          </summary>
          <div class="trace-content">
            ${eventItems}
          </div>
        </details>
      `;
    }

    const planHtml = data.plan && data.plan !== 'Fast-path greeting'
      ? `<div style="font-size:0.78rem; color:var(--text-dim); margin-bottom: 0.5rem;"><strong>Plan:</strong> ${escapeHtml(data.plan)}</div>`
      : '';

    const formattedOutcome = formatMarkdownText(data.outcome || 'Task complete.');

    const msgEl = document.createElement('div');
    msgEl.className = 'message-assistant';
    msgEl.innerHTML = `
      <div class="assistant-card">
        <div class="assistant-header">
          <div class="assistant-header-left">
            <span class="worker-badge ${workerBadgeClass}">${workerLabel}</span>
            <span class="verdict-badge ${verdictClass}">${escapeHtml(verdictText)}</span>
          </div>
          <span class="trials-tag">${data.trials ? `Trial ${data.trials}` : ''}</span>
        </div>
        ${planHtml}
        <div class="assistant-body">
          ${formattedOutcome}
        </div>
        ${traceHtml}
      </div>
    `;
    messagesList.appendChild(msgEl);
  }

  /**
   * Render Assistant Error
   */
  function renderAssistantError(errorMessage) {
    const msgEl = document.createElement('div');
    msgEl.className = 'message-assistant';
    msgEl.innerHTML = `
      <div class="assistant-card" style="border-color: rgba(239, 68, 68, 0.4);">
        <div class="assistant-header">
          <div class="assistant-header-left">
            <span class="worker-badge" style="background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3);">Execution Error</span>
          </div>
        </div>
        <div class="assistant-body" style="color: #fca5a5;">
          ${escapeHtml(errorMessage)}
        </div>
      </div>
    `;
    messagesList.appendChild(msgEl);
  }

  /**
   * Load and Display Workspace Files
   */
  async function loadWorkspace() {
    try {
      const res = await fetch('/api/workspace');
      if (!res.ok) return;
      const data = await res.json();

      if (data.root) {
        workspaceRootDisplay.textContent = '📁 ' + data.root.split('/').slice(-2).join('/');
        workspaceRootDisplay.title = 'Workspace: ' + data.root;
      }

      if (!data.files || data.files.length === 0) {
        workspaceFileList.innerHTML = '<div class="loading-placeholder">Workspace directory is empty</div>';
        return;
      }

      workspaceFileList.innerHTML = data.files.map(f => {
        const icon = f.is_dir ? '📁' : '📄';
        const sizeStr = f.is_dir ? 'dir' : formatBytes(f.size);
        return `
          <div class="file-item">
            <span class="file-name" title="${escapeHtml(f.name)}">
              <span>${icon}</span>
              <span>${escapeHtml(f.name)}</span>
            </span>
            <span class="file-size">${sizeStr}</span>
          </div>
        `;
      }).join('');
    } catch (e) {
      console.warn('Workspace fetch failed:', e);
    }
  }

  /**
   * Load Application Logs
   */
  async function loadLogs() {
    if (!logsContent) return;
    logsContent.textContent = 'Fetching latest application logs...';
    try {
      const res = await fetch('/api/logs?lines=150');
      if (!res.ok) {
        logsContent.textContent = 'Failed to load logs from server.';
        return;
      }
      const data = await res.json();
      if (!data.logs || data.logs.length === 0) {
        logsContent.textContent = 'No logs recorded yet.';
        return;
      }
      logsContent.textContent = data.logs.join('\n');
      const container = document.querySelector('.logs-viewer-body');
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    } catch (err) {
      logsContent.textContent = 'Error connecting to /api/logs: ' + err.message;
    }
  }

  /**
   * Clear Chat messages
   */
  function handleClearChat() {
    messagesList.innerHTML = '';
    if (welcomeCard) {
      welcomeCard.style.display = 'block';
    }
    hitlContainer.classList.add('hidden');
  }

  /**
   * Set UI Executing State
   */
  function setExecutingState(loading) {
    sendBtn.disabled = loading;
    chatInput.disabled = loading;
    if (!loading) {
      chatInput.focus();
    }
  }

  /**
   * Scroll chat to bottom smoothly
   */
  function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  /**
   * Helpers for Badges & Icons
   */
  function getWorkerBadgeClass(worker) {
    switch (worker) {
      case 'direct':
      case 'direct_worker':
        return 'worker-direct';
      case 'react':
      case 'react_worker':
        return 'worker-react';
      case 'reflexion':
      case 'reflexion_worker':
        return 'worker-reflexion';
      case 'hitl':
        return 'worker-hitl';
      default:
        return 'worker-supervisor';
    }
  }

  function getWorkerLabel(worker) {
    switch (worker) {
      case 'direct':
      case 'direct_worker':
        return '⚡ Direct Fast-Path';
      case 'react':
      case 'react_worker':
        return '🔍 Fast ReAct Worker';
      case 'reflexion':
      case 'reflexion_worker':
        return '🔄 Reflexion Worker';
      case 'hitl':
        return '❓ Human-In-The-Loop';
      default:
        return '👑 Executive Supervisor';
    }
  }

  /**
   * Formatting text with simple markdown support
   */
  function formatMarkdownText(text) {
    if (!text) return '';

    // Escape HTML first
    let safe = escapeHtml(text);

    // Code blocks with syntax backticks ```lang ... ```
    safe = safe.replace(/```([\s\S]*?)```/g, (match, p1) => {
      return `<pre><code>${p1.trim()}</code></pre>`;
    });

    // Inline code `...`
    safe = safe.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold **text**
    safe = safe.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Convert newlines to paragraphs/breaks
    const paragraphs = safe.split('\n\n').map(p => {
      if (p.startsWith('<pre>')) return p;
      return `<p>${p.replace(/\n/g, '<br>')}</p>`;
    }).join('');

    return paragraphs;
  }

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function removeElementById(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }
});
