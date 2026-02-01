/**
 * DataAnalysis Pro - Frontend Logic
 * Version: 2.1 - Variable Selection Modal
 */

// ===== State Management =====
const state = {
    dataId: null,
    columns: [],
    columnTypes: {}, // { colName: 'numeric' | 'categorical' }
    analysisType: 'anova', // 'anova', 'pca', 'cluster'

    // ANOVA / Cluster Config
    factors: [], // Also used as Cluster Labels (optional)
    targets: [], // Also used as Cluster Features (numeric)

    // PCA Config
    pcaSelectedVars: [],
    pcaGroupVar: '',
    targetConfigs: {}, // { col: { type, a, b } }

    // Cluster Config
    clusterParams: {
        k: 3,
        algorithm: 'kmeans',
        useMeans: false
    },

    // Heatmap Config
    heatmapX: [],
    heatmapY: [],

    results: null
};

// Temp state for modal operations
let tempState = {
    factors: [],
    targets: [],
    pcaSelectedVars: [],
    pcaGroupVars: '',
    heatmapX: [],
    heatmapY: []
};

// ===== DOM Elements =====
const dom = {
    // Upload & Data
    dropOverlay: document.getElementById('drop-overlay'),
    uploadPanel: document.getElementById('upload-panel'),
    dataInfoPanel: document.getElementById('data-info-panel'),
    fileInput: document.getElementById('file-input'),
    uploadBtn: document.getElementById('upload-btn'),
    fileName: document.getElementById('file-name'),
    fileRows: document.getElementById('file-rows'),
    clearFileBtn: document.getElementById('clear-file'),

    // Sidebar Sections
    methodSection: document.getElementById('method-section'),
    variableSection: document.getElementById('variable-section'),
    actionSection: document.getElementById('action-section'),

    // Method Selection
    methodInputs: document.getElementsByName('analysis-type'),

    // Sidebar Summary & Config
    summaryFactors: document.getElementById('summary-factors'),
    summaryTargets: document.getElementById('summary-targets'),
    openVariableModalBtn: document.getElementById('btn-open-variable-modal'),
    clusterParams: document.getElementById('cluster-params'),

    // Variable Modal
    variableModal: document.getElementById('variable-modal'),
    variableModalTitle: document.getElementById('variable-modal-title'),
    closeVariableModalBtn: document.getElementById('close-variable-modal'),
    cancelVariableModalBtn: document.getElementById('cancel-variable-modal'),
    confirmVariableModalBtn: document.getElementById('confirm-variable-modal'),

    variableSearch: document.getElementById('variable-search'),
    modalSourceList: document.getElementById('modal-source-list'),
    sourceCount: document.getElementById('source-count'),
    modalActions: document.getElementById('modal-actions'),
    modalTargetPanels: document.getElementById('modal-target-panels'),

    // Main Content
    emptyState: document.getElementById('empty-state'),
    loadingSection: document.getElementById('loading-section'),
    resultSection: document.getElementById('result-section'),
    btnAnalyze: document.getElementById('btn-analyze'),

    // Results
    resultTabsNav: document.getElementById('result-tabs-nav'),
    resultTabContent: document.getElementById('result-tab-content'),

    // Export
    btnExport: document.getElementById('btn-export'),
    savePathInput: document.getElementById('save-path-input'),
    btnBrowsePath: document.getElementById('btn-browse-path'),

    // Sheet Modal
    sheetModal: document.getElementById('sheet-modal'),
    sheetList: document.getElementById('sheet-list'),
    closeModal: document.getElementById('close-modal'),

    // Toast
    toast: document.getElementById('toast'),

    // Heatmap Elements
    heatmapSection: document.getElementById('heatmap-section'),
    heatmapXVars: document.getElementById('heatmap-x-vars'),
    heatmapYVars: document.getElementById('heatmap-y-vars'),
    btnAnalyzeHeatmap: document.getElementById('btn-analyze-heatmap'),
    heatmapResult: document.getElementById('heatmap-result'),
    heatmapPreview: document.getElementById('heatmap-preview'),
    btnDownloadHeatmap: document.querySelectorAll('.btn-download-heatmap')
};

// ===== Initialization =====
function init() {
    initUpload();
    initMethodSelection();
    initVariableModal();
    initClusterControls();
    initConfigModal();
    initAnalysis();
    initHeatmap();
    initExport();
    initTabs();
    initSheetModal();
}

// ===== Upload Logic =====
function initUpload() {
    // Click to upload
    dom.uploadBtn.addEventListener('click', () => dom.fileInput.click());

    // File input change
    dom.fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) uploadFile(e.target.files[0]);
    });

    // Global Drag & Drop
    document.body.addEventListener('dragover', (e) => {
        e.preventDefault();
        if (e.dataTransfer.types.includes('Files')) {
            dom.dropOverlay.classList.add('active');
        }
    });

    dom.dropOverlay.addEventListener('dragleave', (e) => {
        if (e.target === dom.dropOverlay) {
            dom.dropOverlay.classList.remove('active');
        }
    });

    dom.dropOverlay.addEventListener('drop', (e) => {
        e.preventDefault();
        dom.dropOverlay.classList.remove('active');
        if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
    });

    // Clear data
    dom.clearFileBtn.addEventListener('click', clearData);
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    showToast('正在上传文件...', 'info');

    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.error) throw new Error(data.error);

        if (data.status === 'select_sheet' || data.need_sheet_selection) {
            showSheetModal(data.sheets, data.temp_id, file.name);
            return;
        }

        loadDataSuccess(data, file.name);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function loadDataSuccess(data, filename) {
    state.dataId = data.data_id;
    state.columns = data.columns;
    state.columnTypes = data.column_types || {};

    // Reset selections on new file
    state.factors = [];
    state.targets = [];
    state.pcaSelectedVars = [];
    state.pcaGroupVars = [];

    // Update UI
    dom.uploadPanel.hidden = true;
    dom.dataInfoPanel.hidden = false;
    dom.fileName.textContent = filename;
    dom.fileRows.textContent = `${data.rows} 行数据`;

    dom.methodSection.hidden = false;
    dom.variableSection.hidden = false;
    dom.actionSection.hidden = false;
    dom.emptyState.hidden = true;

    updateUIForMethod();
    updateSidebarSummary();
    // populateHeatmapSelectors(); // Removed in favor of modal selection

    showToast('数据加载成功', 'success');
}

function clearData() {
    state.dataId = null;
    state.columns = [];
    state.results = null;
    state.factors = [];
    state.targets = [];
    state.pcaSelectedVars = [];
    state.pcaGroupVars = [];
    state.targetConfigs = {};

    dom.fileInput.value = '';
    dom.uploadPanel.hidden = false;
    dom.dataInfoPanel.hidden = true;
    dom.methodSection.hidden = true;
    dom.variableSection.hidden = true;
    dom.actionSection.hidden = true;
    dom.emptyState.hidden = false;
    dom.resultSection.hidden = true;
    dom.loadingSection.hidden = true;
}

// ===== Method Selection =====
function initMethodSelection() {
    dom.methodInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            state.analysisType = e.target.value;
            updateUIForMethod();
        });
    });
}

function updateUIForMethod() {
    const type = state.analysisType;

    // Update Sidebar config visibility
    if (type === 'cluster') {
        dom.clusterParams.hidden = false;
    } else {
        dom.clusterParams.hidden = true;
    }

    // Heatmap Section Visibility
    if (type === 'heatmap') {
        // Hide old heatmap section (selectors) as we move to modal workflow
        if (dom.heatmapSection) dom.heatmapSection.hidden = true;

        // Show standard sections
        dom.variableSection.hidden = false;
        dom.actionSection.hidden = false;
        dom.resultSection.hidden = true;
        if (dom.heatmapResult) dom.heatmapResult.hidden = true;
    } else {
        if (dom.heatmapSection) dom.heatmapSection.hidden = true;
        dom.variableSection.hidden = false;
        dom.actionSection.hidden = false;
        // Result section visibility depends on if we have results, but usually handled by runAnalysis
    }

    updateSidebarSummary();
}

function updateSidebarSummary() {
    const type = state.analysisType;

    // Determine which counts to show
    let factorCount = 0;
    let targetCount = 0;
    let factorLabel = '因子';
    let targetLabel = '性状';

    if (type === 'anova') {
        factorCount = state.factors.length;
        targetCount = state.targets.length;
    } else if (type === 'pca') {
        factorLabel = '分组';
        targetLabel = '变量';
        factorCount = state.pcaGroupVars ? state.pcaGroupVars.length : 0;
        targetCount = state.pcaSelectedVars.length;
    } else if (type === 'cluster') {
        factorLabel = '标签';
        targetLabel = '特征';
        factorCount = state.factors.length;
        targetCount = state.targets.length;
    } else if (type === 'heatmap') {
         factorLabel = 'X轴';
         targetLabel = 'Y轴';
         factorCount = state.heatmapX ? state.heatmapX.length : 0;
         targetCount = state.heatmapY ? state.heatmapY.length : 0;
    }

    dom.summaryFactors.parentNode.innerHTML = `
        ${factorLabel}: <span id="summary-factors" class="badge-text">${factorCount}</span>,
        ${targetLabel}: <span id="summary-targets" class="badge-text">${targetCount}</span>
    `;

    // Re-bind references because innerHTML destroyed them
    dom.summaryFactors = document.getElementById('summary-factors');
    dom.summaryTargets = document.getElementById('summary-targets');
}

// ===== Variable Selection Modal Logic =====

function initVariableModal() {
    dom.openVariableModalBtn.addEventListener('click', openVariableModal);
    dom.closeVariableModalBtn.addEventListener('click', closeVariableModal);
    dom.cancelVariableModalBtn.addEventListener('click', closeVariableModal);
    dom.confirmVariableModalBtn.addEventListener('click', confirmVariableChanges);

    dom.variableSearch.addEventListener('input', (e) => {
        renderSourceList(e.target.value);
    });
}

function openVariableModal() {
    // 1. Initialize Temp State from Global State
    tempState = {
        factors: [...state.factors],
        targets: [...state.targets],
        pcaSelectedVars: [...state.pcaSelectedVars],
        pcaGroupVars: state.pcaGroupVars ? [...state.pcaGroupVars] : [],
        heatmapX: state.heatmapX ? [...state.heatmapX] : [],
        heatmapY: state.heatmapY ? [...state.heatmapY] : []
    };

    lastSelectedIndex = -1; // Reset selection index

    // 2. Set Modal Title
    const typeMap = {
        'anova': '方差分析 - 变量选择',
        'pca': 'PCA - 变量选择',
        'cluster': '聚类分析 - 变量选择',
        'heatmap': '相关性热图 - 变量选择'
    };
    dom.variableModalTitle.textContent = typeMap[state.analysisType];

    // 3. Render Interface
    dom.variableSearch.value = '';
    renderTransferUI();

    // 4. Show Modal
    dom.variableModal.classList.add('active');
}

function closeVariableModal() {
    dom.variableModal.classList.remove('active');
}

function confirmVariableChanges() {
    // Save temp state to global state
    state.factors = [...tempState.factors];
    state.targets = [...tempState.targets];
    state.pcaSelectedVars = [...tempState.pcaSelectedVars];
    state.pcaGroupVars = [...tempState.pcaGroupVars];
    if (tempState.heatmapX) state.heatmapX = [...tempState.heatmapX];
    if (tempState.heatmapY) state.heatmapY = [...tempState.heatmapY];

    updateSidebarSummary();
    closeVariableModal();
    showToast('变量设置已更新', 'success');
}

function renderTransferUI() {
    renderSourceList();
    renderMiddleActions();
    renderTargetPanels();
}

/**
 * Render Source List (Left Panel)
 */
function renderSourceList(filterText = '') {
    dom.modalSourceList.innerHTML = '';

    // Determine which variables are already used
    let usedVars = new Set();
    if (state.analysisType === 'anova' || state.analysisType === 'cluster') {
        usedVars = new Set([...tempState.factors, ...tempState.targets]);
    } else if (state.analysisType === 'pca') {
        usedVars = new Set([...tempState.pcaSelectedVars, ...tempState.pcaGroupVars]);
    } else if (state.analysisType === 'heatmap') {
        usedVars = new Set([...tempState.heatmapX, ...tempState.heatmapY]);
    }

    const availableCols = state.columns.filter(col =>
        !usedVars.has(col) &&
        col.toLowerCase().includes(filterText.toLowerCase())
    );

    dom.sourceCount.textContent = availableCols.length;

    // Helper to get visible items for range selection
    const getVisibleItems = () => Array.from(dom.modalSourceList.querySelectorAll('.transfer-item'));

    availableCols.forEach((col, index) => {
        const li = document.createElement('li');
        li.className = 'transfer-item';
        li.textContent = col;
        li.dataset.index = index; // Store visual index

        // Visual indicator for type
        if (state.columnTypes[col] === 'numeric') {
            li.classList.add('type-numeric');
            li.title = '数值变量';
        } else {
            li.classList.add('type-categorical');
            li.title = '分类变量';
        }

        // Selection Toggle with Shift Key Support
        li.onclick = (e) => {
            if (e.shiftKey && lastSelectedIndex !== -1) {
                // Range Selection
                const items = getVisibleItems();
                const start = Math.min(lastSelectedIndex, index);
                const end = Math.max(lastSelectedIndex, index);

                for (let i = start; i <= end; i++) {
                    items[i].classList.add('selected');
                }
            } else {
                // Normal Toggle
                if (li.classList.contains('selected')) {
                    li.classList.remove('selected');
                } else {
                    li.classList.add('selected');
                    lastSelectedIndex = index;
                }
            }
        };

        // Double Click Action
        li.ondblclick = () => handleSourceDoubleClick(col);

        dom.modalSourceList.appendChild(li);
    });
}

function getSelectedSourceItems() {
    return Array.from(dom.modalSourceList.querySelectorAll('.transfer-item.selected')).map(el => el.textContent);
}

/**
 * Render Middle Actions (Buttons)
 */
function renderMiddleActions() {
    dom.modalActions.innerHTML = '';
    const type = state.analysisType;

    if (type === 'anova') {
        createActionBtn('添加因子 >', 'btn-primary', () => moveItemsTo('factors'));
        createActionBtn('添加性状 >', 'btn-success', () => moveItemsTo('targets', true)); // true = numeric only
        createActionBtn('< 移除', 'btn-outline', () => removeSelectedItems());
    } else if (type === 'pca') {
        createActionBtn('添加分组 >', 'btn-primary', () => moveItemsTo('pcaGroupVars'));
        createActionBtn('添加变量 >', 'btn-success', () => moveItemsTo('pcaSelectedVars', true));
        createActionBtn('< 移除', 'btn-outline', () => removeSelectedItems());
    } else if (type === 'cluster') {
        createActionBtn('添加标签 >', 'btn-primary', () => moveItemsTo('factors')); // Labels
        createActionBtn('添加特征 >', 'btn-success', () => moveItemsTo('targets', true)); // Features
        createActionBtn('< 移除', 'btn-outline', () => removeSelectedItems());
    } else if (type === 'heatmap') {
        createActionBtn('添加 X 轴 >', 'btn-primary', () => moveItemsTo('heatmapX', true));
        createActionBtn('添加 Y 轴 >', 'btn-success', () => moveItemsTo('heatmapY', true));
        createActionBtn('< 移除', 'btn-outline', () => removeSelectedItems());
    }
}

function createActionBtn(text, cls, handler) {
    const btn = document.createElement('button');
    btn.className = `btn-transfer ${cls}`;
    btn.textContent = text;
    btn.onclick = handler;
    dom.modalActions.appendChild(btn);
}

/**
 * Render Target Panels (Right Side)
 */
function renderTargetPanels() {
    dom.modalTargetPanels.innerHTML = '';
    const type = state.analysisType;

    if (type === 'anova') {
        createTargetListPanel('因子 (Factors)', tempState.factors, 'factors');
        createTargetListPanel('性状 (Targets)', tempState.targets, 'targets');
    } else if (type === 'pca') {
        // PCA Vars List
        createTargetListPanel('分析变量 (Numeric)', tempState.pcaSelectedVars, 'pcaSelectedVars');
        // PCA Group List (Multi-select)
        createTargetListPanel('分组变量 (Grouping)', tempState.pcaGroupVars, 'pcaGroupVars');
    } else if (type === 'cluster') {
        createTargetListPanel('聚类特征 (Features)', tempState.targets, 'targets');
        createTargetListPanel('样本标签 (Labels)', tempState.factors, 'factors');
    } else if (type === 'heatmap') {
        createTargetListPanel('X 轴变量 (Numeric)', tempState.heatmapX, 'heatmapX');
        createTargetListPanel('Y 轴变量 (Numeric)', tempState.heatmapY, 'heatmapY');
    }
}

function createTargetListPanel(title, items, listKey) {
    const panel = document.createElement('div');
    panel.className = 'transfer-target-box';

    const header = document.createElement('div');
    header.className = 'target-header';
    header.textContent = `${title} (${items.length})`;
    panel.appendChild(header);

    const ul = document.createElement('ul');
    ul.className = 'transfer-list small-list';
    ul.dataset.listKey = listKey; // For identifying which list items belong to

    items.forEach(item => {
        const li = document.createElement('li');
        li.className = 'transfer-item';
        // Flex layout for item content
        li.style.display = 'flex';
        li.style.justifyContent = 'space-between';
        li.style.alignItems = 'center';

        const span = document.createElement('span');
        span.textContent = item;
        li.appendChild(span);

        // Gear icon for PCA numeric vars
        if (state.analysisType === 'pca' && listKey === 'pcaSelectedVars') {
            const btnConfig = document.createElement('span');
            btnConfig.innerHTML = '⚙️';
            btnConfig.title = '配置正向化/区间';
            btnConfig.style.cursor = 'pointer';
            btnConfig.style.fontSize = '1.1rem';
            btnConfig.style.opacity = '0.7';
            btnConfig.style.padding = '0 4px';

            btnConfig.onmouseover = () => btnConfig.style.opacity = '1';
            btnConfig.onmouseout = () => btnConfig.style.opacity = '0.7';

            btnConfig.onclick = (e) => {
                e.stopPropagation(); // Prevent selection
                openConfigModal(item);
            };
            li.appendChild(btnConfig);
        }

        li.onclick = (e) => {
            if (e.target !== li && e.target !== span) return; // Prevent triggering when clicking gear
            li.classList.toggle('selected');
        };
        li.ondblclick = () => removeItem(item, listKey);

        ul.appendChild(li);
    });

    panel.appendChild(ul);
    dom.modalTargetPanels.appendChild(panel);
}

// ===== Interaction Logic =====

function handleSourceDoubleClick(col) {
    const type = state.analysisType;
    const isNum = state.columnTypes[col] === 'numeric';

    if (type === 'anova') {
        if (isNum) moveItemDirect(col, 'targets');
        else moveItemDirect(col, 'factors');
    } else if (type === 'pca') {
        if (isNum) moveItemDirect(col, 'pcaSelectedVars');
        else moveItemDirect(col, 'pcaGroupVars');
    } else if (type === 'cluster') {
        if (isNum) moveItemDirect(col, 'targets'); // Feature
        else moveItemDirect(col, 'factors'); // Label
    } else if (type === 'heatmap') {
        // Default to X axis for double click, but only if numeric
        if (isNum) moveItemDirect(col, 'heatmapX');
    }
}

function moveItemsTo(targetListKey, requireNumeric = false) {
    const selected = getSelectedSourceItems();
    if (!selected.length) return;

    const validItems = [];
    selected.forEach(col => {
        if (requireNumeric && state.columnTypes[col] !== 'numeric') {
            // Skip non-numeric
        } else {
            validItems.push(col);
        }
    });

    if (validItems.length < selected.length && requireNumeric) {
        showToast('已过滤非数值变量', 'info');
    }

    // Add to temp state
    tempState[targetListKey] = [...tempState[targetListKey], ...validItems];

    // Re-render
    renderTransferUI();
}

function moveItemDirect(col, targetListKey) {
    tempState[targetListKey].push(col);
    renderTransferUI();
}

function removeSelectedItems() {
    // Find all selected items in target lists
    const targetLists = dom.modalTargetPanels.querySelectorAll('ul.transfer-list');
    let changed = false;

    targetLists.forEach(ul => {
        const listKey = ul.dataset.listKey;
        const selectedEls = ul.querySelectorAll('.transfer-item.selected');
        if (selectedEls.length) {
            const itemsToRemove = Array.from(selectedEls).map(el => el.textContent);
            tempState[listKey] = tempState[listKey].filter(item => !itemsToRemove.includes(item));
            changed = true;
        }
    });

    if (changed) renderTransferUI();
}

function removeItem(item, listKey) {
    tempState[listKey] = tempState[listKey].filter(x => x !== item);
    renderTransferUI();
}

// ===== Cluster Controls =====
function initClusterControls() {
    const inputs = dom.clusterParams.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('change', () => {
            if (input.id === 'cluster-k') state.clusterParams.k = parseInt(input.value);
            if (input.id === 'cluster-algorithm') state.clusterParams.algorithm = input.value;
            if (input.id === 'cluster-use-means') state.clusterParams.useMeans = input.checked;
        });
    });
}

// ===== Config Modal (Normalization) =====
function initConfigModal() {
    const modal = document.getElementById('config-modal');
    const typeSelect = document.getElementById('config-type');
    const intervalParams = document.getElementById('config-interval-params');

    document.getElementById('close-config-modal').onclick = () => modal.classList.remove('active');
    document.getElementById('cancel-config-btn').onclick = () => modal.classList.remove('active');

    typeSelect.onchange = () => {
        intervalParams.hidden = typeSelect.value !== 'interval';
    };

    document.getElementById('save-config-btn').onclick = () => {
        const col = modal.dataset.currentItem;
        if (!col) return;

        const type = typeSelect.value;
        const config = { type };

        if (type === 'interval') {
            const a = parseFloat(document.getElementById('config-a').value);
            const b = parseFloat(document.getElementById('config-b').value);
            if (isNaN(a) || isNaN(b)) {
                return showToast('请输入有效的区间边界', 'error');
            }
            config.a = a;
            config.b = b;
        }

        state.targetConfigs[col] = config;
        modal.classList.remove('active');
        showToast(`已保存变量配置: ${col}`, 'success');
    };
}

function openConfigModal(col) {
    const modal = document.getElementById('config-modal');
    const title = document.getElementById('config-modal-title');
    const typeSelect = document.getElementById('config-type');
    const intervalParams = document.getElementById('config-interval-params');
    const inputA = document.getElementById('config-a');
    const inputB = document.getElementById('config-b');

    modal.dataset.currentItem = col;
    title.textContent = `变量配置: ${col}`;

    // Load existing config
    const config = state.targetConfigs[col] || { type: 'benefit' };
    typeSelect.value = config.type;
    intervalParams.hidden = config.type !== 'interval';

    if (config.type === 'interval') {
        inputA.value = config.a !== undefined ? config.a : '';
        inputB.value = config.b !== undefined ? config.b : '';
    } else {
        inputA.value = '';
        inputB.value = '';
    }

    modal.classList.add('active');
}

// ===== Analysis Logic =====
function initAnalysis() {
    dom.btnAnalyze.addEventListener('click', runAnalysis);
}

async function runAnalysis() {
    const type = state.analysisType;
    let payload = { data_id: state.dataId };
    let endpoint = '';

    // Validation & Payload Construction
    if (type === 'anova') {
        if (!state.factors.length || !state.targets.length) {
            return showToast('请至少选择一个因子和一个性状', 'error');
        }
        payload.factors = state.factors;
        payload.targets = state.targets;
        endpoint = '/api/analyze';
    } else if (type === 'pca') {
        if (state.pcaSelectedVars.length < 2) {
            return showToast('PCA 分析至少需要 2 个数值变量', 'error');
        }
        payload.targets = state.pcaSelectedVars;
        payload.group_by = state.pcaGroupVars || [];
        payload.target_configs = state.targetConfigs;
        endpoint = '/api/analyze_pca';
    } else if (type === 'cluster') {
        if (state.targets.length < 1) {
             return showToast('请选择至少一个聚类特征', 'error');
        }
        payload.features = state.targets;
        payload.factors = state.factors; // Optional labels
        payload.algorithm = state.clusterParams.algorithm;
        payload.n_clusters = state.clusterParams.k;
        payload.use_means = state.clusterParams.useMeans;
        endpoint = '/api/analyze_cluster';
    } else if (type === 'heatmap') {
        if (!state.heatmapX.length || !state.heatmapY.length) {
            return showToast('请至少选择一个 X 轴变量和一个 Y 轴变量', 'error');
        }
        payload.x_vars = state.heatmapX;
        payload.y_vars = state.heatmapY;
        endpoint = '/api/analyze_heatmap';
    }

    // UI State
    dom.loadingSection.hidden = false;
    dom.resultSection.hidden = true;
    if (dom.heatmapResult) dom.heatmapResult.hidden = true;
    dom.emptyState.hidden = true;

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (data.error) throw new Error(data.error);

        state.results = data;

        if (type === 'heatmap') {
            dom.heatmapPreview.src = `data:image/png;base64,${data.image}`;
            if (dom.heatmapResult) dom.heatmapResult.hidden = false;
            // Ensure heatmap section (container) is visible if hidden by default
            if (dom.heatmapSection) dom.heatmapSection.hidden = false;
        } else {
            renderResults(data, type);
            dom.resultSection.hidden = false;
            if (dom.heatmapResult) dom.heatmapResult.hidden = true;
        }

        dom.loadingSection.hidden = true;
        showToast('分析完成', 'success');

    } catch (err) {
        dom.loadingSection.hidden = true;
        showToast(err.message, 'error');
    }
}

// ===== Result Rendering =====
function renderResults(data, type) {
    // 1. Generate Tabs
    dom.resultTabsNav.innerHTML = '';
    const tabs = [];

    if (type === 'anova') {
        if (data.sliced_sep) tabs.push({ id: 'panel-sliced-sep', label: '组内比较(分列)' });
        if (data.sliced_comb) tabs.push({ id: 'panel-sliced', label: '组内比较(组合)' });
        if (data.main) tabs.push({ id: 'panel-main', label: '主效应' });
        if (data.anova) tabs.push({ id: 'panel-anova', label: '方差分析表' });
        if (data.corr) tabs.push({ id: 'panel-corr', label: '相关分析' });
    } else if (type === 'pca') {
        tabs.push({ id: 'panel-pca-scree', label: '碎石图' });
        tabs.push({ id: 'panel-pca-variance', label: '特征值/方差' }); // New Tab
        tabs.push({ id: 'panel-pca-biplot', label: '双标图' });
        tabs.push({ id: 'panel-pca-loadings', label: '载荷矩阵' });
        tabs.push({ id: 'panel-pca-scores', label: '得分数据' });
    } else if (type === 'cluster') {
        tabs.push({ id: 'panel-cluster-summary', label: '聚类摘要' });
        tabs.push({ id: 'panel-cluster-scatter', label: '散点图' });
        tabs.push({ id: 'panel-cluster-heatmap', label: '热图' });
        tabs.push({ id: 'panel-cluster-data', label: '聚类数据' });
        tabs.push({ id: 'panel-cluster-elbow', label: '肘部法则' });
    }

    tabs.forEach((tab, idx) => {
        const btn = document.createElement('button');
        btn.className = `tab-btn ${idx === 0 ? 'active' : ''}`;
        btn.textContent = tab.label;
        btn.dataset.target = tab.id;
        btn.addEventListener('click', () => switchTab(tab.id));
        dom.resultTabsNav.appendChild(btn);
    });

    // Switch to first tab content
    if (tabs.length) switchTab(tabs[0].id);

    // 2. Populate Content
    if (type === 'anova') {
        renderTable('sliced-sep-table', data.sliced_sep);
        renderTable('sliced-table', data.sliced_comb);
        renderTable('main-table', data.main);
        renderTable('anova-table', data.anova);
        renderTable('corr-table', data.corr);
    } else if (type === 'pca') {
        renderPlot('pca-scree-plot', data.scree_plot, 'PCA_碎石图.png');

        // Render Variance/Eigenvalue Table
        renderTable('pca-variance-table', data.variance);

        // Fix: Render Loadings Table correctly
        if (data.loadings) {
            renderTable('pca-loadings-table', data.loadings);
        } else {
            console.warn('No loadings data found in response');
        }

        renderTable('pca-scores-table', data.scores);

        // Init Biplot Logic
        if (data.biplot_2d) {
            renderPlot('pca-biplot-2d', data.biplot_2d, 'PCA_双标图_2D.png');
            initBiplotControls(data.summary.n_components);
        }
    } else if (type === 'cluster') {
        // Summary
        if (data.summary) {
            const sumHtml = `
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:16px; margin-bottom:24px;">
                    <div class="file-card"><div class="file-details"><strong>算法</strong><div>${data.summary.algorithm}</div></div></div>
                    <div class="file-card"><div class="file-details"><strong>聚类数</strong><div>${data.summary.n_clusters}</div></div></div>
                    <div class="file-card"><div class="file-details"><strong>样本数</strong><div>${data.summary.n_samples}</div></div></div>
                </div>
                <div style="display:flex; flex-wrap:wrap; gap:8px;">
                    ${data.summary.cluster_sizes.map(s =>
                        `<span class="badge" style="font-size:0.9rem; padding:6px 10px;">Cluster ${s.cluster}: ${s.size} (${s.percentage}%)</span>`
                    ).join('')}
                </div>
            `;
            document.getElementById('cluster-summary-content').innerHTML = sumHtml;
        }

        renderPlot('cluster-scatter-plot', data.scatter_plot, '聚类_散点图.png');
        renderPlot('cluster-heatmap-plot', data.heatmap_plot, '聚类_热图.png');
        renderPlot('cluster-corr-heatmap-plot', data.corr_heatmap_plot, '聚类_相关性热图.png');

        // Render Cluster Data Table (Specific rendering for highlighted cells)
        const dt = document.getElementById('cluster-data-table');
        if (data.labeled_data && data.labeled_data.rows) {
             let html = '<table><thead><tr>';
             data.labeled_data.headers.forEach(h => html += `<th>${h}</th>`);
             html += '</tr></thead><tbody>';
             data.labeled_data.rows.forEach(row => {
                 html += '<tr>';
                 row.forEach(cell => html += `<td>${cell}</td>`);
                 html += '</tr>';
             });
             html += '</tbody></table>';
             dt.innerHTML = html;
        }

        // Init Cluster Export Button
        document.getElementById('btn-export-cluster').onclick = () => exportClusterData();

        // Init Elbow Button logic
        document.getElementById('btn-elbow').onclick = fetchElbowPlot;
    }
}

function switchTab(id) {
    // Buttons
    const btns = dom.resultTabsNav.querySelectorAll('.tab-btn');
    btns.forEach(b => {
        if (b.dataset.target === id) b.classList.add('active');
        else b.classList.remove('active');
    });

    // Content
    const panes = dom.resultTabContent.querySelectorAll('.tab-pane');
    panes.forEach(p => {
        if (p.id === id) p.classList.add('active');
        else p.classList.remove('active');
    });
}

function renderTable(id, data) {
    const container = document.getElementById(id);
    if (!container || !data || !data.length) {
        if (container) container.innerHTML = '<div class="p-4 text-center text-muted">暂无数据</div>';
        return;
    }

    const cols = Object.keys(data[0]);
    let html = '<table><thead><tr>';
    cols.forEach(c => html += `<th>${c}</th>`);
    html += '</tr></thead><tbody>';

    data.slice(0, 500).forEach(row => {
        html += '<tr>';
        cols.forEach(c => html += `<td>${row[c] !== null ? row[c] : ''}</td>`);
        html += '</tr>';
    });

    html += '</tbody></table>';

    if (data.length > 500) {
        html += `<div class="p-2 text-center text-muted bg-light border-top">仅显示前 500 行，完整数据请导出</div>`;
    }

    container.innerHTML = html;
}

function renderPlot(id, plotData, filename = 'chart.png') {
    const container = document.getElementById(id);
    if (!container) return;

    if (!plotData || !plotData.data) {
        container.innerHTML = '<div class="text-muted">图表生成失败</div>';
        return;
    }

    // 清空容器
    container.innerHTML = '';

    const wrapper = document.createElement('div');
    wrapper.style.display = 'flex';
    wrapper.style.flexDirection = 'column';
    wrapper.style.alignItems = 'center';

    if (plotData.format === 'png') {
        const img = document.createElement('img');
        img.src = `data:image/png;base64,${plotData.data}`;
        img.alt = "Plot";
        img.style.maxWidth = '100%';
        img.style.height = 'auto';
        img.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
        wrapper.appendChild(img);

        // 下载按钮
        const btn = document.createElement('button');
        btn.innerHTML = '📥 下载高清大图 (600 DPI)';
        btn.className = 'btn-outline-sm';
        btn.style.marginTop = '12px';
        btn.onclick = () => {
            const a = document.createElement('a');
            a.href = img.src;
            a.download = filename;
            a.click();
        };
        wrapper.appendChild(btn);
    } else {
        wrapper.innerHTML = plotData.data;
    }

    container.appendChild(wrapper);
}

// ===== Biplot Interactive Logic =====
function initBiplotControls(n_components) {
    // Populate Selects
    const selects = [document.getElementById('biplot-x-select'), document.getElementById('biplot-y-select'), document.getElementById('biplot-z-select')];
    selects.forEach(sel => {
        sel.innerHTML = '';
        for (let i = 1; i <= n_components; i++) {
            sel.innerHTML += `<option value="${i}">PC${i}</option>`;
        }
    });

    // Defaults
    selects[0].value = 1;
    selects[1].value = 2;
    selects[2].value = 3;

    // 2D/3D Toggle
    const btn2d = document.getElementById('btn-biplot-2d');
    const btn3d = document.getElementById('btn-biplot-3d');
    const zSel = document.getElementById('biplot-z-select');
    const groupSel = document.getElementById('biplot-group-select'); // New
    const p2d = document.getElementById('pca-biplot-2d');
    const p3d = document.getElementById('pca-biplot-3d');

    // Update Group Select options when controls init or variables update
    const updateGroupOptions = () => {
        groupSel.innerHTML = '<option value="">(无)</option>';
        if (state.pcaGroupVars && state.pcaGroupVars.length) {
            state.pcaGroupVars.forEach(g => {
                const opt = document.createElement('option');
                opt.value = g;
                opt.textContent = g;
                groupSel.appendChild(opt);
            });
            // Default select the first one if available
            groupSel.value = state.pcaGroupVars[0];
        }
    };
    updateGroupOptions(); // Init call

    btn2d.onclick = () => {
        btn2d.classList.add('active');
        btn3d.classList.remove('active');
        zSel.hidden = true;
        p2d.hidden = false;
        p3d.hidden = true;
    };

    btn3d.onclick = () => {
        btn3d.classList.add('active');
        btn2d.classList.remove('active');
        zSel.hidden = false;
        p2d.hidden = true;
        p3d.hidden = false;
    };

    // Update Button
    document.getElementById('btn-update-biplot').onclick = async () => {
        const is3D = btn3d.classList.contains('active');
        const x = parseInt(selects[0].value);
        const y = parseInt(selects[1].value);
        const z = is3D ? parseInt(selects[2].value) : null;
        const ellipseGroup = groupSel.value; // Get selected group

        const drawEllipse = document.getElementById('pca-draw-ellipse').checked;
        const confidence = parseInt(document.getElementById('pca-confidence-level').value) / 100;

        // Validate
        if (x === y || (is3D && (x === z || y === z))) {
            return showToast('坐标轴不能选择相同的主成分', 'warning');
        }

        const container = is3D ? p3d : p2d;
        container.innerHTML = '<div class="spinner"></div>';

        try {
            const res = await fetch('/api/pca_plot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    data_id: state.dataId,
                    targets: state.pcaSelectedVars,
                    group_by: state.pcaGroupVars || [],
                    ellipse_group: ellipseGroup, // Pass specific group
                    plot_type: is3D ? 'biplot_3d' : 'biplot_2d',
                    format: 'png',
                    pc_x: x, pc_y: y, pc_z: z,
                    draw_ellipse: drawEllipse,
                    confidence_level: confidence
                })
            });
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            renderPlot(is3D ? 'pca-biplot-3d' : 'pca-biplot-2d', data, is3D ? 'PCA_双标图_3D.png' : 'PCA_双标图_2D.png');
        } catch (err) {
            container.innerHTML = `<div class="text-danger">${err.message}</div>`;
        }
    };

    // Ellipse Options Toggle
    document.getElementById('pca-draw-ellipse').onchange = (e) => {
        document.getElementById('ellipse-options').hidden = !e.target.checked;
    };
}

// ===== Elbow Plot Logic =====
async function fetchElbowPlot() {
    const btn = document.getElementById('btn-elbow');
    btn.disabled = true;
    btn.textContent = '计算中...';

    try {
        const res = await fetch('/api/cluster_elbow', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: state.dataId,
                features: state.targets,
                max_k: 10
            })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        renderPlot('cluster-elbow-plot', data.elbow_plot, '聚类_肘部法则图.png');
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '生成肘部图';
    }
}

// ===== Export Logic =====
function initExport() {
    dom.btnExport.addEventListener('click', async () => {
        if (!state.results) return showToast('无分析结果可导出', 'warning');

        // Check Analysis Type and call appropriate export
        const type = state.analysisType;
        let endpoint = '/api/export';
        let payload = {};

        if (type === 'anova') {
            payload = {
                sliced_comb: state.results.sliced_comb,
                sliced_sep: state.results.sliced_sep,
                main: state.results.main,
                anova: state.results.anova,
                corr: state.results.corr
            };
        } else if (type === 'pca') {
            endpoint = '/api/export_pca';
            payload = {
                loadings: state.results.loadings,
                variance: state.results.variance,
                weights: state.results.weights,
                scores: state.results.scores,
                include_loadings: true, include_variance: true, include_weights: true, include_scores: true
            };
        }

        if (dom.savePathInput.value) payload.save_directory = dom.savePathInput.value;

        doExport(endpoint, payload);
    });

    dom.btnBrowsePath.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/select_directory');
            const data = await res.json();
            if (data.directory) dom.savePathInput.value = data.directory;
        } catch (e) { console.error(e); }
    });
}

async function exportClusterData() {
    doExport('/api/export_cluster', {
        data_id: state.dataId,
        features: state.targets,
        algorithm: state.clusterParams.algorithm,
        n_clusters: state.clusterParams.k,
        linkage_method: "ward"
    });
}

async function doExport(endpoint, payload) {
    showToast('正在导出...', 'info');
    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.text();
            throw new Error('导出请求失败');
        }

        const contentType = res.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const json = await res.json();
            if (json.success) showToast(json.message, 'success');
            else throw new Error(json.error);
        } else {
            // Blob Download
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'Analysis_Result.xlsx'; // Generic name
            a.click();
            URL.revokeObjectURL(url);
            showToast('导出成功', 'success');
        }
    } catch (err) {
        showToast('导出失败: ' + err.message, 'error');
    }
}

// ===== Heatmap Logic =====
function initHeatmap() {
    // Legacy button listener removed as we use main analyze button now
    // if (dom.btnAnalyzeHeatmap) {
    //     dom.btnAnalyzeHeatmap.addEventListener('click', runHeatmapAnalysis);
    // }

    if (dom.btnDownloadHeatmap) {
        dom.btnDownloadHeatmap.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const format = e.target.dataset.format || 'png';
                downloadHeatmap(format);
            });
        });
    }
}

// populateHeatmapSelectors removed

// runHeatmapAnalysis removed

async function downloadHeatmap(format) {
    const xOptions = state.heatmapX;
    const yOptions = state.heatmapY;

    if (!xOptions || xOptions.length === 0 || !yOptions || yOptions.length === 0) {
        return showToast('请先进行热图分析配置', 'warning');
    }

    showToast('正在导出热图...', 'info');

    try {
        const res = await fetch('/api/export_heatmap_image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: state.dataId,
                x_vars: xOptions,
                y_vars: yOptions,
                format: format
            })
        });

        if (!res.ok) throw new Error('Export failed');

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `correlation_heatmap.${format}`;
        a.click();
        URL.revokeObjectURL(url);

        showToast('导出成功', 'success');
    } catch (err) {
        showToast('导出失败: ' + err.message, 'error');
    }
}

// ===== Utilities =====
function showToast(msg, type = 'info') {
    dom.toast.textContent = msg;
    dom.toast.className = `toast ${type} show`;
    setTimeout(() => {
        dom.toast.classList.remove('show');
    }, 3000);
}

function initSheetModal() {
    dom.closeModal.onclick = () => dom.sheetModal.classList.remove('active');
}

function showSheetModal(sheets, tempId, fileName) {
    dom.sheetList.innerHTML = '';
    sheets.forEach(sheet => {
        const div = document.createElement('div');
        div.className = 'sheet-item';
        div.textContent = sheet;
        div.onclick = async () => {
            dom.sheetModal.classList.remove('active');
            // Load Sheet
            const res = await fetch('/api/load_sheet', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ temp_id: tempId, sheet_name: sheet })
            });
            const data = await res.json();
            loadDataSuccess(data, `${fileName} [${sheet}]`);
        };
        dom.sheetList.appendChild(div);
    });
    dom.sheetModal.classList.add('active');
}

function initTabs() {
    // Initial tab logic is handled by renderResults
}

// Start
document.addEventListener('DOMContentLoaded', init);
