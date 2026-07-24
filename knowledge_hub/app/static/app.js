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

        // Retrieval Mode Controls
        searchRetrievalMode: document.getElementById('search-retrieval-mode'),
        hybridWeightsPanel: document.getElementById('hybrid-weights-panel'),
        searchDenseWeight: document.getElementById('search-dense-weight'),
        searchBm25Weight: document.getElementById('search-bm25-weight'),
        valDenseWeight: document.getElementById('val-dense-weight'),
        valBm25Weight: document.getElementById('val-bm25-weight'),
        bm25StatusIndicator: document.getElementById('bm25-status-indicator'),
        bm25StatusText: document.getElementById('bm25-status-text'),
        sidebarBm25Status: document.getElementById('sidebar-bm25-status'),

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
        toastContainer: document.getElementById('toast-container'),

        // RAG Evaluation Form & Views
        evalForm: document.getElementById('eval-form'),
        evalRunName: document.getElementById('eval-run-name'),
        evalType: document.getElementById('eval-type'),
        evalDatasetEditor: document.getElementById('eval-dataset-editor'),
        btnResetEvalJson: document.getElementById('btn-reset-eval-json'),
        btnSubmitEval: document.getElementById('btn-submit-eval'),
        btnRefreshEvals: document.getElementById('btn-refresh-evals'),
        evalHistoryList: document.getElementById('eval-history-list'),
        evalDetailedReport: document.getElementById('eval-detailed-report'),
        btnBackToEvalHistory: document.getElementById('btn-back-to-eval-history'),
        evalsTableBody: document.getElementById('evals-table-body'),
        evalDetailsTableBody: document.getElementById('eval-details-body'),

        // Report detail summaries
        reportRunTitle: document.getElementById('report-run-title'),
        reportRunMeta: document.getElementById('report-run-meta'),
        reportRunDate: document.getElementById('report-run-date'),
        valAvgFaithfulness: document.getElementById('val-avg-faithfulness'),
        valAvgRelevance: document.getElementById('val-avg-relevance'),
        valAvgRecall: document.getElementById('val-avg-recall'),
        valAvgPrecision: document.getElementById('val-avg-precision'),
        evalSchemaInfo: document.getElementById('eval-schema-info'),
        evalRetrievalMode: document.getElementById('eval-retrieval-mode'),
        evalRetrievalModeWrapper: document.getElementById('eval-retrieval-mode-wrapper')
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
            'tab-evaluation': { title: 'RAG Evaluation Center', sub: 'Run RAGAS benchmarks and review regression reports' },
            'tab-api-docs': { title: 'API Endpoint Specifications', sub: 'RESTful API documentation and schema endpoints' }
        };

        if (titles[tabId]) {
            DOM.tabTitle.textContent = titles[tabId].title;
            DOM.tabSubtitle.textContent = titles[tabId].sub;
        }

        if (tabId === 'tab-documents') {
            fetchDocuments();
        } else if (tabId === 'tab-evaluation') {
            fetchEvaluationHistory();
            initEvalForm();
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

    // Retrieval Mode Interactions
    if (DOM.searchRetrievalMode) {
        DOM.searchRetrievalMode.addEventListener('change', (e) => {
            const isHybrid = e.target.value === 'hybrid';
            if (DOM.hybridWeightsPanel) {
                DOM.hybridWeightsPanel.style.display = isHybrid ? 'block' : 'none';
            }
            console.log(`[Retrieval Mode] Switched to: ${e.target.value}`);
        });
    }

    if (DOM.searchDenseWeight) {
        DOM.searchDenseWeight.addEventListener('input', (e) => {
            const denseVal = parseFloat(e.target.value);
            const bm25Val = Math.round((1.0 - denseVal) * 100) / 100;
            DOM.valDenseWeight.textContent = denseVal.toFixed(2);
            DOM.searchBm25Weight.value = bm25Val;
            DOM.valBm25Weight.textContent = bm25Val.toFixed(2);
        });
    }

    if (DOM.searchBm25Weight) {
        DOM.searchBm25Weight.addEventListener('input', (e) => {
            const bm25Val = parseFloat(e.target.value);
            const denseVal = Math.round((1.0 - bm25Val) * 100) / 100;
            DOM.valBm25Weight.textContent = bm25Val.toFixed(2);
            DOM.searchDenseWeight.value = denseVal;
            DOM.valDenseWeight.textContent = denseVal.toFixed(2);
        });
    }

    // Fetch BM25 index status on page load
    async function fetchBm25Status() {
        try {
            const response = await fetch('/api/v1/bm25/status');
            const result = await response.json();
            if (result.success && result.data) {
                const { is_ready, document_count } = result.data;
                if (DOM.bm25StatusIndicator) {
                    DOM.bm25StatusIndicator.className = `status-indicator ${is_ready ? 'online' : 'offline'}`;
                }
                if (DOM.bm25StatusText) {
                    DOM.bm25StatusText.textContent = is_ready
                        ? `BM25 Index: Ready (${document_count} docs)`
                        : 'BM25 Index: Not Built';
                }
                if (DOM.sidebarBm25Status) {
                    DOM.sidebarBm25Status.textContent = is_ready
                        ? `Ready (${document_count})`
                        : 'Not Built';
                    DOM.sidebarBm25Status.style.color = is_ready ? '#4ade80' : '#ef4444';
                }
            }
        } catch (err) {
            console.warn('[BM25 Status] Failed to fetch BM25 index status:', err.message);
            if (DOM.bm25StatusText) {
                DOM.bm25StatusText.textContent = 'BM25 Index: Unavailable';
            }
        }
    }
    fetchBm25Status();

    // Rebuild BM25 index button handler
    const btnRebuildBm25 = document.getElementById('btn-rebuild-bm25');
    if (btnRebuildBm25) {
        btnRebuildBm25.addEventListener('click', async () => {
            btnRebuildBm25.disabled = true;
            const originalHtml = btnRebuildBm25.innerHTML;
            btnRebuildBm25.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Rebuilding...';
            showToast('Rebuilding BM25 keyword index from Qdrant payloads...', 'info');
            try {
                const response = await fetch('/api/v1/bm25/rebuild', { method: 'POST' });
                const result = await response.json();
                if (result.success && result.data) {
                    showToast(`BM25 Index rebuilt successfully! (${result.data.document_count} docs)`, 'success');
                    await fetchBm25Status();
                } else {
                    throw new Error(result.message || 'Failed to rebuild BM25 index');
                }
            } catch (err) {
                console.error('[BM25 Rebuild] Failed:', err);
                showToast(`Rebuild failed: ${err.message}`, 'error');
            } finally {
                btnRebuildBm25.disabled = false;
                btnRebuildBm25.innerHTML = originalHtml;
            }
        });
    }

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
        const retrievalMode = DOM.searchRetrievalMode ? DOM.searchRetrievalMode.value : 'dense';
        const payload = {
            query: queryText,
            top_k: parseInt(DOM.searchTopK.value, 10),
            score_threshold: parseFloat(DOM.searchScoreThreshold.value),
            max_context_tokens: parseInt(DOM.cbMaxTokens.value, 10),
            enable_llm_generation: DOM.searchEnableLlm.checked,
            temperature: parseFloat(DOM.searchTemperature.value),
            prompt_name: DOM.searchPromptName.value.trim() || 'rag_qa',
            retrieval_mode: retrievalMode,
            dense_weight: DOM.searchDenseWeight ? parseFloat(DOM.searchDenseWeight.value) : 0.7,
            bm25_weight: DOM.searchBm25Weight ? parseFloat(DOM.searchBm25Weight.value) : 0.3
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
                const rawScore = typeof item.score === 'number' ? item.score.toFixed(4) : 'N/A';
                const docId = doc.document_id || 'N/A';
                const chunkId = doc.chunk_id || 'N/A';
                const docVersion = doc.doc_version || '1.0.0';
                const pageNum = doc.page_number !== undefined && doc.page_number !== null ? doc.page_number : 'N/A';
                const chunkIdx = doc.chuk_index !== undefined ? doc.chuk_index : (doc.chunk_index !== undefined ? doc.chunk_index : 'N/A');
                const sourcePath = doc.source || 'N/A';
                const fileType = doc.file_type || (doc.file_name ? doc.file_name.split('.').pop().toUpperCase() : 'PDF');

                return `
                    <div class="chunk-card">
                        <div class="chunk-header">
                            <div class="chunk-doc-title">
                                <i class="fa-solid fa-file-lines text-primary"></i>
                                ${escapeHtml(doc.file_name || 'Unknown Document')}
                                <span class="badge badge-outline" style="margin-left: 0.5rem; font-size: 0.7rem;">v${escapeHtml(docVersion)}</span>
                            </div>
                            <div style="display: flex; gap: 0.5rem; align-items: center;">
                                <span class="badge badge-primary" style="font-size: 0.75rem;">Score: ${rawScore}</span>
                                <span class="chunk-score-badge">${scorePct}% Similarity</span>
                            </div>
                        </div>

                        <!-- All Available Metadata Pills -->
                        <div class="chunk-metadata-pills" style="display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.75rem; font-size: 0.75rem; font-family: var(--font-mono);">
                            <span class="meta-pill" style="background: rgba(255,255,255,0.04); padding: 0.25rem 0.55rem; border-radius: 4px; border: 1px solid var(--border-color);" title="Document ID">
                                <i class="fa-solid fa-id-card text-muted mr-1"></i> Doc ID: <strong style="color: #60a5fa;">${escapeHtml(docId)}</strong>
                            </span>
                            <span class="meta-pill" style="background: rgba(255,255,255,0.04); padding: 0.25rem 0.55rem; border-radius: 4px; border: 1px solid var(--border-color);" title="Chunk ID">
                                <i class="fa-solid fa-fingerprint text-muted mr-1"></i> Chunk ID: <strong style="color: #a78bfa;">${escapeHtml(chunkId)}</strong>
                            </span>
                            <span class="meta-pill" style="background: rgba(255,255,255,0.04); padding: 0.25rem 0.55rem; border-radius: 4px; border: 1px solid var(--border-color);" title="Page Number">
                                <i class="fa-solid fa-book-open text-muted mr-1"></i> Page: <strong style="color: #34d399;">${pageNum}</strong>
                            </span>
                            <span class="meta-pill" style="background: rgba(255,255,255,0.04); padding: 0.25rem 0.55rem; border-radius: 4px; border: 1px solid var(--border-color);" title="Chunk Index">
                                <i class="fa-solid fa-hashtag text-muted mr-1"></i> Chunk Index: <strong style="color: #fbbf24;">${chunkIdx}</strong>
                            </span>
                            <span class="meta-pill" style="background: rgba(255,255,255,0.04); padding: 0.25rem 0.55rem; border-radius: 4px; border: 1px solid var(--border-color);" title="Document Version">
                                <i class="fa-solid fa-code-branch text-muted mr-1"></i> Version: <strong style="color: #f472b6;">v${escapeHtml(docVersion)}</strong>
                            </span>
                        </div>

                        <div class="chunk-body">${escapeHtml(doc.content || '')}</div>

                        <div class="chunk-footer" style="margin-top: 0.75rem; font-size: 0.75rem; color: var(--text-dim); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
                            <span title="${escapeHtml(sourcePath)}">
                                <i class="fa-solid fa-folder-tree mr-1"></i> Source: <code style="font-size: 0.7rem; color: #cbd5e1; background: rgba(0,0,0,0.3); padding: 0.1rem 0.4rem; border-radius: 3px;">${escapeHtml(sourcePath)}</code>
                            </span>
                            <span>
                                <i class="fa-solid fa-file-code mr-1"></i> Type: <span class="badge badge-outline" style="font-size: 0.65rem;">${escapeHtml(fileType)}</span>
                            </span>
                        </div>
                    </div>`;
            }).join('');
        }
        else {
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

            const retrievalModeBadge = stats.retrieval_mode 
                ? `<span>Mode: <strong style="color: ${stats.retrieval_mode === 'hybrid' ? '#a78bfa' : (stats.retrieval_mode === 'bm25' ? '#fbbf24' : '#60a5fa')}">${stats.retrieval_mode.toUpperCase()}</strong></span>` 
                : '';
            
            // Generate extra retrieval metrics for hybrid search
            let hybridStatsHtml = '';
            if (stats.retrieval_mode === 'hybrid') {
                hybridStatsHtml = `
                    <span>Dense Candidates: <strong>${stats.dense_count !== undefined ? stats.dense_count : 'N/A'}</strong></span>
                    <span>BM25 Candidates: <strong>${stats.bm25_count !== undefined ? stats.bm25_count : 'N/A'}</strong></span>
                    <span>Fused Candidates: <strong>${stats.fused_count !== undefined ? stats.fused_count : 'N/A'}</strong></span>
                `;
            } else if (stats.retrieval_mode === 'bm25') {
                hybridStatsHtml = `
                    <span>BM25 Candidates: <strong>${stats.input_count || 0}</strong></span>
                `;
            }

            const statsBar = `
                <div style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-dim); background: rgba(255,255,255,0.03); padding: 0.5rem 0.75rem; border-radius: 4px; margin-bottom: 1rem; display: flex; gap: 1rem; flex-wrap: wrap;">
                    ${retrievalModeBadge}
                    ${hybridStatsHtml}
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

    // ── RAG Evaluation Center Logic ───────────────────────────────────
    const DEFAULT_EVAL_JSON = {
        static: [
            {
                "question": "What is the primary benefit of Multi-Head Attention?",
                "contexts": [
                    "Multi-head attention projects queries, keys, and values into multiple representation subspaces, executing scaled dot-product attention in parallel."
                ],
                "answer": "Multi-head attention allows the model to process sequence values in parallel across distinct linear projections.",
                "ground_truth": "Multi-head attention projects Queries, Keys, and Values h times into different subspaces, executing scaled dot-product calculations in parallel."
            }
        ],
        pipeline: [
            {
                "question": "What is the primary benefit of Multi-Head Attention?",
                "ground_truth": "It projects queries, keys, and values to different subspaces, letting the network focus on sequence info at multiple positions in parallel."
            },
            {
                "question": "What embedding dimensions are configured for Local LM Studio?",
                "ground_truth": "It uses nomic-embed-text embedding model configured with a dimension length of 384."
            }
        ]
    };

    function initEvalForm() {
        if (!DOM.evalDatasetEditor.value) {
            updateEvalJsonTemplate();
        } else {
            // Keep visibility in sync even if editor already has value
            const type = DOM.evalType.value;
            if (DOM.evalRetrievalModeWrapper) {
                DOM.evalRetrievalModeWrapper.style.display = (type === 'pipeline') ? 'block' : 'none';
            }
        }
    }

    function updateEvalJsonTemplate() {
        const type = DOM.evalType.value;
        const defaultData = DEFAULT_EVAL_JSON[type];
        DOM.evalDatasetEditor.value = JSON.stringify(defaultData, null, 4);
        
        if (type === 'pipeline') {
            if (DOM.evalRetrievalModeWrapper) DOM.evalRetrievalModeWrapper.style.display = 'block';
            DOM.evalSchemaInfo.style.background = 'rgba(59, 130, 246, 0.08)';
            DOM.evalSchemaInfo.style.borderLeft = '3px solid var(--primary)';
            DOM.evalSchemaInfo.style.color = '#93c5fd';
            DOM.evalSchemaInfo.innerHTML = `
                <i class="fa-solid fa-circle-info" style="margin-right: 0.5rem;"></i>
                <strong>Dynamic RAG Mode:</strong> Enter questions and ground truths. The active pipeline will automatically search Qdrant and generate answers on-the-fly.
                <ul style="margin-left: 1.25rem; margin-top: 0.25rem; font-size: 0.75rem; list-style-type: disc;">
                    <li><code>question</code> (Required): Query text to search.</li>
                    <li><code>ground_truth</code> (Required): Baseline reference answer.</li>
                </ul>`;
        } else {
            if (DOM.evalRetrievalModeWrapper) DOM.evalRetrievalModeWrapper.style.display = 'none';
            DOM.evalSchemaInfo.style.background = 'rgba(16, 185, 129, 0.08)';
            DOM.evalSchemaInfo.style.borderLeft = '3px solid var(--success)';
            DOM.evalSchemaInfo.style.color = '#a7f3d0';
            DOM.evalSchemaInfo.innerHTML = `
                <i class="fa-solid fa-list-check" style="margin-right: 0.5rem;"></i>
                <strong>Static Logs Mode:</strong> Paste pre-computed logs. No live search or LLM calls are made during evaluation.
                <ul style="margin-left: 1.25rem; margin-top: 0.25rem; font-size: 0.75rem; list-style-type: disc;">
                    <li><code>question</code> (Required) | <code>ground_truth</code> (Required)</li>
                    <li><code>contexts</code> (Required): List of text chunks retrieved.</li>
                    <li><code>answer</code> (Required): LLM answer text to evaluate.</li>
                </ul>`;
        }
        console.log(`[Evaluation Center] Pre-filled JSON editor template for type: ${type}`);
    }

    DOM.evalType.addEventListener('change', () => {
        updateEvalJsonTemplate();
    });

    DOM.btnResetEvalJson.addEventListener('click', () => {
        updateEvalJsonTemplate();
        showToast('JSON dataset editor reset to template.', 'info');
    });

    // ── API Function: Submit RAGAS Evaluation ────────────────────────
    DOM.evalForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const runName = DOM.evalRunName.value.trim();
        const evalType = DOM.evalType.value;
        const editorText = DOM.evalDatasetEditor.value.trim();

        if (!runName) {
            showToast('Please provide a Run Description / Name.', 'error');
            return;
        }

        let datasetParsed;
        try {
            datasetParsed = JSON.parse(editorText);
            if (!Array.isArray(datasetParsed)) {
                throw new Error("JSON root element must be a list / array.");
            }
        } catch (jsonErr) {
            showToast(`JSON parsing failed: ${jsonErr.message}`, 'error');
            return;
        }

        DOM.btnSubmitEval.disabled = true;
        DOM.btnSubmitEval.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Running RAGAS Evaluation...`;
        showToast("RAGAS Evaluation triggered. This will take a moment depending on dataset size...", "info");

        // Prepare endpoint and payload
        const isPipeline = evalType === 'pipeline';
        const url = isPipeline ? '/api/v1/evaluate/pipeline' : '/api/v1/evaluate/static';
        const payload = {
            run_name: runName
        };

        if (isPipeline) {
            payload.test_questions = datasetParsed;
            payload.retrieval_mode = DOM.evalRetrievalMode ? DOM.evalRetrievalMode.value : 'dense';
            payload.dense_weight = DOM.searchDenseWeight ? parseFloat(DOM.searchDenseWeight.value) : 0.7;
            payload.bm25_weight = DOM.searchBm25Weight ? parseFloat(DOM.searchBm25Weight.value) : 0.3;
        } else {
            payload.test_set = datasetParsed;
        }

        console.log(`[API Call] Triggering POST ${url} payload:`, payload);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            console.log('[API Response] Evaluation response:', result);

            if (result.success && result.data) {
                showToast(`Evaluation Run '${runName}' completed successfully!`, 'success');
                DOM.evalRunName.value = '';
                fetchEvaluationHistory();
                viewEvaluationReport(result.data.run_id);
            } else {
                throw new Error(result.message || 'Evaluation run failed.');
            }
        } catch (err) {
            console.error('[API Error] Evaluation failed:', err);
            showToast(`Evaluation failed: ${err.message}`, 'error');
        } finally {
            DOM.btnSubmitEval.disabled = false;
            DOM.btnSubmitEval.innerHTML = `<i class="fa-solid fa-play"></i> Trigger Evaluation Suite`;
        }
    });

    // ── API Function: Fetch Evaluation Runs History ─────────────────
    async function fetchEvaluationHistory() {
        console.log('[API Call] Requesting GET /api/v1/evaluate/runs...');
        DOM.evalsTableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4 text-muted">
                    <i class="fa-solid fa-spinner fa-spin mr-2"></i> Loading historical runs...
                </td>
            </tr>`;

        try {
            const response = await fetch('/api/v1/evaluate/runs');
            const result = await response.json();

            if (result.success && Array.isArray(result.data)) {
                renderEvaluationHistoryTable(result.data);
                console.log(`[API Call] Successfully retrieved ${result.data.length} evaluation runs.`);
            } else {
                throw new Error(result.message || 'Failed to fetch evaluation history');
            }
        } catch (err) {
            console.error('[API Error] Error fetching evaluation history:', err);
            showToast(`Error fetching history: ${err.message}`, 'error');
            DOM.evalsTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4 text-danger">
                        <i class="fa-solid fa-circle-exclamation mr-2"></i> ${err.message}
                    </td>
                </tr>`;
        }
    }

    function renderEvaluationHistoryTable(runs) {
        if (runs.length === 0) {
            DOM.evalsTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4 text-muted">
                        <i class="fa-solid fa-square-poll-vertical mr-2"></i> No evaluation runs saved yet. Trigger one on the left.
                    </td>
                </tr>`;
            return;
        }

        DOM.evalsTableBody.innerHTML = runs.map(run => {
            const created = run.created_at ? new Date(run.created_at).toLocaleString() : 'N/A';
            const f = typeof run.avg_faithfulness === 'number' ? run.avg_faithfulness.toFixed(4) : 'N/A';
            const rel = typeof run.avg_answer_relevance === 'number' ? run.avg_answer_relevance.toFixed(4) : 'N/A';
            const rec = typeof run.avg_context_recall === 'number' ? run.avg_context_recall.toFixed(4) : 'N/A';
            const prec = typeof run.avg_context_precision === 'number' ? run.avg_context_precision.toFixed(4) : 'N/A';

            return `
                <tr class="eval-run-row" data-id="${run.run_id}" style="cursor: pointer;">
                    <td>
                        <strong style="color: #60a5fa;"><i class="fa-solid fa-file-invoice"></i> ${escapeHtml(run.run_name || 'Evaluation Run')}</strong>
                        <div style="font-size: 0.7rem; color: var(--text-dim); font-family: var(--font-mono);">${run.run_id}</div>
                    </td>
                    <td>
                        <span class="badge badge-outline">${escapeHtml(run.provider.toUpperCase())}</span>
                        <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 0.15rem;">${escapeHtml(run.eval_model)}</div>
                    </td>
                    <td class="${getScoreColorClass(run.avg_faithfulness)}">${f}</td>
                    <td class="${getScoreColorClass(run.avg_answer_relevance)}">${rel}</td>
                    <td class="${getScoreColorClass(run.avg_context_recall)}">${rec}</td>
                    <td class="${getScoreColorClass(run.avg_context_precision)}">${prec}</td>
                    <td style="font-size: 0.8rem; color: var(--text-muted);">${created}</td>
                </tr>`;
        }).join('');

        // Attach click handlers to open detailed reports
        document.querySelectorAll('.eval-run-row').forEach(row => {
            row.addEventListener('click', () => {
                const runId = row.getAttribute('data-id');
                viewEvaluationReport(runId);
            });
        });
    }

    // Helper: score coloring based on standard thresholds
    function getScoreColorClass(score) {
        if (score === null || score === undefined || typeof score !== 'number') return '';
        if (score >= 0.8) return 'score-high';
        if (score >= 0.5) return 'score-med';
        return 'score-low';
    }

    // ── API Function: View Detailed Evaluation Report ────────────────
    async function viewEvaluationReport(runId) {
        console.log(`[API Call] Requesting GET /api/v1/evaluate/runs/${runId}...`);
        
        // Hide history view, show detailed report with loaders
        DOM.evalHistoryList.classList.add('hidden');
        DOM.evalDetailedReport.classList.remove('hidden');
        
        DOM.reportRunTitle.textContent = "Loading run details...";
        DOM.reportRunMeta.textContent = "";
        DOM.reportRunDate.textContent = "";
        DOM.valAvgFaithfulness.textContent = "0.0000";
        DOM.valAvgRelevance.textContent = "0.0000";
        DOM.valAvgRecall.textContent = "0.0000";
        DOM.valAvgPrecision.textContent = "0.0000";
        
        DOM.evalDetailsTableBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4 text-muted">
                    <i class="fa-solid fa-spinner fa-spin mr-2"></i> Fetching individual query details...
                </td>
            </tr>`;

        try {
            const response = await fetch(`/api/v1/evaluate/runs/${runId}`);
            const result = await response.json();

            if (result.success && result.data) {
                const run = result.data;
                const created = run.created_at ? new Date(run.created_at).toLocaleString() : 'N/A';
                
                // Populate run details
                DOM.reportRunTitle.innerHTML = `<i class="fa-solid fa-square-poll-vertical text-primary"></i> ${escapeHtml(run.run_name || 'Evaluation Report')}`;
                DOM.reportRunMeta.textContent = `Provider: ${run.provider.toUpperCase()} | Model: ${run.eval_model}`;
                DOM.reportRunDate.textContent = `Run Time: ${created}`;

                // Populate aggregates (with score coloring classes)
                DOM.valAvgFaithfulness.textContent = formatScoreValue(run.avg_faithfulness);
                DOM.valAvgFaithfulness.className = `metric-value mt-1 ${getScoreColorClass(run.avg_faithfulness)}`;
                
                DOM.valAvgRelevance.textContent = formatScoreValue(run.avg_answer_relevance);
                DOM.valAvgRelevance.className = `metric-value mt-1 ${getScoreColorClass(run.avg_answer_relevance)}`;
                
                DOM.valAvgRecall.textContent = formatScoreValue(run.avg_context_recall);
                DOM.valAvgRecall.className = `metric-value mt-1 ${getScoreColorClass(run.avg_context_recall)}`;
                
                DOM.valAvgPrecision.textContent = formatScoreValue(run.avg_context_precision);
                DOM.valAvgPrecision.className = `metric-value mt-1 ${getScoreColorClass(run.avg_context_precision)}`;

                // Render individual query scores
                renderDetailedResultsTable(run.individual_results || []);
            } else {
                throw new Error(result.message || 'Failed to fetch evaluation details');
            }
        } catch (err) {
            console.error('[API Error] Failed to fetch run details:', err);
            showToast(`Failed to load details: ${err.message}`, 'error');
            DOM.evalDetailsTableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-4 text-danger">
                        <i class="fa-solid fa-circle-exclamation mr-2"></i> ${err.message}
                    </td>
                </tr>`;
        }
    }

    function formatScoreValue(val) {
        return typeof val === 'number' ? val.toFixed(4) : 'N/A';
    }

    function renderDetailedResultsTable(results) {
        if (results.length === 0) {
            DOM.evalDetailsTableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-4 text-muted">
                        No queries found in this evaluation report.
                    </td>
                </tr>`;
            return;
        }

        let html = '';
        results.forEach((res, idx) => {
            const f = formatScoreValue(res.faithfulness);
            const rel = formatScoreValue(res.answer_relevance);
            const rec = formatScoreValue(res.context_recall);
            const prec = formatScoreValue(res.context_precision);

            // Double rows: Primary row for metrics, expandable row for question details
            html += `
                <tr class="eval-details-row-expandable" data-target="expand-row-${idx}">
                    <td>
                        <strong style="color: #fff;"><i class="fa-solid fa-angle-right expand-arrow mr-2"></i> ${escapeHtml(res.question)}</strong>
                    </td>
                    <td class="${getScoreColorClass(res.faithfulness)}">${f}</td>
                    <td class="${getScoreColorClass(res.answer_relevance)}">${rel}</td>
                    <td class="${getScoreColorClass(res.context_recall)}">${rec}</td>
                    <td class="${getScoreColorClass(res.context_precision)}">${prec}</td>
                </tr>
                <tr id="expand-row-${idx}" class="eval-expanded-row hidden">
                    <td colspan="5" class="eval-details-panel">
                        <div class="eval-details-grid">
                            <!-- Left: Ground Truth vs Answer -->
                            <div class="eval-details-section">
                                <h5><i class="fa-solid fa-clipboard-check text-success"></i> Synthesis Assessment</h5>
                                <div class="mb-2">
                                    <strong style="color: #3b82f6;">Expected Ground Truth:</strong>
                                    <div class="eval-details-content text-muted">${escapeHtml(res.ground_truth || 'None provided')}</div>
                                </div>
                                <div>
                                    <strong style="color: #10b981;">Generated Answer:</strong>
                                    <div class="eval-details-content">${escapeHtml(res.answer)}</div>
                                </div>
                            </div>
                            
                            <!-- Right: Retrieved Chunks -->
                            <div class="eval-details-section">
                                <h5><i class="fa-solid fa-database text-primary"></i> Retrieved Context Chunks</h5>
                                <div class="eval-details-content">
                                    ${res.contexts && res.contexts.length > 0 ? 
                                        res.contexts.map((ctx, cIdx) => `
                                            <div style="border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; margin-bottom: 0.5rem;">
                                                <strong style="color: var(--primary);">Chunk #${cIdx + 1}:</strong>
                                                <p style="margin-top: 0.25rem; font-family: var(--font-mono); font-size: 0.75rem;">${escapeHtml(ctx)}</p>
                                            </div>`).join('')
                                        : 'No context retrieved for this query.'
                                    }
                                </div>
                            </div>
                        </div>
                    </td>
                </tr>`;
        });

        DOM.evalDetailsTableBody.innerHTML = html;

        // Attach expand events
        document.querySelectorAll('.eval-details-row-expandable').forEach(row => {
            row.addEventListener('click', () => {
                const targetId = row.getAttribute('data-target');
                const expandRow = document.getElementById(targetId);
                const arrow = row.querySelector('.expand-arrow');
                const isHidden = expandRow.classList.contains('hidden');

                // Toggle visibility
                expandRow.classList.toggle('hidden', !isHidden);
                row.classList.toggle('eval-expanded-row', isHidden);

                // Rotate arrow icon
                if (arrow) {
                    if (isHidden) {
                        arrow.className = "fa-solid fa-angle-down expand-arrow mr-2";
                    } else {
                        arrow.className = "fa-solid fa-angle-right expand-arrow mr-2";
                    }
                }
            });
        });
    }

    DOM.btnBackToEvalHistory.addEventListener('click', () => {
        DOM.evalDetailedReport.classList.add('hidden');
        DOM.evalHistoryList.classList.remove('hidden');
    });

    DOM.btnRefreshEvals.addEventListener('click', () => {
        fetchEvaluationHistory();
    });

    // ── Global Refresh Button Listener ──────────────────────────────
    DOM.btnRefreshAll.addEventListener('click', () => {
        showToast('Refreshing application state...', 'info');
        fetchDocuments();
        if (AppState.currentTab === 'tab-evaluation') {
            fetchEvaluationHistory();
        }
    });

    DOM.btnRefreshDocs.addEventListener('click', () => {
        fetchDocuments();
    });

    // Initial load
    fetchDocuments();
});
