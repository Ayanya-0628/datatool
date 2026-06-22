/**
 * DataAnalysis Pro - Frontend Logic
 * Version: 2.1 - Variable Selection Modal
 */

const APP_BASE_PATH = (() => {
    const marker = '/slylab-app/';
    return window.location.pathname.startsWith(marker) ? marker.replace(/\/$/, '') : '';
})();

const apiUrl = (path) => `${APP_BASE_PATH}${path}`;

const nativeFetch = window.fetch.bind(window);
window.fetch = (input, init) => {
    if (typeof input === 'string' && input.startsWith('/api/')) {
        return nativeFetch(apiUrl(input), init);
    }
    if (input instanceof Request && new URL(input.url).pathname.startsWith('/api/')) {
        return nativeFetch(new Request(apiUrl(new URL(input.url).pathname), input), init);
    }
    return nativeFetch(input, init);
};

// ===== State Management =====
const state = {
    dataId: null,
    columns: [],
    columnTypes: {}, // { colName: 'numeric' | 'categorical' }
    analysisType: 'anova', // 'anova', 'pca', 'cluster', 'heatmap', 'barchart', 'nature'

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

    // Reshape Config
    reshapeMode: 'melt', // 'melt' or 'pivot'

    // Barchart Config
    barchartGroupCols: [],
    barchartValueCol: '',
    barchartColors: {},  // { groupVal: '#hex' }

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
    initReshape();
    initBarChart();
    initNaturePlot();
    initExport();
    initTabs();
    initSheetModal();
    initMethodGallery();
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

    dom.methodSection.hidden = true;
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
    const natureSection = document.getElementById('nature-section');
    if (natureSection) natureSection.hidden = true;
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

// ===== Method Gallery (首屏方法画廊) =====
function initMethodGallery() {
    document.querySelectorAll('.gallery-card').forEach(card => {
        card.addEventListener('click', () => enterWorkspace(card.dataset.method));
    });
    const backBtn = document.getElementById('back-to-gallery');
    if (backBtn) backBtn.addEventListener('click', backToGallery);
}

function enterWorkspace(method) {
    state.analysisType = method || 'anova';
    // 同步选中侧栏对应的方法 radio（保留快速切换）
    dom.methodInputs.forEach(input => { input.checked = (input.value === state.analysisType); });
    // 隐藏画廊，进入工作区
    const gallery = document.getElementById('method-gallery');
    if (gallery) gallery.hidden = true;
    // 方法已在画廊选定，侧栏不再显示方法列表，腾出空间给参数设置（切换方法走「返回方法」）
    dom.methodSection.hidden = true;
    updateUIForMethod();
}

function backToGallery() {
    const gallery = document.getElementById('method-gallery');
    if (gallery) gallery.hidden = false;
}

function updateUIForMethod() {
    const type = state.analysisType;
    const reshapeSection = document.getElementById('reshape-section');
    const natureSection = document.getElementById('nature-section');

    // Update Sidebar config visibility
    if (type === 'cluster') {
        dom.clusterParams.hidden = false;
    } else {
        dom.clusterParams.hidden = true;
    }

    // Reshape mode: hide sidebar variable/action, show reshape panel
    if (type === 'reshape') {
        dom.variableSection.hidden = true;
        dom.actionSection.hidden = true;
        dom.resultSection.hidden = true;
        dom.emptyState.hidden = true;
        if (dom.heatmapSection) dom.heatmapSection.hidden = true;
        const barchartSection = document.getElementById('barchart-section');
        if (barchartSection) barchartSection.hidden = true;
        if (natureSection) natureSection.hidden = true;
        if (reshapeSection) reshapeSection.hidden = false;
        // 默认进入 smart 模式
        setTimeout(() => setReshapeMode('smart'), 50);
        // Load preview
        if (state.dataId) loadReshapePreview();
        return;
    } else {
        if (reshapeSection) reshapeSection.hidden = true;
    }

    // Barchart mode: similar to reshape, has its own panel
    const barchartSection = document.getElementById('barchart-section');
    if (type === 'barchart') {
        dom.variableSection.hidden = true;
        dom.actionSection.hidden = true;
        dom.resultSection.hidden = true;
        dom.emptyState.hidden = true;
        if (dom.heatmapSection) dom.heatmapSection.hidden = true;
        if (reshapeSection) reshapeSection.hidden = true;
        if (natureSection) natureSection.hidden = true;
        if (barchartSection) {
            barchartSection.hidden = false;
            populateBarchartSelectors();
        }
        return;
    } else {
        if (barchartSection) barchartSection.hidden = true;
    }

    // Nature plot mode: independent figure panel
    if (type === 'nature') {
        dom.variableSection.hidden = true;
        dom.actionSection.hidden = true;
        dom.resultSection.hidden = true;
        dom.emptyState.hidden = true;
        if (dom.heatmapSection) dom.heatmapSection.hidden = true;
        if (reshapeSection) reshapeSection.hidden = true;
        if (natureSection) {
            natureSection.hidden = false;
            populateNatureSelectors();
        }
        return;
    } else {
        if (natureSection) natureSection.hidden = true;
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
    renderInlineVars();
}

// ===== 侧栏内联变量选择（anova/cluster/pca，免开弹窗直接勾选） =====
function renderInlineVars() {
    const box = document.getElementById('inline-vars');
    if (!box) return;
    const type = state.analysisType;
    if (!['anova', 'cluster', 'pca'].includes(type) || !state.dataId) {
        box.hidden = true;
        box.innerHTML = '';
        return;
    }
    const cols = state.columns || [];
    const isNum = c => state.columnTypes[c] === 'numeric';
    let groups;
    if (type === 'pca') {
        groups = [
            { title: '分组（可选）', cands: cols.filter(c => !isNum(c)), key: 'pcaGroupVars' },
            { title: '分析变量（数值）', cands: cols.filter(isNum), key: 'pcaSelectedVars' },
        ];
    } else {
        const fTitle = type === 'cluster' ? '标签 / 分组' : '因子（分组变量）';
        const tTitle = type === 'cluster' ? '聚类特征（数值）' : '性状（数值指标）';
        groups = [
            { title: fTitle, cands: cols, key: 'factors' },
            { title: tTitle, cands: cols.filter(isNum), key: 'targets' },
        ];
    }
    box.hidden = false;
    box.innerHTML = groups.map(g => {
        const sel = state[g.key] || [];
        const items = g.cands.map(c => {
            const safe = String(c).replace(/"/g, '&quot;');
            const checked = sel.includes(c) ? 'checked' : '';
            return `<label class="flex items-center gap-2 text-xs cursor-pointer py-0.5"><input type="checkbox" value="${safe}" ${checked} class="rounded text-primary focus:ring-primary h-3.5 w-3.5"><span class="truncate">${safe}</span></label>`;
        }).join('');
        return `<div class="flex flex-col gap-1"><p class="text-xs font-semibold text-slate-600 dark:text-slate-300">${g.title}</p><div class="max-h-36 overflow-y-auto rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-2 flex flex-col" data-key="${g.key}">${items || '<span class="text-xs text-slate-400">无可选列</span>'}</div></div>`;
    }).join('');
    box.querySelectorAll('div[data-key]').forEach(container => {
        const key = container.dataset.key;
        container.addEventListener('change', () => {
            state[key] = Array.from(container.querySelectorAll('input:checked')).map(i => i.value);
            updateSidebarSummary();
        });
    });
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
    } else if (type === 'reshape') {
        factorLabel = '模式';
        targetLabel = '列数';
        factorCount = state.reshapeMode === 'melt' ? 1 : 0;
        targetCount = state.columns.length;
    } else if (type === 'barchart') {
        factorLabel = '分组';
        targetLabel = '数值列';
        factorCount = state.barchartGroupCols.length;
        targetCount = state.barchartValueCol ? 1 : 0;
    } else if (type === 'nature') {
        factorLabel = '图型';
        targetLabel = '变量';
        factorCount = 1;
        targetCount = 0;
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
    renderInlineVars();
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
        if (data.circular_heatmap_plot) {
            renderPlot('cluster-circular-heatmap-plot', data.circular_heatmap_plot, '聚类_环形热图.png');
        }

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

// ===== Reshape Module =====

// Reshape local state
const reshapeState = {
    mode: 'melt',
    // Melt
    meltIdVars: [],
    meltValueVars: [],
    // Pivot
    pivotIndexCols: [],
    // Original data preview
    originalPreview: null
};

function initReshape() {
    const btnExecute = document.getElementById('btn-reshape-execute');
    const btnExport = document.getElementById('btn-reshape-export');
    const btnUse = document.getElementById('btn-reshape-use');

    if (btnExecute) btnExecute.addEventListener('click', executeReshape);
    if (btnExport) btnExport.addEventListener('click', exportReshapeResult);
    if (btnUse) btnUse.addEventListener('click', useReshapeResult);
}

// Reshape modes have been simplified to ONLY Smart Tidy
window.setReshapeMode = function (mode) {
    reshapeState.mode = 'smart';
    state.reshapeMode = 'smart';
};

async function loadReshapePreview() {
    if (!state.dataId) return;

    try {
        const res = await fetch('/api/reshape_preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data_id: state.dataId })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        reshapeState.originalPreview = data;

        // Render original preview table
        const infoEl = document.getElementById('reshape-original-info');
        if (infoEl) infoEl.textContent = `${data.rows} 行 × ${data.columns.length} 列 (显示前 ${data.preview_rows} 行)`;

        const tableEl = document.getElementById('reshape-original-table');
        if (tableEl && data.preview.length > 0) {
            renderMiniTable(tableEl, data.preview);
        }

        // Reset and render available columns
        reshapeState.meltIdVars = [];
        reshapeState.meltValueVars = [];
        reshapeState.pivotIndexCols = [];
        renderReshapeAvailableCols();
        renderReshapeTargetBoxes();

        if (reshapeState.mode === 'pivot') {
            populatePivotDropdowns();
        }

        // Clear result
        const resultEl = document.getElementById('reshape-result-table');
        if (resultEl) resultEl.innerHTML = '<p class="text-sm text-slate-400 text-center py-8">配置参数后点击「执行转换」查看结果</p>';
        const btnExport = document.getElementById('btn-reshape-export');
        const btnUse = document.getElementById('btn-reshape-use');
        if (btnExport) btnExport.hidden = true;
        if (btnUse) btnUse.hidden = true;
    } catch (err) {
        showToast('预览加载失败: ' + err.message, 'error');
    }
}

function renderReshapeAvailableCols() {
    const container = document.getElementById('reshape-available-cols');
    const countEl = document.getElementById('reshape-available-count');
    if (!container) return;

    container.innerHTML = '';

    // Determine which columns are already used
    let usedCols = new Set();
    if (reshapeState.mode === 'melt') {
        usedCols = new Set([...reshapeState.meltIdVars, ...reshapeState.meltValueVars]);
    } else {
        usedCols = new Set([...reshapeState.pivotIndexCols]);
    }

    const available = state.columns.filter(c => !usedCols.has(c));
    if (countEl) countEl.textContent = available.length;

    available.forEach(col => {
        const tag = document.createElement('button');
        const isNum = state.columnTypes[col] === 'numeric';
        tag.className = `px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer border ${isNum
            ? 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100 hover:border-blue-300'
            : 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100 hover:border-amber-300'
            }`;
        tag.textContent = col;
        tag.title = isNum ? '数值变量 - 点击添加' : '分类变量 - 点击添加';
        tag.onclick = () => handleReshapeColClick(col);
        container.appendChild(tag);
    });
}

function handleReshapeColClick(col) {
    if (reshapeState.mode === 'melt') {
        // Auto-assign: categorical -> ID, numeric -> Value
        const isNum = state.columnTypes[col] === 'numeric';
        if (isNum) {
            reshapeState.meltValueVars.push(col);
        } else {
            reshapeState.meltIdVars.push(col);
        }
    } else {
        // Pivot: add to index cols
        reshapeState.pivotIndexCols.push(col);
    }
    renderReshapeAvailableCols();
    renderReshapeTargetBoxes();
}

function renderReshapeTargetBoxes() {
    if (reshapeState.mode === 'melt') {
        renderReshapeTagList('melt-id-vars', reshapeState.meltIdVars, 'meltIdVars',
            'bg-violet-100 text-violet-700 border-violet-300');
        renderReshapeTagList('melt-value-vars', reshapeState.meltValueVars, 'meltValueVars',
            'bg-emerald-100 text-emerald-700 border-emerald-300');

        const idCount = document.getElementById('melt-id-count');
        const valCount = document.getElementById('melt-value-count');
        if (idCount) idCount.textContent = reshapeState.meltIdVars.length;
        if (valCount) valCount.textContent = reshapeState.meltValueVars.length;
    } else {
        renderReshapeTagList('pivot-index-cols', reshapeState.pivotIndexCols, 'pivotIndexCols',
            'bg-violet-100 text-violet-700 border-violet-300');
    }
}

function renderReshapeTagList(containerId, items, stateKey, colorClass) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    if (items.length === 0) {
        container.innerHTML = '<p class="text-xs text-slate-400 w-full text-center py-3">点击下方列名添加</p>';
        return;
    }

    items.forEach(item => {
        const tag = document.createElement('span');
        tag.className = `inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium border ${colorClass} cursor-pointer hover:opacity-75 transition-opacity`;
        tag.innerHTML = `${item} <span class="text-xs opacity-60">×</span>`;
        tag.title = '点击移除';
        tag.onclick = () => {
            reshapeState[stateKey] = reshapeState[stateKey].filter(x => x !== item);
            renderReshapeAvailableCols();
            renderReshapeTargetBoxes();
        };
        container.appendChild(tag);
    });
}

function populatePivotDropdowns() {
    const colSelect = document.getElementById('pivot-columns-col');
    const valSelect = document.getElementById('pivot-values-col');
    if (!colSelect || !valSelect) return;

    // Save current selection
    const currentCol = colSelect.value;
    const currentVal = valSelect.value;

    colSelect.innerHTML = '<option value="">-- 选择 --</option>';
    valSelect.innerHTML = '<option value="">-- 选择 --</option>';

    state.columns.forEach(col => {
        // Columns dropdown: only show non-index columns
        if (!reshapeState.pivotIndexCols.includes(col)) {
            const opt1 = document.createElement('option');
            opt1.value = col;
            opt1.textContent = col;
            colSelect.appendChild(opt1);

            const opt2 = document.createElement('option');
            opt2.value = col;
            opt2.textContent = col;
            valSelect.appendChild(opt2);
        }
    });

    // Restore selection
    if (currentCol) colSelect.value = currentCol;
    if (currentVal) valSelect.value = currentVal;
}

function renderMiniTable(containerEl, data) {
    if (!data || data.length === 0) {
        containerEl.innerHTML = '<p class="text-sm text-slate-400 text-center py-4">无数据</p>';
        return;
    }

    const cols = Object.keys(data[0]);

    let html = '<table class="w-full text-xs border-collapse">';
    html += '<thead class="sticky top-0 z-10"><tr>';
    cols.forEach(col => {
        html += `<th class="px-3 py-2 text-left font-bold text-slate-600 bg-slate-100 border-b border-slate-200 whitespace-nowrap">${col}</th>`;
    });
    html += '</tr></thead><tbody>';

    data.forEach((row, idx) => {
        const bgClass = idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50';
        html += `<tr class="${bgClass} hover:bg-blue-50/50 transition-colors">`;
        cols.forEach(col => {
            const val = row[col];
            const displayVal = val === null || val === undefined ? '' : String(val);
            html += `<td class="px-3 py-1.5 border-b border-slate-100 whitespace-nowrap text-slate-700">${displayVal}</td>`;
        });
        html += '</tr>';
    });

    html += '</tbody></table>';
    containerEl.innerHTML = html;
}

async function executeReshape() {
    if (!state.dataId) return showToast('请先上传数据', 'error');

    // 智能整理模式走单独流程
    if (reshapeState.mode === 'smart') {
        return executeSmartTidy();
    }

    let payload = {
        data_id: state.dataId,
        action: reshapeState.mode
    };

    if (reshapeState.mode === 'melt') {
        if (reshapeState.meltIdVars.length === 0) return showToast('请选择至少一个 ID 列', 'error');
        if (reshapeState.meltValueVars.length === 0) return showToast('请选择至少一个值列', 'error');

        payload.id_vars = reshapeState.meltIdVars;
        payload.value_vars = reshapeState.meltValueVars;
        payload.var_name = document.getElementById('melt-var-name')?.value || '变量';
        payload.value_name = document.getElementById('melt-value-name')?.value || '值';
    } else if (reshapeState.mode === 'pivot') {
        if (reshapeState.pivotIndexCols.length === 0) return showToast('请选择至少一个索引列', 'error');

        const columnsCol = document.getElementById('pivot-columns-col')?.value;
        const valuesCol = document.getElementById('pivot-values-col')?.value;
        const aggFunc = document.getElementById('pivot-agg-func')?.value || 'first';

        if (!columnsCol) return showToast('请选择列名列', 'error');
        if (!valuesCol) return showToast('请选择值列', 'error');

        payload.index_cols = reshapeState.pivotIndexCols;
        payload.columns_col = columnsCol;
        payload.values_col = valuesCol;
        payload.agg_func = aggFunc;
    }

    const btn = document.getElementById('btn-reshape-execute');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined text-lg animate-spin">progress_activity</span> 正在转换...';
    }

    try {
        const res = await fetch('/api/reshape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        showReshapeResult(data);

    } catch (err) {
        showToast('转换失败: ' + err.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined text-lg">play_arrow</span> 执行转换';
        }
    }
}

async function exportReshapeResult() {
    if (!state.dataId) return;

    try {
        const saveDir = dom.savePathInput?.value || '';
        const res = await fetch('/api/export_reshape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data_id: state.dataId, save_dir: saveDir })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error || '导出失败');
        }

        // Trigger download
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `reshape_result.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast('Excel 导出成功', 'success');
    } catch (err) {
        showToast('导出失败: ' + err.message, 'error');
    }
}

async function useReshapeResult() {
    if (!state.dataId) return;

    try {
        const res = await fetch('/api/reshape_load_result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data_id: state.dataId })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        // Load as new data source
        loadDataSuccess(data, '整形结果数据');

        // Switch to ANOVA method by default
        const anovaRadio = document.querySelector('input[name="analysis-type"][value="anova"]');
        if (anovaRadio) {
            anovaRadio.checked = true;
            state.analysisType = 'anova';
            updateUIForMethod();
        }

        showToast('整形结果已加载为新数据源，可继续分析', 'success');
    } catch (err) {
        showToast('加载失败: ' + err.message, 'error');
    }
}

// ===== 公共结果渲染 =====
function showReshapeResult(data) {
    const resultInfo = document.getElementById('reshape-result-info');
    if (resultInfo) resultInfo.textContent = `${data.total_rows} 行 × ${data.columns.length} 列 (显示前 ${data.preview_rows} 行)`;

    const resultTable = document.getElementById('reshape-result-table');
    if (resultTable && data.preview.length > 0) {
        renderMiniTable(resultTable, data.preview);
    }

    const btnExport = document.getElementById('btn-reshape-export');
    const btnUse = document.getElementById('btn-reshape-use');
    if (btnExport) btnExport.hidden = false;
    if (btnUse) btnUse.hidden = false;

    showToast(`转换成功！共 ${data.total_rows} 行 × ${data.columns.length} 列`, 'success');
}

// ===== 智能整理 (Smart Tidy) =====

async function runSmartTidyScan() {
    if (!state.dataId) return;

    const statusEl = document.getElementById('smart-scan-status');
    const structureEl = document.getElementById('smart-structure-info');
    const optionsEl = document.getElementById('smart-options');

    if (statusEl) statusEl.innerHTML = '<div class="flex items-center justify-center gap-2 py-2"><span class="material-symbols-outlined text-violet-500 animate-spin text-lg">progress_activity</span><span class="text-xs text-slate-500">正在扫描文件结构...</span></div>';

    try {
        const res = await fetch('/api/smart_tidy_scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data_id: state.dataId })
        });
        const data = await res.json();
        if (data.error) {
            if (statusEl) statusEl.innerHTML = `<p class="text-xs text-red-500 text-center py-2">${data.error}</p>`;
            return;
        }

        // 扫描成功
        reshapeState.smartScanData = data;

        // 更新状态
        if (statusEl) statusEl.innerHTML = '<div class="flex items-center gap-2 py-1"><span class="material-symbols-outlined text-emerald-500 text-lg">check_circle</span><span class="text-xs text-emerald-600 font-bold">结构识别完成</span></div>';

        // 显示检测到的结构
        if (structureEl) {
            structureEl.hidden = false;
            const titleEl = document.getElementById('smart-title');
            const mergedEl = document.getElementById('smart-merged');
            const rowsEl = document.getElementById('smart-rows');
            const factorsEl = document.getElementById('smart-factors');
            const groupsEl = document.getElementById('smart-groups');
            const subsEl = document.getElementById('smart-subs');

            if (titleEl) titleEl.textContent = data.title || '(未检测到)';
            if (mergedEl) mergedEl.textContent = data.merged_count || 0;
            if (rowsEl) rowsEl.textContent = data.total_rows || 0;
            if (factorsEl) factorsEl.textContent = data.factor_headers?.join(', ') || '-';
            if (groupsEl) groupsEl.textContent = data.groups?.join(', ') || '(无分组)';
            if (subsEl) subsEl.textContent = data.sub_labels?.join(', ') || '(无重复标签)';
        }

        // 显示选项
        if (optionsEl) optionsEl.hidden = false;

        // 渲染原始数据预览
        if (data.preview && data.preview.length > 0) {
            const tableEl = document.getElementById('reshape-original-table');
            if (tableEl) renderMiniTable(tableEl, data.preview);
            const infoEl = document.getElementById('reshape-original-info');
            if (infoEl) infoEl.textContent = `${data.total_rows} 行 × ${data.total_cols} 列 (含 ${data.merged_count} 个合并单元格)`;
        }

    } catch (err) {
        if (statusEl) statusEl.innerHTML = `<p class="text-xs text-red-500 text-center py-2">扫描失败: ${err.message}</p>`;
    }
}

async function executeSmartTidy() {
    if (!state.dataId) return showToast('请先上传数据', 'error');

    const btn = document.getElementById('btn-reshape-execute');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined text-lg animate-spin">progress_activity</span> 正在整理...';
    }

    try {
        const dropAvg = document.getElementById('smart-drop-avg')?.checked ?? true;
        const outputFormat = document.getElementById('smart-output-format')?.value || 'semi_long';

        const res = await fetch('/api/smart_tidy_execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: state.dataId,
                drop_avg: dropAvg,
                output_format: outputFormat
            })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        showReshapeResult(data);

    } catch (err) {
        showToast('整理失败: ' + err.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined text-lg">auto_fix_high</span> 执行智能整理';
        }
    }
}

// ===== AI 智能整理 (LLM Tidy) =====

async function executeLlmTidy() {
    if (!state.dataId) return showToast('请先上传 Excel 数据', 'error');

    const apiKey = document.getElementById('llm-api-key')?.value?.trim();
    if (!apiKey) return showToast('请输入 API Key', 'error');

    const model = document.getElementById('llm-model')?.value || '';
    const btn = document.getElementById('btn-llm-tidy');
    const statusEl = document.getElementById('smart-scan-status');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">progress_activity</span> AI 分析中... (约30秒~2分钟)';
    }
    if (statusEl) {
        statusEl.innerHTML = '<div class="flex items-center justify-center gap-2 py-2"><span class="material-symbols-outlined text-blue-500 animate-spin text-lg">progress_activity</span><span class="text-xs text-blue-600">DeepSeek V3 正在分析数据结构...</span></div>';
    }

    try {
        const res = await fetch('/api/llm_tidy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: state.dataId,
                api_key: apiKey,
                model: model
            })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        // 更新状态
        if (statusEl) {
            statusEl.innerHTML = '<div class="flex items-center gap-2 py-1"><span class="material-symbols-outlined text-emerald-500 text-lg">check_circle</span><span class="text-xs text-emerald-600 font-bold">AI 整理完成</span></div>';
        }

        // 显示 AI 分析描述
        const descEl = document.getElementById('llm-description');
        const descText = document.getElementById('llm-desc-text');
        const tablesList = document.getElementById('llm-tables-list');
        if (descEl && data.description) {
            descEl.hidden = false;
            if (descText) descText.textContent = data.description;
            if (tablesList && data.tables_found && data.tables_found.length > 0) {
                tablesList.innerHTML = '<div class="font-bold text-slate-600 mb-1">检测到的表块:</div>' +
                    data.tables_found.map(t =>
                        `<div class="flex items-center gap-1 ml-2"><span class="text-blue-400">•</span>${t.name || '未命名'} <span class="text-slate-400">(${t.row_range || t.location || ''})</span></div>`
                    ).join('');
            }
        }

        showReshapeResult(data);

    } catch (err) {
        showToast('AI 整理失败: ' + err.message, 'error');
        if (statusEl) {
            statusEl.innerHTML = `<p class="text-xs text-red-500 text-center py-2">${err.message}</p>`;
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span class="material-symbols-outlined text-lg">auto_fix_high</span> 一键 AI 智能整理';
        }
    }
}
window.executeLlmTidy = executeLlmTidy;

// ===== Bar Chart Module =====

function initBarChart() {
    const addGroupBtn = document.getElementById('bc-add-group-btn');
    const addGroupSelect = document.getElementById('bc-add-group-select');
    const refreshColorsBtn = document.getElementById('bc-refresh-colors');
    const genBtn = document.getElementById('btn-gen-barchart');
    const barwidthSlider = document.getElementById('bc-barwidth');
    const fontsizeSlider = document.getElementById('bc-fontsize');

    if (addGroupBtn) {
        addGroupBtn.onclick = () => {
            const val = addGroupSelect.value;
            if (!val) return;
            if (state.barchartGroupCols.includes(val)) {
                return showToast('该列已添加', 'info');
            }
            state.barchartGroupCols.push(val);
            renderBarchartGroupList();
            refreshBarchartColors();
        };
    }

    if (refreshColorsBtn) {
        refreshColorsBtn.onclick = () => refreshBarchartColors();
    }

    if (genBtn) {
        genBtn.onclick = () => generateBarChart();
    }

    if (barwidthSlider) {
        barwidthSlider.oninput = () => {
            document.getElementById('bc-barwidth-val').textContent = barwidthSlider.value;
        };
    }

    if (fontsizeSlider) {
        fontsizeSlider.oninput = () => {
            document.getElementById('bc-fontsize-val').textContent = fontsizeSlider.value;
        };
    }

    // Download buttons
    document.querySelectorAll('.bc-download-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const format = e.target.dataset.format || 'png';
            downloadBarChart(format);
        });
    });
}

function populateBarchartSelectors() {
    const addGroupSelect = document.getElementById('bc-add-group-select');
    const valueSelect = document.getElementById('bc-value-col');

    if (!addGroupSelect || !valueSelect) return;

    // Populate add-group select
    addGroupSelect.innerHTML = '<option value="">选择列...</option>';
    state.columns.forEach(col => {
        const opt = document.createElement('option');
        opt.value = col;
        opt.textContent = col;
        addGroupSelect.appendChild(opt);
    });

    // Populate value column select (numeric only)
    valueSelect.innerHTML = '<option value="">选择数值列...</option>';
    state.columns.forEach(col => {
        if (state.columnTypes[col] === 'numeric') {
            const opt = document.createElement('option');
            opt.value = col;
            opt.textContent = col;
            valueSelect.appendChild(opt);
        }
    });

    // Restore selection
    if (state.barchartValueCol) {
        valueSelect.value = state.barchartValueCol;
    }

    valueSelect.onchange = () => {
        state.barchartValueCol = valueSelect.value;
    };

    renderBarchartGroupList();
}

function renderBarchartGroupList() {
    const list = document.getElementById('bc-group-list');
    const countEl = document.getElementById('bc-group-count');
    if (!list) return;

    list.innerHTML = '';
    countEl.textContent = state.barchartGroupCols.length;

    state.barchartGroupCols.forEach((col, idx) => {
        const li = document.createElement('li');
        li.className = 'flex items-center justify-between bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm cursor-move group';
        li.draggable = true;
        li.dataset.index = idx;

        const leftPart = document.createElement('div');
        leftPart.className = 'flex items-center gap-2';

        const dragHandle = document.createElement('span');
        dragHandle.className = 'material-symbols-outlined text-slate-300 text-sm group-hover:text-slate-500';
        dragHandle.textContent = 'drag_indicator';

        const badge = document.createElement('span');
        badge.className = 'bg-primary/10 text-primary text-[10px] px-1.5 py-0.5 rounded font-bold';
        badge.textContent = idx === state.barchartGroupCols.length - 1 ? '内层' : `第${idx + 1}层`;

        const text = document.createElement('span');
        text.textContent = col;

        leftPart.appendChild(dragHandle);
        leftPart.appendChild(badge);
        leftPart.appendChild(text);

        const removeBtn = document.createElement('button');
        removeBtn.className = 'text-slate-400 hover:text-red-500 transition-colors';
        removeBtn.innerHTML = '<span class="material-symbols-outlined text-sm">close</span>';
        removeBtn.onclick = () => {
            state.barchartGroupCols.splice(idx, 1);
            renderBarchartGroupList();
            refreshBarchartColors();
        };

        li.appendChild(leftPart);
        li.appendChild(removeBtn);

        // Drag & Drop for reordering
        li.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', idx.toString());
            li.classList.add('opacity-50');
        });
        li.addEventListener('dragend', () => {
            li.classList.remove('opacity-50');
        });
        li.addEventListener('dragover', (e) => {
            e.preventDefault();
            li.classList.add('border-primary');
        });
        li.addEventListener('dragleave', () => {
            li.classList.remove('border-primary');
        });
        li.addEventListener('drop', (e) => {
            e.preventDefault();
            li.classList.remove('border-primary');
            const fromIdx = parseInt(e.dataTransfer.getData('text/plain'));
            const toIdx = idx;
            if (fromIdx !== toIdx) {
                const [moved] = state.barchartGroupCols.splice(fromIdx, 1);
                state.barchartGroupCols.splice(toIdx, 0, moved);
                renderBarchartGroupList();
                refreshBarchartColors();
            }
        });

        list.appendChild(li);
    });
}

const DEFAULT_BAR_COLORS = [
    '#4472C4', '#ED7D31', '#A5A5A5', '#FFC000',
    '#5B9BD5', '#70AD47', '#264478', '#9B59B6',
    '#E74C3C', '#1ABC9C', '#F39C12', '#2ECC71'
];

async function refreshBarchartColors() {
    const colorList = document.getElementById('bc-color-list');
    if (!colorList) return;

    if (state.barchartGroupCols.length === 0) {
        colorList.innerHTML = '<p class="text-xs text-slate-400">选择分组列后自动显示</p>';
        return;
    }

    // Get inner group values from backend
    try {
        const res = await fetch('/api/barchart_preview_groups', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: state.dataId,
                group_cols: state.barchartGroupCols
            })
        });
        const data = await res.json();
        if (data.error) {
            colorList.innerHTML = `<p class="text-xs text-red-400">${data.error}</p>`;
            return;
        }

        const innerVals = data.inner_vals || [];
        colorList.innerHTML = '';

        if (innerVals.length === 0) {
            colorList.innerHTML = '<p class="text-xs text-slate-400">无有效分组值</p>';
            return;
        }

        // Caption
        const caption = document.createElement('p');
        caption.className = 'text-[10px] text-slate-400 mb-1';
        caption.textContent = `最内层分组: ${data.inner_col}  (共 ${innerVals.length} 组)`;
        colorList.appendChild(caption);

        innerVals.forEach((val, i) => {
            const row = document.createElement('div');
            row.className = 'flex items-center gap-2';

            const colorInput = document.createElement('input');
            colorInput.type = 'color';
            colorInput.className = 'w-8 h-8 rounded border border-slate-200 cursor-pointer';
            colorInput.value = state.barchartColors[val] || DEFAULT_BAR_COLORS[i % DEFAULT_BAR_COLORS.length];
            colorInput.onchange = () => {
                state.barchartColors[val] = colorInput.value;
            };
            // Initialize color in state
            if (!state.barchartColors[val]) {
                state.barchartColors[val] = colorInput.value;
            }

            const label = document.createElement('span');
            label.className = 'text-sm text-slate-700 truncate';
            label.textContent = val;
            label.title = val;

            row.appendChild(colorInput);
            row.appendChild(label);
            colorList.appendChild(row);
        });

    } catch (e) {
        colorList.innerHTML = `<p class="text-xs text-red-400">加载分组失败: ${e.message}</p>`;
    }
}

// Store last generated chart data for re-download in different formats
let lastBarChartData = null;

async function generateBarChart() {
    if (!state.dataId) return showToast('请先上传数据', 'error');

    if (state.barchartGroupCols.length === 0) {
        return showToast('请至少选择一个分组列', 'error');
    }

    const valueCol = document.getElementById('bc-value-col')?.value;
    if (!valueCol) return showToast('请选择数值列', 'error');

    state.barchartValueCol = valueCol;

    // Collect colors in order of inner_vals
    const barColors = [];
    const colorList = document.getElementById('bc-color-list');
    if (colorList) {
        const colorInputs = colorList.querySelectorAll('input[type=color]');
        colorInputs.forEach(inp => barColors.push(inp.value));
    }

    // 收集底部表格颜色
    const bandColors = [];
    const bandColorBox = document.getElementById('bc-band-colors');
    if (bandColorBox) {
        bandColorBox.querySelectorAll('input[type=color]').forEach(inp => bandColors.push(inp.value));
    }

    const showErrBar = document.getElementById('bc-show-errbar')?.checked ?? true;
    const showLetters = document.getElementById('bc-show-letters')?.checked ?? false;
    const yLabel = document.getElementById('bc-ylabel')?.value || '';
    const title = document.getElementById('bc-title')?.value || '';
    const barWidth = parseFloat(document.getElementById('bc-barwidth')?.value || '0.6');
    const fontSize = parseInt(document.getElementById('bc-fontsize')?.value || '10');
    const yMin = document.getElementById('bc-ymin')?.value || null;
    const yMax = document.getElementById('bc-ymax')?.value || null;
    const yStep = document.getElementById('bc-ystep')?.value || null;

    const genBtn = document.getElementById('btn-gen-barchart');
    if (genBtn) {
        genBtn.disabled = true;
        genBtn.innerHTML = '<span class="material-symbols-outlined text-sm animate-spin">progress_activity</span> 生成中...';
    }

    try {
        const res = await fetch('/api/analyze_barchart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: state.dataId,
                group_cols: state.barchartGroupCols,
                value_col: valueCol,
                bar_colors: barColors.length > 0 ? barColors : null,
                band_colors: bandColors.length > 0 ? bandColors : null,
                show_error_bars: showErrBar,
                show_letters: showLetters,
                y_label: yLabel,
                title: title,
                bar_width: barWidth,
                font_size: fontSize,
                y_min: yMin,
                y_max: yMax,
                y_step: yStep,
                output_format: 'png'
            })
        });

        const data = await res.json();
        if (data.error) throw new Error(data.error);

        lastBarChartData = data;

        // Show chart
        const preview = document.getElementById('bc-chart-preview');
        if (preview && data.plot) {
            const img = document.createElement('img');
            img.src = `data:image/${data.plot.format};base64,${data.plot.data}`;
            img.alt = 'Bar Chart';
            img.style.maxWidth = '100%';
            img.style.maxHeight = '100%';
            img.style.objectFit = 'contain';
            img.style.boxShadow = '0 2px 12px rgba(0,0,0,0.08)';
            img.style.borderRadius = '8px';
            preview.innerHTML = '';
            preview.appendChild(img);
        }

        // Show download buttons
        const dlBtns = document.getElementById('bc-download-btns');
        if (dlBtns) dlBtns.hidden = false;

        showToast('分组柱状图生成成功', 'success');

    } catch (err) {
        showToast('分组柱状图生成失败: ' + err.message, 'error');
    } finally {
        if (genBtn) {
            genBtn.disabled = false;
            genBtn.innerHTML = '<span class="material-symbols-outlined text-lg">bar_chart</span> 生成分组柱状图';
        }
    }
}

async function downloadBarChart(format) {
    if (!state.dataId || state.barchartGroupCols.length === 0 || !state.barchartValueCol) {
        return showToast('请先生成分组柱状图', 'error');
    }

    showToast(`正在导出 ${format.toUpperCase()} 格式...`, 'info');

    // Collect colors
    const barColors = [];
    const colorList = document.getElementById('bc-color-list');
    if (colorList) {
        const colorInputs = colorList.querySelectorAll('input[type=color]');
        colorInputs.forEach(inp => barColors.push(inp.value));
    }

    // 收集底部表格颜色
    const bandColors = [];
    const bandColorBox = document.getElementById('bc-band-colors');
    if (bandColorBox) {
        bandColorBox.querySelectorAll('input[type=color]').forEach(inp => bandColors.push(inp.value));
    }

    const showErrBar = document.getElementById('bc-show-errbar')?.checked ?? true;
    const showLetters = document.getElementById('bc-show-letters')?.checked ?? false;
    const yLabel = document.getElementById('bc-ylabel')?.value || '';
    const title = document.getElementById('bc-title')?.value || '';
    const barWidth = parseFloat(document.getElementById('bc-barwidth')?.value || '0.6');
    const fontSize = parseInt(document.getElementById('bc-fontsize')?.value || '10');
    const yMin = document.getElementById('bc-ymin')?.value || null;
    const yMax = document.getElementById('bc-ymax')?.value || null;
    const yStep = document.getElementById('bc-ystep')?.value || null;

    try {
        const res = await fetch('/api/analyze_barchart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: state.dataId,
                group_cols: state.barchartGroupCols,
                value_col: state.barchartValueCol,
                bar_colors: barColors.length > 0 ? barColors : null,
                band_colors: bandColors.length > 0 ? bandColors : null,
                show_error_bars: showErrBar,
                show_letters: showLetters,
                y_label: yLabel,
                title: title,
                bar_width: barWidth,
                font_size: fontSize,
                y_min: yMin,
                y_max: yMax,
                y_step: yStep,
                output_format: format
            })
        });

        const data = await res.json();
        if (data.error) throw new Error(data.error);

        if (data.plot && data.plot.data) {
            // Convert base64 to blob and download
            const byteString = atob(data.plot.data);
            const ab = new ArrayBuffer(byteString.length);
            const ia = new Uint8Array(ab);
            for (let i = 0; i < byteString.length; i++) {
                ia[i] = byteString.charCodeAt(i);
            }

            const mimeTypes = {
                'png': 'image/png',
                'pdf': 'application/pdf',
                'svg': 'image/svg+xml'
            };
            const blob = new Blob([ab], { type: mimeTypes[format] || 'application/octet-stream' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bar_chart.${format}`;
            a.click();
            URL.revokeObjectURL(url);

            showToast('导出成功', 'success');
        }

    } catch (err) {
        showToast('导出失败: ' + err.message, 'error');
    }
}

// ===== Nature Plot Logic =====
let lastNaturePlot = null;

function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, ch => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[ch]));
}

function initNaturePlot() {
    const chartType = document.getElementById('nature-chart-type');
    const genBtn = document.getElementById('btn-gen-nature');
    const downloadBtn = document.getElementById('nature-download-btn');

    if (chartType) {
        chartType.addEventListener('change', () => {
            updateNatureFieldVisibility();
            populateNatureSelectors();
        });
    }
    if (genBtn) genBtn.addEventListener('click', generateNaturePlot);
    if (downloadBtn) downloadBtn.addEventListener('click', downloadNaturePlot);
}

async function ensureNatureColumns() {
    if (state.columns.length > 0) return true;
    if (!state.dataId) return false;

    try {
        const res = await fetch('/api/data_columns', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data_id: state.dataId })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        state.columns = data.columns || [];
        state.columnTypes = data.column_types || {};
        return state.columns.length > 0;
    } catch (err) {
        showToast('读取列名失败: ' + err.message, 'error');
        return false;
    }
}

async function populateNatureSelectors() {
    const xSelect = document.getElementById('nature-x-col');
    const ySelect = document.getElementById('nature-y-cols');
    const estimateSelect = document.getElementById('nature-estimate-col');
    const lowSelect = document.getElementById('nature-ci-low-col');
    const highSelect = document.getElementById('nature-ci-high-col');
    if (!xSelect || !ySelect) return;

    const hasColumns = await ensureNatureColumns();
    if (!hasColumns) {
        xSelect.innerHTML = '<option value="">请先上传数据</option>';
        ySelect.innerHTML = '';
        [estimateSelect, lowSelect, highSelect].forEach(sel => {
            if (sel) sel.innerHTML = '';
        });
        updateNatureFieldVisibility();
        return;
    }

    const numericCols = state.columns.filter(col => state.columnTypes[col] === 'numeric');
    const optionHtml = (cols) => cols.map(col => `<option value="${escapeHtml(col)}">${escapeHtml(col)}</option>`).join('');

    xSelect.innerHTML = optionHtml(state.columns);
    ySelect.innerHTML = optionHtml(numericCols);
    [estimateSelect, lowSelect, highSelect].forEach(sel => {
        if (sel) sel.innerHTML = optionHtml(numericCols);
    });

    const chartType = document.getElementById('nature-chart-type')?.value || 'grouped_bar';
    if (chartType !== 'forest') {
        Array.from(ySelect.options).slice(0, Math.min(2, ySelect.options.length)).forEach(opt => {
            opt.selected = true;
        });
    } else {
        autoSelectNatureForestColumns();
    }
    updateNatureFieldVisibility();
}

function updateNatureFieldVisibility() {
    const chartType = document.getElementById('nature-chart-type')?.value || 'grouped_bar';
    const forestFields = document.getElementById('nature-forest-fields');
    const ySelect = document.getElementById('nature-y-cols');
    if (forestFields) forestFields.hidden = chartType !== 'forest';
    if (ySelect) ySelect.disabled = chartType === 'forest';
}

function autoSelectNatureForestColumns() {
    const numericCols = state.columns.filter(col => state.columnTypes[col] === 'numeric');
    const pick = (patterns, fallbackIndex) => {
        const found = numericCols.find(col => patterns.some(pattern => pattern.test(col)));
        return found || numericCols[fallbackIndex] || '';
    };
    const estimate = document.getElementById('nature-estimate-col');
    const low = document.getElementById('nature-ci-low-col');
    const high = document.getElementById('nature-ci-high-col');
    if (estimate) estimate.value = pick([/estimate/i, /effect/i, /coef/i, /or$/i], 0);
    if (low) low.value = pick([/low/i, /lower/i, /ci.*l/i], 1);
    if (high) high.value = pick([/high/i, /upper/i, /ci.*h/i], 2);
}

function selectedNatureYCols() {
    const select = document.getElementById('nature-y-cols');
    if (!select) return [];
    return Array.from(select.selectedOptions).map(opt => opt.value);
}

function buildNatureConfig(chartType, format) {
    const xCol = document.getElementById('nature-x-col')?.value || '';
    const yCols = selectedNatureYCols();
    const config = {
        format,
        palette: document.getElementById('nature-palette')?.value || 'nature',
        title: document.getElementById('nature-title')?.value || '',
        xlabel: document.getElementById('nature-x-label')?.value || '',
        ylabel: document.getElementById('nature-y-label')?.value || '',
        font_size: 7,
        dpi: 300
    };

    if (chartType === 'grouped_bar') {
        config.category_col = xCol;
        config.value_cols = yCols;
    } else if (chartType === 'trend') {
        config.x_col = xCol;
        config.y_cols = yCols;
    } else if (chartType === 'heatmap') {
        config.row_label_col = xCol;
        config.value_cols = yCols;
        config.annotate = document.getElementById('nature-annotate')?.checked ?? true;
    } else if (chartType === 'forest') {
        config.label_col = xCol;
        config.estimate_col = document.getElementById('nature-estimate-col')?.value || '';
        config.ci_low_col = document.getElementById('nature-ci-low-col')?.value || '';
        config.ci_high_col = document.getElementById('nature-ci-high-col')?.value || '';
    }
    return config;
}

async function generateNaturePlot() {
    if (!state.dataId) return showToast('请先上传数据', 'error');

    const chartType = document.getElementById('nature-chart-type')?.value || 'grouped_bar';
    const format = document.getElementById('nature-format')?.value || 'png';
    const config = buildNatureConfig(chartType, format);
    const needsYCols = ['grouped_bar', 'trend', 'heatmap'].includes(chartType);

    if (!config.category_col && chartType === 'grouped_bar') return showToast('请选择类别列', 'error');
    if (!config.x_col && chartType === 'trend') return showToast('请选择 X 轴列', 'error');
    if (!config.row_label_col && chartType === 'heatmap') return showToast('请选择行标签列', 'error');
    if (needsYCols && ((!config.value_cols && !config.y_cols) || (config.value_cols || config.y_cols).length === 0)) {
        return showToast('请选择至少一个数值列', 'error');
    }
    if (chartType === 'forest' && (!config.label_col || !config.estimate_col || !config.ci_low_col || !config.ci_high_col)) {
        return showToast('森林图需要标签列、估计值和置信区间列', 'error');
    }

    const btn = document.getElementById('btn-gen-nature');
    if (btn) {
        btn.disabled = true;
        btn.classList.add('opacity-70');
    }

    try {
        const res = await fetch('/api/nature_plot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data_id: state.dataId, chart_type: chartType, config })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        lastNaturePlot = data.plot;
        renderNaturePreview(data.plot);
        showToast('Nature 图生成完成', 'success');
    } catch (err) {
        showToast('生成失败: ' + err.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('opacity-70');
        }
    }
}

function renderNaturePreview(plot) {
    const preview = document.getElementById('nature-chart-preview');
    const downloadBtn = document.getElementById('nature-download-btn');
    if (!preview || !plot) return;

    const fmt = plot.format || 'png';
    const mimeTypes = {
        png: 'image/png',
        jpeg: 'image/jpeg',
        jpg: 'image/jpeg',
        svg: 'image/svg+xml',
        pdf: 'application/pdf',
        tiff: 'image/tiff'
    };

    if (['png', 'jpeg', 'jpg', 'svg'].includes(fmt)) {
        preview.innerHTML = `<img class="max-w-full max-h-full object-contain" src="data:${mimeTypes[fmt]};base64,${plot.data}" alt="Nature plot preview">`;
    } else {
        preview.innerHTML = `
            <div class="text-center text-slate-500">
                <span class="material-symbols-outlined text-[48px] mb-2 opacity-50">description</span>
                <p class="text-sm">${fmt.toUpperCase()} 已生成，可点击右上角下载</p>
            </div>
        `;
    }
    if (downloadBtn) {
        downloadBtn.hidden = false;
        downloadBtn.textContent = `下载 ${fmt.toUpperCase()}`;
    }
}

function downloadNaturePlot() {
    if (!lastNaturePlot || !lastNaturePlot.data) return showToast('请先生成图表', 'error');

    const fmt = lastNaturePlot.format || 'png';
    const mimeTypes = {
        png: 'image/png',
        jpeg: 'image/jpeg',
        jpg: 'image/jpeg',
        svg: 'image/svg+xml',
        pdf: 'application/pdf',
        tiff: 'image/tiff'
    };
    const byteString = atob(lastNaturePlot.data);
    const buffer = new ArrayBuffer(byteString.length);
    const bytes = new Uint8Array(buffer);
    for (let i = 0; i < byteString.length; i++) {
        bytes[i] = byteString.charCodeAt(i);
    }
    const blob = new Blob([buffer], { type: mimeTypes[fmt] || 'application/octet-stream' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nature_plot.${fmt}`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('导出成功', 'success');
}

// Start
document.addEventListener('DOMContentLoaded', init);
