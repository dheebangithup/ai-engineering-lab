/**
 * Enterprise Knowledge Hub RAG Portal Engine
 * Frontend JavaScript Client
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Knowledge Hub UI] Initializing RAG Web Portal application...');

    // ── Global Application State ─────────────────────────────────────
    const AppState = {
        documents: [],
        currentTab: 'tab-search',
        selectedIngestFile: null,
        isSearching: false,
        isIngesting: false
    };

    // ── DOM Element Selectors ─────────────────────────────────────────
    const DOM = {
        // Navigation
        navItems: document.querySelectorAll('.nav-item'),
        tabPanes: document.querySelectorAll('.tab-pane'),
        tabTitle: document.getElementById('current-tab-title'),
        tabSubtitle: document.getElementById('current-tab-subtitle'),
        sidebarDocCount: document.getElementById('sidebar-doc-count'),
        btnRefreshAll: document.getElementById('btn-refresh-all'),

        // Search Form Elements
        searchForm: document.getElementById('search-form'),
        searchQuery: document.getElementById('search-query'),
        searchTopK: document.getElementById('search-top-k'),
        valTopK: document.getElementById('val-top-k'),
        searchScoreThreshold: document.getElementById('search-score-threshold'),
        valScoreThreshold: document.getElementById('val-score-threshold'),
        searchEnableLlm: document.getElementById('search-enable-llm'),
        searchTemperature: document.getElementById('search-temperature'),
        valTemperature: document.getElementById('val-temperature'),
        btnSubmitSearch: document.getElementById('btn-submit-search'),

        // Prompt Provisioning Form Elements
        searchPromptName: document.getElementById('search-prompt-name'),
        searchPromptVersion: document.getElementById('search-prompt-version'),
        searchAdditionalVars: document.getElementById('search-additional-vars'),

        // ContextBuilder Overrides Form Elements
        cbMaxTokens: document.getElementById('cb-max-tokens'),
        cbSortStrategy: document.getElementById('cb-sort-strategy'),
        cbMinScoreThreshold: document.getElementById('cb-min-score-threshold'),
        valCbMinScore: document.getElementById('val-cb-min-score'),
        cbAdjacentExpansion: document.getElementById('cb-adjacent-expansion'),
        cbAdjacencyWindow: document.getElementById('cb-adjacency-window'),
        cbChunkMerging: document.getElementById('cb-chunk-merging'),
        cbMergeGap: document.getElementById('cb-merge-gap'),
        cbSourceHeader: document.getElementById('cb-source-header'),
        cbChunkSeparator: document.getElementById('cb-chunk-separator'),
        cbHeaderTemplate: document.getElementById('cb-header-template'),
        cbSeparatorStr: document.getElementById('cb-separator-str'),
        searchFilters: document.getElementById('search-filters'),

        // Search Result Workspace Sub-Tabs & Outputs
        resTabBtns: document.querySelectorAll('.tabs-header .tab-btn'),
        resPanes: document.querySelectorAll('.res-panel'),
        chunkCountBadge: document.getElementById('chunk-count-badge'),
        llmOutputContainer: document.getElementById('llm-output-container'),
        chunksOutputContainer: document.getElementById('chunks-output-container'),
        ctxTokenCount: document.getElementById('ctx-token-count'),
        ctxChunkCount: document.getElementById('ctx-chunk-count'),
        contextTextBlock: document.getElementById('context-text-block'),
        renderedPromptBadge: document.getElementById('rendered-prompt-badge'),
        promptTextBlock: document.getElementById('prompt-text-block'),

        // Document Table Elements
        docsTableBody: document.getElementById('docs-table-body'),
        btnRefreshDocs: document.getElementById('btn-refresh-docs'),

        // Ingestion Form Elements
        ingestForm: document.getElementById('ingest-form'),
        dropZone: document.getElementById('drop-zone'),
        ingestFileInput: document.getElementById('ingest-file-input'),
        selectedFileBadge: document.getElementById('selected-file-badge'),
        selectedFileName: document.getElementById('selected-file-name'),
        btnRemoveFile: document.getElementById('btn-remove-file'),
        ingestFileType: document.getElementById('ingest-file-type'),
        ingestStrategy: document.getElementById('ingest-strategy'),
        ingestChunkSize: document.getElementById('ingest-chunk-size'),
        ingestNewAfter: document.getElementById('ingest-new-after'),
        ingestCombineUnder: document.getElementById('ingest-combine-under'),
        ingestDocVersion: document.getElementById('ingest-doc-version'),
        ingestDocId: document.getElementById('ingest-doc-id'),
        ingestKeepTableHtml: document.getElementById('ingest-keep-table-html'),
        ingestVisionModel: document.getElementById('ingest-vision-model'),
        btnSubmitIngest: document.getElementById('btn-submit-ingest'),
        ingestOutputStatus: document.getElementById('ingest-output-status'),

        // Toast Container
        toastContainer: document.getElementById('toast-container')
    };

    // ── Helper: Toast Notifications ───────────────────────────────────
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        const icon = type === 'success' ? 'fa-circle-check' : (type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info');
        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        DOM.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // ── Navigation & Tab Handling ────────────────────────────────────
    DOM.navItems.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            switchTab(targetTab);
        });
    });

    function switchTab(tabId) {
        AppState.currentTab = tabId;
        DOM.navItems.forEach(item => {
            item.classList.toggle('active', item.getAttribute('data-tab') === tabId);
        });
        DOM.tabPanes.forEach(pane => {
            pane.classList.toggle('active', pane.id === tabId);
        });

        // Update topbar titles
        const titles = {
            'tab-search': { title: 'RAG Semantic Search & LLM Playground', sub: 'Perform hybrid semantic search, context building, and LLM text generation' },
            'tab-documents': { title: 'Uploaded Document Registry', sub: 'Inspect stored PostgreSQL document metadata entities and page statistics' },
            'tab-ingest': { title: 'Document Ingestion Studio', sub: 'Parse, chunk, embed, and index enterprise documents into vector store' },
            'tab-api-docs': { title: 'API Endpoint Specifications', sub: 'RESTful API documentation and schema endpoints' }
        };

        if (titles[tabId]) {
            DOM.tabTitle.textContent = titles[tabId].title;
            DOM.tabSubtitle.textContent = titles[tabId].sub;
        }

        if (tabId === 'tab-documents') {
            fetchDocuments();
        }
    }

    // Sub-Tabs in Results Workspace
    DOM.resTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-target');
            DOM.resTabBtns.forEach(b => b.classList.toggle('active', b === btn));
            DOM.resPanes.forEach(p => p.classList.toggle('active', p.id === target));
        });
    });

    // Accordions Toggle
    document.querySelectorAll('.accordion-header').forEach(header => {
        header.addEventListener('click', () => {
            const targetId = header.getAttribute('data-toggle');
            const content = document.getElementById(targetId);
            const isOpen = content.classList.contains('open');

            content.classList.toggle('open', !isOpen);
            header.classList.toggle('active', !isOpen);
        });
    });

    // ── Live Slider Value Listeners ──────────────────────────────────
    DOM.searchTopK.addEventListener('input', (e) => DOM.valTopK.textContent = e.target.value);
    DOM.searchScoreThreshold.addEventListener('input', (e) => DOM.valScoreThreshold.textContent = parseFloat(e.target.value).toFixed(2));
    if (DOM.cbMinScoreThreshold) {
        DOM.cbMinScoreThreshold.addEventListener('input', (e) => DOM.valCbMinScore.textContent = parseFloat(e.target.value).toFixed(2));
    }
    DOM.searchTemperature.addEventListener('input', (e) => DOM.valTemperature.textContent = parseFloat(e.target.value).toFixed(2));

    // ── File Drag & Drop Handling ─────────────────────────────────────
    DOM.dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        DOM.dropZone.classList.add('dragover');
    });

    DOM.dropZone.addEventListener('dragleave', () => {
        DOM.dropZone.classList.remove('dragover');
    });

    DOM.dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        DOM.dropZone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileSelected(e.dataTransfer.files[0]);
        }
    });

    DOM.ingestFileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFileSelected(e.target.files[0]);
        }
    });

    DOM.btnRemoveFile.addEventListener('click', (e) => {
        e.stopPropagation();
        clearSelectedFile();
    });

    function handleFileSelected(file) {
        AppState.selectedIngestFile = file;
        DOM.selectedFileName.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        DOM.selectedFileBadge.classList.remove('hidden');

        // Auto detect file type
        const ext = file.name.split('.').pop().toLowerCase();
        if (['pdf'].includes(ext)) DOM.ingestFileType.value = 'pdf';
        else if (['docx', 'doc'].includes(ext)) DOM.ingestFileType.value = 'docx';
        else if (['md', 'markdown', 'txt'].includes(ext)) DOM.ingestFileType.value = 'md';
        else if (['png', 'jpg', 'jpeg', 'webp'].includes(ext)) DOM.ingestFileType.value = 'image';

        console.log(`[Ingestion Studio] Selected file: '${file.name}', type: ${DOM.ingestFileType.value}`);
    }

    function clearSelectedFile() {
        AppState.selectedIngestFile = null;
        DOM.ingestFileInput.value = '';
        DOM.selectedFileBadge.classList.add('hidden');
        console.log('[Ingestion Studio] File cleared.');
    }

    // ── API Function: Fetch All Documents ────────────────────────────
    async function fetchDocuments() {
        console.log('[API Call] Requesting GET /api/v1/documents...');
        DOM.docsTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-4 text-muted">
                    <i class="fa-solid fa-spinner fa-spin mr-2"></i> Loading document metadata...
                </td>
            </tr>`;

        try {
            const response = await fetch('/api/v1/documents');
            const result = await response.json();

            if (result.success && Array.isArray(result.data)) {
                AppState.documents = result.data;
                DOM.sidebarDocCount.textContent = result.data.length;
                renderDocumentsTable(result.data);
                console.log(`[API Call] Successfully retrieved ${result.data.length} documents.`);
            } else {
                throw new Error(result.message || 'Failed to fetch document registry');
            }
        } catch (err) {
            console.error('[API Error] Error fetching documents:', err);
            showToast(`Error fetching documents: ${err.message}`, 'error');
            DOM.docsTableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-4 text-danger">
                        <i class="fa-solid fa-circle-exclamation mr-2"></i> ${err.message}
                    </td>
                </tr>`;
        }
    }

    function renderDocumentsTable(docs) {
        if (docs.length === 0) {
            DOM.docsTableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-4 text-muted">
                        <i class="fa-solid fa-folder-open mr-2"></i> No documents uploaded yet. Use Ingestion Studio to upload.
                    </td>
                </tr>`;
            return;
        }

        DOM.docsTableBody.innerHTML = docs.map(doc => {
            const created = doc.created_at ? new Date(doc.created_at).toLocaleString() : 'N/A';
            const statusClass = doc.status === 'SUCCESS' ? 'badge-success' : 'badge-primary';
            return `
                <tr>
                    <td>
                        <strong style="color: #fff;">${escapeHtml(doc.file_name)}</strong>
                        <div style="font-size: 0.7rem; color: var(--text-dim); font-family: var(--font-mono);">${doc.document_id}</div>
                    </td>
                    <td><span class="badge badge-outline">${doc.file_type.toUpperCase()}</span></td>
                    <td>v${escapeHtml(doc.doc_version || '1.0.0')}</td>
                    <td><span class="badge ${statusClass}">${escapeHtml(doc.status)}</span></td>
                    <td>${doc.total_pages !== null ? doc.total_pages : 'N/A'}</td>
                    <td><span class="badge badge-primary">${doc.chunk_count} chunks</span></td>
                    <td style="font-size: 0.8rem; color: var(--text-muted);">${created}</td>
                    <td>
                        <button class="btn btn-danger btn-sm btn-delete-doc" data-id="${doc.document_id}" data-name="${escapeHtml(doc.file_name)}">
                            <i class="fa-solid fa-trash"></i> Delete
                        </button>
                    </td>
                </tr>`;
        }).join('');

        // Attach event listener to delete buttons
        document.querySelectorAll('.btn-delete-doc').forEach(btn => {
            btn.addEventListener('click', () => {
                const docId = btn.getAttribute('data-id');
                const docName = btn.getAttribute('data-name');
                deleteDocument(docId, docName);
            });
        });
    }

    // ── API Function: Delete Document ─────────────────────────────────
    async function deleteDocument(docId, docName) {
        if (!confirm(`Are you sure you want to delete document '${docName}'? This will remove all associated database chunks.`)) {
            return;
        }

        console.log(`[API Call] Requesting DELETE /api/v1/documents/${docId}...`);
        try {
            const response = await fetch(`/api/v1/documents/${docId}`, { method: 'DELETE' });
            const result = await response.json();

            if (result.success) {
                showToast(`Document '${docName}' deleted successfully`, 'success');
                fetchDocuments();
            } else {
                throw new Error(result.message || 'Failed to delete document');
            }
        } catch (err) {
            console.error('[API Error] Delete failed:', err);
            showToast(`Failed to delete document: ${err.message}`, 'error');
        }
    }

    // ── API Function: Submit Document Ingestion Pipeline ─────────────
    DOM.ingestForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!AppState.selectedIngestFile) {
            showToast('Please select or drop a file to ingest.', 'error');
            return;
        }

        AppState.isIngesting = true;
        DOM.btnSubmitIngest.disabled = true;
        DOM.btnSubmitIngest.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing Ingestion Pipeline...`;

        DOM.ingestOutputStatus.className = 'ingest-output-container';
        DOM.ingestOutputStatus.innerHTML = `
            <div class="card" style="background: var(--bg-dark);">
                <div class="card-body text-center py-5">
                    <i class="fa-solid fa-gear fa-spin" style="font-size: 2.5rem; color: var(--primary); margin-bottom: 1rem;"></i>
                    <h4>Parsing & Chunking Document...</h4>
                    <p class="text-muted">Extracting text, computing Qdrant embeddings, and saving relational metadata.</p>
                </div>
            </div>`;

        const formData = new FormData();
        formData.append('file', AppState.selectedIngestFile);
        formData.append('file_type', DOM.ingestFileType.value);
        formData.append('chunk_size', DOM.ingestChunkSize.value);
        formData.append('new_after_n_chars', DOM.ingestNewAfter.value);
        formData.append('combine_text_under_n_chars', DOM.ingestCombineUnder.value);
        formData.append('strategy', DOM.ingestStrategy.value);
        formData.append('keep_table_as_html', DOM.ingestKeepTableHtml.checked);
        formData.append('enable_vision_model', DOM.ingestVisionModel.checked);
        formData.append('doc_version', DOM.ingestDocVersion.value || '1.0.0');
        if (DOM.ingestDocId.value.trim()) {
            formData.append('doc_id', DOM.ingestDocId.value.trim());
        }

        console.log('[API Call] Triggering POST /api/v1/ingest for file:', AppState.selectedIngestFile.name);

        try {
            const response = await fetch('/api/v1/ingest', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            console.log('[API Response] Ingestion endpoint response:', result);

            if (result.success && result.data) {
                showToast(`Document '${result.data.file_name}' ingested successfully!`, 'success');
                DOM.ingestOutputStatus.innerHTML = `
                    <div class="card" style="border-left: 4px solid var(--success);">
                        <div class="card-header">
                            <h4 style="color: var(--success);"><i class="fa-solid fa-circle-check"></i> Ingestion Successful</h4>
                        </div>
                        <div class="card-body">
                            <p style="margin-bottom: 1rem;"><strong>Document ID:</strong> <code>${result.data.document_id}</code></p>
                            <div class="metrics-row" style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                                <span class="badge badge-primary">File: ${escapeHtml(result.data.file_name)}</span>
                                <span class="badge badge-outline">Type: ${result.data.file_type}</span>
                                <span class="badge badge-success">Status: ${result.data.status}</span>
                                <span class="badge badge-outline">Total Pages: ${result.data.total_pages || 1}</span>
                            </div>
                            <pre class="code-block">${JSON.stringify(result, null, 2)}</pre>
                        </div>
                    </div>`;
                clearSelectedFile();
                fetchDocuments();
            } else {
                throw new Error(result.message || 'Ingestion failed');
            }
        } catch (err) {
            console.error('[API Error] Ingestion failed:', err);
            showToast(`Ingestion failed: ${err.message}`, 'error');
            DOM.ingestOutputStatus.innerHTML = `
                <div class="card" style="border-left: 4px solid var(--danger);">
                    <div class="card-header">
                        <h4 style="color: var(--danger);"><i class="fa-solid fa-circle-exclamation"></i> Ingestion Failed</h4>
                    </div>
                    <div class="card-body">
                        <p class="text-danger" style="margin-bottom: 1rem;">${escapeHtml(err.message)}</p>
                    </div>
                </div>`;
        } finally {
            AppState.isIngesting = false;
            DOM.btnSubmitIngest.disabled = false;
            DOM.btnSubmitIngest.innerHTML = `<i class="fa-solid fa-microchip"></i> Start Document Ingestion Pipeline`;
        }
    });

    // ── API Function: Execute RAG Retrieval & LLM Generation ──────────
    DOM.searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const queryText = DOM.searchQuery.value.trim();
        if (!queryText) {
            showToast('Please enter a natural language search query.', 'error');
            return;
        }

        AppState.isSearching = true;
        DOM.btnSubmitSearch.disabled = true;
        DOM.btnSubmitSearch.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Retrieving & Generating...`;

        // Reset workspace loading state
        DOM.llmOutputContainer.innerHTML = `
            <div class="card empty-state-card">
                <div class="empty-state">
                    <i class="fa-solid fa-brain fa-spin" style="font-size: 2.5rem; color: var(--primary);"></i>
                    <h3>Synthesizing Answer via LLM</h3>
                    <p>Fetching Qdrant vector matches, assembling context budget, and executing LM Studio generation...</p>
                </div>
            </div>`;

        // Assemble SearchRequest Payload (ALL Parameters covered)
        const payload = {
            query: queryText,
            top_k: parseInt(DOM.searchTopK.value, 10),
            score_threshold: parseFloat(DOM.searchScoreThreshold.value),
            max_context_tokens: parseInt(DOM.cbMaxTokens.value, 10),
            enable_llm_generation: DOM.searchEnableLlm.checked,
            temperature: parseFloat(DOM.searchTemperature.value),
            prompt_name: DOM.searchPromptName.value.trim() || 'rag_qa'
        };

        if (DOM.searchPromptVersion.value.trim()) {
            payload.prompt_version = DOM.searchPromptVersion.value.trim();
        }

        // Additional Prompt Vars
        if (DOM.searchAdditionalVars.value.trim()) {
            try {
                payload.additional_prompt_vars = JSON.parse(DOM.searchAdditionalVars.value.trim());
            } catch (jsonErr) {
                showToast('Invalid JSON format in Additional Prompt Variables.', 'error');
                AppState.isSearching = false;
                DOM.btnSubmitSearch.disabled = false;
                DOM.btnSubmitSearch.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Execute RAG Retrieval & Answer`;
                return;
            }
        }

        // Filters
        if (DOM.searchFilters.value.trim()) {
            try {
                payload.filters = JSON.parse(DOM.searchFilters.value.trim());
            } catch (jsonErr) {
                showToast('Invalid JSON format in Search Metadata Filters.', 'error');
                AppState.isSearching = false;
                DOM.btnSubmitSearch.disabled = false;
                DOM.btnSubmitSearch.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Execute RAG Retrieval & Answer`;
                return;
            }
        }

        // ContextBuilder Overrides
        payload.context_builder = {
            max_context_tokens: parseInt(DOM.cbMaxTokens.value, 10),
            sort_strategy: DOM.cbSortStrategy.value,
            enable_adjacent_expansion: DOM.cbAdjacentExpansion.checked,
            adjacency_window: parseInt(DOM.cbAdjacencyWindow.value, 10),
            enable_chunk_merging: DOM.cbChunkMerging.checked,
            max_merge_gap: parseInt(DOM.cbMergeGap.value, 10),
            include_source_header: DOM.cbSourceHeader.checked,
            include_chunk_separator: DOM.cbChunkSeparator.checked,
            chunk_separator: DOM.cbSeparatorStr.value.replace(/\\n/g, '\n'),
            source_header_template: DOM.cbHeaderTemplate.value,
            min_score_threshold: DOM.cbMinScoreThreshold ? parseFloat(DOM.cbMinScoreThreshold.value) : parseFloat(DOM.searchScoreThreshold.value)
        };

        console.log('[API Call] Sending POST /api/v1/search payload:', payload);

        try {
            const response = await fetch('/api/v1/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            console.log('[API Response] Search endpoint response:', result);

            if (result.success && result.data) {
                renderSearchResults(result.data);
                showToast('Retrieval & Answer Generation completed!', 'success');
            } else {
                throw new Error(result.message || 'Search execution failed');
            }
        } catch (err) {
            console.error('[API Error] Search failed:', err);
            showToast(`Search failed: ${err.message}`, 'error');
            DOM.llmOutputContainer.innerHTML = `
                <div class="card" style="border-left: 4px solid var(--danger);">
                    <div class="card-body text-danger">
                        <i class="fa-solid fa-circle-exclamation mr-2"></i> ${escapeHtml(err.message)}
                    </div>
                </div>`;
        } finally {
            AppState.isSearching = false;
            DOM.btnSubmitSearch.disabled = false;
            DOM.btnSubmitSearch.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Execute RAG Retrieval & Answer`;
        }
    });

    // ── Render Search & LLM Generation Results ────────────────────────
    function renderSearchResults(data) {
        const { search_response, built_context, rendered_prompt, llm_response } = data;

        // 1. LLM Response
        if (llm_response && llm_response.answer) {
            const latency = llm_response.latency_ms ? `${llm_response.latency_ms.toFixed(0)} ms` : 'N/A';
            DOM.llmOutputContainer.innerHTML = `
                <div class="card llm-response-card">
                    <div class="llm-meta-bar">
                        <span><i class="fa-solid fa-robot"></i> Model: <strong>${escapeHtml(llm_response.model_name || 'LM Studio')}</strong></span>
                        <span><i class="fa-solid fa-clock"></i> Latency: <strong>${latency}</strong></span>
                        <span><i class="fa-solid fa-ticket"></i> Tokens: <strong>${llm_response.total_tokens || 'N/A'}</strong></span>
                    </div>
                    <div class="llm-body">
                        ${formatMarkdown(llm_response.answer)}
                    </div>
                </div>`;
        } else {
            DOM.llmOutputContainer.innerHTML = `
                <div class="card">
                    <div class="card-body text-muted text-center py-4">
                        <i class="fa-solid fa-info-circle mr-2"></i> LLM text generation was not requested or prompt was omitted.
                    </div>
                </div>`;
        }

        // 2. Candidate Chunks
        const chunks = (search_response && search_response.results) ? search_response.results : [];
        DOM.chunkCountBadge.textContent = chunks.length;

        if (chunks.length > 0) {
            DOM.chunksOutputContainer.innerHTML = chunks.map((item, idx) => {
                const doc = item.document || {};
                const scorePct = (item.score * 100).toFixed(1);
                return `
                    <div class="chunk-card">
                        <div class="chunk-header">
                            <div class="chunk-doc-title">
                                <i class="fa-solid fa-file-lines text-primary"></i>
                                ${escapeHtml(doc.file_name || 'Unknown Document')}
                            </div>
                            <span class="chunk-score-badge">${scorePct}% Similarity</span>
                        </div>
                        <div class="chunk-body">${escapeHtml(doc.content || '')}</div>
                        <div class="chunk-footer">
                            <span>Page: ${doc.page_number !== undefined ? doc.page_number : 'N/A'}</span>
                            <span>Chunk Hash: ${doc.chunk_hash ? doc.chunk_hash.substring(0, 12) + '...' : 'N/A'}</span>
                            <span>Type: ${doc.file_type || 'pdf'}</span>
                        </div>
                    </div>`;
            }).join('');
        } else {
            DOM.chunksOutputContainer.innerHTML = `
                <div class="card empty-state-card">
                    <div class="empty-state">
                        <i class="fa-solid fa-circle-question"></i>
                        <h3>No Candidate Chunks Matched</h3>
                        <p>Try lowering the similarity threshold slider or increasing Top-K.</p>
                    </div>
                </div>`;
        }

        // 3. Assembled Context
        if (built_context) {
            DOM.ctxTokenCount.textContent = built_context.token_count || 0;
            DOM.ctxChunkCount.textContent = built_context.chunk_count || 0;

            const stats = built_context.pipeline_stats || {};
            let statsHtml = '';
            if (stats.below_threshold_dropped && stats.below_threshold_dropped > 0) {
                statsHtml = `
                    <div style="background: rgba(239, 68, 68, 0.15); border-left: 3px solid #ef4444; padding: 0.75rem 1rem; border-radius: 4px; margin-bottom: 1rem; color: #fca5a5; font-size: 0.85rem;">
                        <i class="fa-solid fa-triangle-exclamation mr-1"></i>
                        <strong>Notice:</strong> ${stats.below_threshold_dropped} retrieved candidate chunk(s) were dropped because their similarity scores were below the similarity threshold slider setting. Try lowering the threshold slider to 0.10.
                    </div>`;
            }

            const statsBar = `
                <div style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-dim); background: rgba(255,255,255,0.03); padding: 0.5rem 0.75rem; border-radius: 4px; margin-bottom: 1rem; display: flex; gap: 1rem; flex-wrap: wrap;">
                    <span>Input: <strong>${stats.input_count || 0}</strong></span>
                    <span>Dropped: <strong style="color: ${stats.below_threshold_dropped ? '#ef4444' : 'inherit'}">${stats.below_threshold_dropped || 0}</strong></span>
                    <span>After Dedup: <strong>${stats.after_dedup || 0}</strong></span>
                    <span>After Merge: <strong>${stats.after_merge || 0}</strong></span>
                    <span>Pipeline Time: <strong>${stats.total_pipeline_ms || 0} ms</strong></span>
                </div>`;

            const contextText = built_context.context_str || '(No context assembled — all candidate chunks dropped by pipeline score filter)';
            DOM.contextTextBlock.parentElement.innerHTML = statsHtml + statsBar + `<pre class="code-block" id="context-text-block">${escapeHtml(contextText)}</pre>`;
        }

        // 4. Provisioned Prompt
        if (rendered_prompt) {
            DOM.renderedPromptBadge.textContent = `${rendered_prompt.prompt_name} (v${rendered_prompt.version})`;
            let fullPrompt = '';
            if (rendered_prompt.system_prompt) {
                fullPrompt += `=== SYSTEM PROMPT ===\n${rendered_prompt.system_prompt}\n\n`;
            }
            if (rendered_prompt.user_prompt) {
                fullPrompt += `=== USER PROMPT ===\n${rendered_prompt.user_prompt}`;
            }
            if (!fullPrompt && rendered_prompt.prompt_text) {
                fullPrompt = rendered_prompt.prompt_text;
            }
            DOM.promptTextBlock.textContent = fullPrompt || 'No prompt content rendered.';
        } else {
            DOM.renderedPromptBadge.textContent = 'None';
            DOM.promptTextBlock.textContent = 'No versioned prompt was provisioned.';
        }
    }

    // ── Simple Markdown Formatter Helper ─────────────────────────────
    function formatMarkdown(text) {
        if (!text) return '';
        let html = escapeHtml(text);

        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Italics
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Inline Code
        html = html.replace(/`(.*?)`/g, '<code>$1</code>');
        // Code Blocks
        html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        // Newlines to paragraph/br
        return html.split('\n\n').map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
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

    // ── Global Refresh Button Listener ──────────────────────────────
    DOM.btnRefreshAll.addEventListener('click', () => {
        showToast('Refreshing application state...', 'info');
        fetchDocuments();
    });

    DOM.btnRefreshDocs.addEventListener('click', () => {
        fetchDocuments();
    });

    // Initial load
    fetchDocuments();
});
