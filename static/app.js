/**
 * 数据分析工具 - 前端交互逻辑
 */

// ===== 全局状态 =====
let appState = {
    dataId: null,
    columns: [],
    factors: [],
    targets: [],
    pcaGroups: [],  // PCA 分组变量
    results: null,
    analysisType: 'anova',  // 分析类型: 'anova', 'pca', 'cluster'
    // 聚类分析状态
    clusterFilter: 'all',   // 当前数据过滤器: 'all' 或 聚类标签
    clusterParams: {
        algorithm: 'kmeans',
        n_clusters: 3,
        linkage_method: 'ward'
    },
    // 多选相关状态
    selectedItems: [],      // 当前选中的变量名数组
    lastSelectedIndex: -1   // 上次选中的索引（用于 Shift 范围选择）
};

// ===== DOM 元素 =====
const elements = {
    // 上传区域
    uploadZone: document.getElementById('upload-zone'),
    fileInput: document.getElementById('file-input'),
    fileInfo: document.getElementById('file-info'),
    fileName: document.getElementById('file-name'),
    fileRows: document.getElementById('file-rows'),
    clearFile: document.getElementById('clear-file'),

    // 变量选择
    variableSection: document.getElementById('variable-section'),
    sourceList: document.getElementById('source-list'),
    factorList: document.getElementById('factor-list'),
    targetList: document.getElementById('target-list'),
    btnAnalyze: document.getElementById('btn-analyze'),
    btnAddAsFactor: null,   // 批量添加按钮（动态创建）
    btnAddAsTarget: null,

    // 加载状态
    loadingSection: document.getElementById('loading-section'),

    // 结果区域
    resultSection: document.getElementById('result-section'),
    resultTabs: document.getElementById('result-tabs'),
    btnExport: document.getElementById('btn-export'),
    savePathInput: document.getElementById('save-path-input'),
    btnBrowsePath: document.getElementById('btn-browse-path'),

    // 表格容器
    threeLineTable: document.getElementById('three-line-table'),
    slicedTable: document.getElementById('sliced-table'),
    slicedSepTable: document.getElementById('sliced-sep-table'),
    mainTable: document.getElementById('main-table'),
    anovaTable: document.getElementById('anova-table'),
    corrTable: document.getElementById('corr-table'),

    // PCA 表格容器
    pcaLoadingsTable: document.getElementById('pca-loadings-table'),
    pcaVarianceTable: document.getElementById('pca-variance-table'),
    pcaWeightsTable: document.getElementById('pca-weights-table'),
    pcaScoresTable: document.getElementById('pca-scores-table'),

    // PCA 图表容器
    pcaScreePlot: document.getElementById('pca-scree-plot'),
    pcaBiplot2d: document.getElementById('pca-biplot-2d'),
    pcaBiplot3d: document.getElementById('pca-biplot-3d'),

    // 双标图控制
    biplotControls: document.getElementById('biplot-controls'),
    biplotXSelect: document.getElementById('biplot-x-select'),
    biplotYSelect: document.getElementById('biplot-y-select'),
    biplotZSelect: document.getElementById('biplot-z-select'),
    biplotZLabel: document.getElementById('biplot-z-label'),

    // 分析类型选择
    appSidebar: document.getElementById('app-sidebar'),
    analysisTypeTabs: document.getElementById('analysis-type-tabs'),
    factorBox: document.getElementById('factor-box'),
    targetBoxTitle: document.getElementById('target-box-title'),
    targetBoxHint: document.getElementById('target-box-hint'),
    pcaResultTabs: document.getElementById('pca-result-tabs'),

    // PCA 分组变量
    pcaGroupBox: document.getElementById('pca-group-box'),
    pcaGroupList: document.getElementById('pca-group-list'),

    // 聚类分析
    clusterParamsPanel: document.getElementById('cluster-params-panel'),
    clusterAlgorithm: document.getElementById('cluster-algorithm'),
    clusterK: document.getElementById('cluster-k'),
    linkageGroup: document.getElementById('linkage-group'),
    linkageMethod: document.getElementById('linkage-method'),
    btnElbow: document.getElementById('btn-elbow'),
    btnExportCluster: document.getElementById('btn-export-cluster'),
    clusterResultTabs: document.getElementById('cluster-result-tabs'),
    clusterSummary: document.getElementById('cluster-summary-content'),
    clusterScatterPlot: document.getElementById('cluster-scatter-plot'),
    clusterDendrogramPlot: document.getElementById('cluster-dendrogram-plot'),
    clusterDataTable: document.getElementById('cluster-data-table'),
    clusterElbowPlot: document.getElementById('cluster-elbow-plot'),

    // 全局数据过滤器
    dataFilterPanel: document.getElementById('data-filter-panel'),
    clusterFilterSelect: document.getElementById('cluster-filter-select'),
    filterInfo: document.getElementById('filter-info'),

    // Toast
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toast-message'),

    // 密度切换
    densityToggle: document.getElementById('density-toggle')
};

// ===== 初始化 =====
function init() {
    initUpload();
    initTabs();
    initExport();
    initModal();
    initMultiSelect();
    initBrowse();
    initAnalysisTypeTabs();
    initClusterControls();  // 聚类控制初始化
    initPcaEllipseControls();  // PCA 椭圆控制初始化
    initDensityToggle(); // 数据密度切换
    initDragAndDrop(); // 拖拽功能初始化
    initHeartbeat(); // 启动心跳
}

// ===== 心跳检测 =====
function initHeartbeat() {
    setInterval(() => {
        fetch('/api/heartbeat', { method: 'POST' })
            .catch(err => {
                // 可以在这里处理断开连接的逻辑，比如显示"服务器已断开"
                console.log('Heartbeat failed:', err);
            });
    }, 2000);
}

// ===== 拖拽功能初始化 =====
function initDragAndDrop() {
    const boxes = [
        { id: 'factor-box', type: 'factors', label: '因子' },
        { id: 'target-box', type: 'targets', label: '性状' },
        { id: 'pca-group-box', type: 'pcaGroups', label: '分组变量' }
    ];

    boxes.forEach(boxInfo => {
        const box = document.getElementById(boxInfo.id);
        if (box) {
            setupDropZone(box, boxInfo.type, boxInfo.label);
        }
    });
}

// ===== 设置拖拽目标区域 =====
function setupDropZone(element, listType, label) {
    element.addEventListener('dragover', (e) => {
        e.preventDefault(); // 允许放置
        element.classList.add('drag-over');
        e.dataTransfer.dropEffect = 'copy';
    });

    element.addEventListener('dragleave', (e) => {
        // 防止子元素触发dragleave导致样式闪烁
        if (!element.contains(e.relatedTarget)) {
            element.classList.remove('drag-over');
        }
    });

    element.addEventListener('drop', (e) => {
        e.preventDefault();
        element.classList.remove('drag-over');

        try {
            const data = e.dataTransfer.getData('application/json');
            if (!data) return;

            const items = JSON.parse(data);
            if (!Array.isArray(items) || items.length === 0) return;

            let addedCount = 0;

            items.forEach(name => {
                // 1. 类型安全检查: 防止将文本列拖入性状框
                if (listType === 'targets') {
                    if (appState.columnTypes && appState.columnTypes[name] !== 'numeric') {
                        showToast(`无法添加 "${name}": 该列包含文本，性状必须是数值`, 'warning');
                        return; // 跳过此项
                    }
                }

                // 2. 检查变量是否已存在，避免重复添加
                if (listType === 'factors') {
                    if (!appState.factors.includes(name) && !appState.targets.includes(name)) {
                        appState.factors.push(name);
                        addedCount++;
                    }
                } else if (listType === 'targets') {
                    if (!appState.targets.includes(name) && !appState.factors.includes(name)) {
                        appState.targets.push(name);
                        addedCount++;
                    }
                } else if (listType === 'pcaGroups') {
                    if (!appState.pcaGroups.includes(name)) {
                        appState.pcaGroups.push(name);
                        addedCount++;
                    }
                }
            });

            if (addedCount > 0) {
                // 刷新列表
                renderSourceList();
                if (listType === 'factors') renderFactorList();
                if (listType === 'targets') renderTargetList();
                if (typeof renderPcaGroupList === 'function' && listType === 'pcaGroups') renderPcaGroupList();

                // 清除选择
                clearSelection();
                showToast(`已添加 ${addedCount} 个变量到${label}`, 'success');
            }
        } catch (err) {
            console.error('Drop error:', err);
        }
    });
}

// ===== 数据密度切换初始化 (Carbon Spec) =====
function initDensityToggle() {
    if (!elements.densityToggle) return;

    elements.densityToggle.addEventListener('click', (e) => {
        if (e.target.classList.contains('density-btn')) {
            const density = e.target.dataset.density;

            // 更新按钮状态
            elements.densityToggle.querySelectorAll('.density-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.density === density);
            });

            // 应用密度样式到结果区域容器
            if (density === 'default') {
                elements.resultSection.removeAttribute('data-density');
            } else {
                elements.resultSection.setAttribute('data-density', density);
            }

            showToast(`已切换至${e.target.textContent}视图`, 'info');
        }
    });
}

// ===== 分析类型切换初始化 =====
function initAnalysisTypeTabs() {
    if (!elements.analysisTypeTabs) return;

    elements.analysisTypeTabs.addEventListener('click', (e) => {
        const btn = e.target.closest('.nav-btn');
        if (!btn) return;

        const newType = btn.dataset.type;
        if (newType === appState.analysisType) return;

        // 更新状态
        appState.analysisType = newType;

        // 更新按钮样式
        elements.analysisTypeTabs.querySelectorAll('.nav-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.type === newType);
        });

        // 切换时清空已选变量
        appState.factors = [];
        appState.targets = [];

        // 根据分析类型调整 UI
        updateVariableUIForAnalysisType();

        // 重新渲染变量池
        renderSourceList();

        const messages = {
            'anova': '已切换到方差分析模式',
            'pca': '已切换到主成分分析模式',
            'cluster': '已切换到聚类分析模式'
        };
        showToast(messages[newType] || '已切换分析模式', 'info');
    });
}

// ===== PCA 置信椭圆控制初始化 =====
function initPcaEllipseControls() {
    const drawEllipseCheckbox = document.getElementById('pca-draw-ellipse');
    const ellipseOptions = document.getElementById('ellipse-options');
    const confidenceSlider = document.getElementById('pca-confidence-level');
    const confidenceValue = document.getElementById('confidence-value');

    if (!drawEllipseCheckbox) return;

    // 复选框切换椭圆选项显示
    drawEllipseCheckbox.addEventListener('change', () => {
        if (ellipseOptions) {
            ellipseOptions.hidden = !drawEllipseCheckbox.checked;
        }
        // 填充分组变量下拉框
        if (drawEllipseCheckbox.checked) {
            populateEllipseGroupDropdown();
        }
    });

    // 置信水平滑块更新显示
    if (confidenceSlider && confidenceValue) {
        confidenceSlider.addEventListener('input', () => {
            confidenceValue.textContent = `${confidenceSlider.value}%`;
        });
    }
}

// ===== 填充 PCA 椭圆分组变量下拉框 =====
function populateEllipseGroupDropdown() {
    const dropdown = document.getElementById('pca-ellipse-group');
    if (!dropdown) return;

    // 清空并重新填充
    dropdown.innerHTML = '<option value="">-- 选择因子变量 --</option>';

    // 使用因子列表（如果有）或从 columns 中筛选分类变量
    const groupOptions = appState.factors.length > 0
        ? appState.factors
        : appState.columns.filter(col =>
            appState.columnTypes && appState.columnTypes[col] === 'categorical'
        );

    // 如果没有因子，使用所有列
    const options = groupOptions.length > 0 ? groupOptions : appState.columns;

    options.forEach(col => {
        const option = document.createElement('option');
        option.value = col;
        option.textContent = col;
        dropdown.appendChild(option);
    });
}

// ===== 根据分析类型更新变量选择 UI =====
function updateVariableUIForAnalysisType() {
    const isPCA = appState.analysisType === 'pca';
    const isCluster = appState.analysisType === 'cluster';
    const isANOVA = appState.analysisType === 'anova';

    // 因子选择框：方差分析和聚类分析都显示
    if (elements.factorBox) {
        elements.factorBox.style.display = (isANOVA || isCluster) ? 'block' : 'none';

        // 更新因子框标题
        const factorTitle = elements.factorBox.querySelector('h3');
        if (factorTitle) {
            factorTitle.textContent = isCluster ? '🏷️ 标签/分组变量' : '🌱 因子 (X)';
        }

        // 更新提示
        const factorHint = elements.factorBox.querySelector('.hint-text');
        if (factorHint) {
            factorHint.textContent = isCluster ? '选择用于标记样本的列（如品种、处理，不参与聚类计算）' : '分类变量，如：品种、处理';
        }
    }

    // PCA 分组变量框：仅 PCA 模式显示
    const pcaGroupSection = document.getElementById('pca-group-section');
    if (pcaGroupSection) {
        pcaGroupSection.hidden = !isPCA;
    }
    if (elements.pcaGroupBox) {
        elements.pcaGroupBox.hidden = !isPCA;
    }

    // 聚类参数面板：仅聚类模式显示
    if (elements.clusterParamsPanel) {
        elements.clusterParamsPanel.hidden = !isCluster;
    }

    // PCA 置信椭圆面板：仅 PCA 模式显示
    const pcaEllipsePanel = document.getElementById('pca-ellipse-panel');
    if (pcaEllipsePanel) {
        pcaEllipsePanel.hidden = !isPCA;
    }

    // 性状选择框标题和提示
    if (elements.targetBoxTitle) {
        if (isCluster) {
            elements.targetBoxTitle.textContent = '🔢 聚类特征';
        } else if (isPCA) {
            elements.targetBoxTitle.textContent = '🔢 数值变量';
        } else {
            elements.targetBoxTitle.textContent = '📈 性状 (Y)';
        }
    }
    if (elements.targetBoxHint) {
        if (isCluster) {
            elements.targetBoxHint.textContent = '选择用于聚类分析的数值变量（至少选择2个）';
        } else if (isPCA) {
            elements.targetBoxHint.textContent = '选择用于主成分分析的数值变量（至少选择2个）';
        } else {
            elements.targetBoxHint.textContent = '数值变量，如：产量、株高';
        }
    }

    // 清空 PCA 分组选择
    if (isPCA) {
        appState.pcaGroups = [];
        renderPcaGroupList();
    }

    // 更新批量添加按钮文字
    const btnAddFactor = document.getElementById('btn-add-factor');
    if (btnAddFactor) {
        if (isPCA) {
            btnAddFactor.textContent = '✚ 设为分组';
        } else if (isCluster) {
            btnAddFactor.textContent = '✚ 设为标签';
        } else {
            btnAddFactor.textContent = '✚ 设为因子';
        }
    }
}

// ===== 渲染 PCA 分组变量列表 =====
function renderPcaGroupList() {
    if (!elements.pcaGroupList) return;

    let html = '';
    appState.pcaGroups.forEach(col => {
        html += `<li class="variable-item selected" data-column="${escapeHtml(col)}">${escapeHtml(col)}</li>`;
    });
    elements.pcaGroupList.innerHTML = html;

    // 绑定双击移除事件
    elements.pcaGroupList.querySelectorAll('.variable-item').forEach(item => {
        item.addEventListener('dblclick', () => {
            const col = item.dataset.column;
            appState.pcaGroups = appState.pcaGroups.filter(c => c !== col);
            renderPcaGroupList();
            renderSourceList();
        });
    });
}

// ===== 路径浏览初始化 =====
function initBrowse() {
    if (!elements.btnBrowsePath) return;

    elements.btnBrowsePath.addEventListener('click', async () => {
        try {
            showToast('请在弹出的窗口中选择文件夹...', 'info');
            const response = await fetch('/api/select_directory');
            const data = await response.json();

            if (data.success && data.directory) {
                elements.savePathInput.value = data.directory;
                showToast('已选择路径', 'success');
            } else if (data.message) {
                showToast(data.message, 'info');
            }
        } catch (error) {
            showToast('选择路径失败: ' + error.message, 'error');
        }
    });
}

// ===== 模态框初始化 =====
function initModal() {
    elements.sheetModal = document.getElementById('sheet-modal');
    elements.sheetList = document.getElementById('sheet-list');
    elements.closeModal = document.getElementById('close-modal');

    // 关闭模态框
    elements.closeModal.addEventListener('click', () => {
        elements.sheetModal.classList.remove('active');
        // 清除文件选择，允许重新上传
        elements.fileInput.value = '';
    });
}

// ===== 多选功能初始化 =====
function initMultiSelect() {
    // 点击空白处取消选择
    document.addEventListener('click', (e) => {
        // 如果点击的不是变量列表内的元素，清除选择
        if (!e.target.closest('.variable-list') && !e.target.closest('.batch-actions')) {
            clearSelection();
        }
    });
}

// ===== 文件上传 =====
function initUpload() {
    // 获取新元素
    const uploadBtn = document.getElementById('upload-btn');
    const dropOverlay = document.getElementById('drop-overlay');
    const dataInfo = document.getElementById('data-info');

    // 点击上传按钮 (工具栏)
    if (uploadBtn) {
        uploadBtn.addEventListener('click', () => {
            elements.fileInput.click();
        });
    }

    // 兼容旧的 upload-zone (如果存在)
    if (elements.uploadZone) {
        elements.uploadZone.addEventListener('click', () => {
            elements.fileInput.click();
        });
    }

    // 文件选择
    elements.fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadFile(e.target.files[0]);
        }
    });

    // 全局拖拽上传
    document.body.addEventListener('dragover', (e) => {
        e.preventDefault();
        // 仅当拖拽的是文件时显示遮罩 (避免与变量拖拽冲突)
        if (dropOverlay && e.dataTransfer.types && Array.from(e.dataTransfer.types).includes('Files')) {
            dropOverlay.classList.add('active');
        }
    });

    document.body.addEventListener('dragleave', (e) => {
        // 只有离开整个 body 才隐藏
        if (e.relatedTarget === null) {
            if (dropOverlay) dropOverlay.classList.remove('active');
        }
    });

    document.body.addEventListener('drop', (e) => {
        e.preventDefault();
        if (dropOverlay) dropOverlay.classList.remove('active');
        if (e.dataTransfer.files.length > 0) {
            uploadFile(e.dataTransfer.files[0]);
        }
    });

    // 清除文件
    if (elements.clearFile) {
        elements.clearFile.addEventListener('click', clearData);
    }

    // 分析按钮
    if (elements.btnAnalyze) {
        elements.btnAnalyze.addEventListener('click', runAnalysis);
    }

    // 批量添加按钮
    const btnAddFactor = document.getElementById('btn-add-factor');
    const btnAddTarget = document.getElementById('btn-add-target');

    console.log('initUpload: btnAddFactor =', btnAddFactor);
    console.log('initUpload: btnAddTarget =', btnAddTarget);

    if (btnAddFactor) {
        btnAddFactor.addEventListener('click', () => {
            console.log('btn-add-factor clicked!');
            // PCA 模式添加到分组变量，其他模式添加到因子
            if (appState.analysisType === 'pca') {
                addSelectedToList('pcaGroups');
            } else {
                addSelectedToList('factors');
            }
        });
        console.log('btn-add-factor event bound');
    } else {
        console.error('btn-add-factor NOT FOUND!');
    }

    if (btnAddTarget) {
        btnAddTarget.addEventListener('click', () => {
            console.log('btn-add-target clicked!');
            addSelectedToList('targets');
        });
        console.log('btn-add-target event bound');
    } else {
        console.error('btn-add-target NOT FOUND!');
    }
}

// ===== 添加选中变量到指定列表 =====
function addSelectedToList(listType) {
    const sourceList = document.getElementById('source-list');
    console.log('addSelectedToList called, listType:', listType);
    console.log('sourceList element:', sourceList);

    if (!sourceList) {
        console.error('source-list not found!');
        return;
    }

    // 查找所有选中项
    const selectedItems = sourceList.querySelectorAll('.variable-item.selected');
    console.log('Selected items found:', selectedItems.length);

    if (selectedItems.length === 0) {
        showToast('请先在变量列表中选择变量', 'warning');
        return;
    }

    let addedCount = 0;
    selectedItems.forEach(item => {
        // 使用 dataset.name 而不是 dataset.column (与 createVariableItem 一致)
        const col = item.dataset.name || item.dataset.column;
        console.log('Processing item:', item.textContent, 'name:', col);
        if (!col) return;

        // 根据目标列表类型添加
        if (listType === 'factors') {
            if (!appState.factors.includes(col) && !appState.targets.includes(col)) {
                appState.factors.push(col);
                addedCount++;
                console.log('Added to factors:', col);
            }
        } else if (listType === 'targets') {
            if (!appState.targets.includes(col) && !appState.factors.includes(col)) {
                appState.targets.push(col);
                addedCount++;
                console.log('Added to targets:', col);
            }
        } else if (listType === 'pcaGroups') {
            if (!appState.pcaGroups.includes(col)) {
                appState.pcaGroups.push(col);
                addedCount++;
            }
        }
    });

    console.log('After adding - factors:', appState.factors, 'targets:', appState.targets);

    // 刷新显示
    renderSourceList();
    renderFactorList();
    renderTargetList();
    if (typeof renderPcaGroupList === 'function') {
        renderPcaGroupList();
    }

    const labels = { 'factors': '因子', 'targets': '性状', 'pcaGroups': '分组变量' };
    showToast(`已添加 ${addedCount} 个变量到${labels[listType]}`, 'success');
}

// ===== 上传文件到服务器 =====
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        showToast('正在上传文件...', 'info');

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            showToast(data.error, 'error');
            return;
        }

        // 处理多 Sheet 选择
        if (data.need_sheet_selection || data.status === 'select_sheet') {
            showSheetModal(data.sheets, data.temp_id);
            return;
        }

        handleLoadedData(data, file.name);

    } catch (error) {
        showToast('上传失败: ' + error.message, 'error');
    }
}

// ===== 显示 Sheet 选择模态框 =====
function showSheetModal(sheets, tempId) {
    elements.sheetList.innerHTML = '';

    sheets.forEach(sheet => {
        const div = document.createElement('div');
        div.className = 'sheet-item';
        div.textContent = sheet;
        div.addEventListener('click', () => loadSheet(tempId, sheet));
        elements.sheetList.appendChild(div);
    });

    elements.sheetModal.classList.add('active');
}

// ===== 加载指定 Sheet =====
async function loadSheet(tempId, sheetName) {
    try {
        elements.sheetModal.classList.remove('active');
        showToast(`正在加载工作表: ${sheetName}...`, 'info');

        const response = await fetch('/api/load_sheet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                temp_id: tempId,
                sheet_name: sheetName
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast(data.error, 'error');
            return;
        }

        // 获取原始文件名（如果有缓存的话，或者这里简化处理）
        // 这里可以直接用当前显示的文件名，或者从后端返回
        // 假设 fileInput 还有值
        const originalName = elements.fileInput.files[0] ? elements.fileInput.files[0].name : 'Data.xlsx';

        handleLoadedData(data, `${originalName} [${sheetName}]`);

    } catch (error) {
        showToast('加载失败: ' + error.message, 'error');
    }
}

// ===== 处理加载成功的数据 =====
function handleLoadedData(data, fileNameDisplay) {
    console.log('Loaded data:', data); // Debugging

    // 保存状态
    appState.dataId = data.data_id;
    appState.columns = data.columns || [];

    // 保存列类型信息
    appState.columnTypes = data.column_types || {};
    appState.suggestedFactors = data.suggested_factors || [];
    appState.suggestedIndicators = data.suggested_indicators || [];

    // 重置选择
    appState.factors = [];
    appState.targets = [];
    appState.pcaGroups = [];

    // 更新UI - 工具栏数据信息
    const dataInfo = document.getElementById('data-info');
    if (dataInfo) {
        dataInfo.hidden = false;
    }

    elements.fileName.textContent = fileNameDisplay;
    const rowCount = data.rows !== undefined ? data.rows : '?';
    elements.fileRows.textContent = `共 ${rowCount} 行`;

    // 兼容旧的 file-info 显示
    if (elements.fileInfo) {
        elements.fileInfo.hidden = false;
    }

    // 填充变量池
    renderSourceList();

    // 显示变量选择区域
    if (elements.variableSection) {
        elements.variableSection.hidden = false;
    }
    if (elements.appSidebar) {
        elements.appSidebar.hidden = false;
    }

    // 隐藏结果区域
    if (elements.resultSection) {
        elements.resultSection.hidden = true;
    }

    showToast('数据加载成功！', 'success');
}

// ===== 渲染变量池 =====
function renderSourceList() {
    elements.sourceList.innerHTML = '';

    if (!appState.columns || !Array.isArray(appState.columns)) {
        console.error('appState.columns is invalid:', appState.columns);
        return;
    }

    // 分离变量类型
    const numericCols = [];
    const categoricalCols = [];

    // 如果没有列类型信息，尝试推断 (向后兼容)
    const hasTypeInfo = appState.columnTypes && Object.keys(appState.columnTypes).length > 0;

    appState.columns.forEach(col => {
        // 排除已选变量
        if (appState.factors.includes(col) ||
            appState.targets.includes(col) ||
            appState.pcaGroups.includes(col)) {
            return;
        }

        if (hasTypeInfo) {
            if (appState.columnTypes[col] === 'numeric') {
                numericCols.push(col);
            } else {
                categoricalCols.push(col);
            }
        } else {
            // 没有类型信息时，默认全部放入数值列表（之前的行为）
            numericCols.push(col);
        }
    });

    // 渲染分类变量区 (Factors)
    if (categoricalCols.length > 0) {
        const factorList = document.createElement('ul');
        factorList.className = 'variable-sublist list-categorical';
        categoricalCols.forEach((col, index) => {
            // 注意：这里需要传递正确的全局索引或使用名称索引
            const li = createVariableItem(col, 'source');
            factorList.appendChild(li);
        });
        elements.sourceList.appendChild(factorList);
    }

    // 渲染数值变量区 (Indicators)
    if (numericCols.length > 0) {
        const indicatorList = document.createElement('ul');
        indicatorList.className = 'variable-sublist list-numeric';
        numericCols.forEach((col, index) => {
            const li = createVariableItem(col, 'source');
            indicatorList.appendChild(li);
        });
        elements.sourceList.appendChild(indicatorList);
    }

    // 如果两个都为空且有列，显示提示
    if (categoricalCols.length === 0 && numericCols.length === 0 && appState.columns.length > 0) {
        elements.sourceList.innerHTML = '<div style="padding:10px;color:#888;text-align:center">所有变量已被选中</div>';
    }

    // 渲染批量操作按钮
    renderBatchActions();

    renderFactorList();
    renderTargetList();

    // 更新选择状态显示
    updateSelectionUI();
}

// ===== 渲染批量操作区域 =====
function renderBatchActions() {
    let batchActionsDiv = document.querySelector('.batch-actions');

    // Determine labels based on analysis type
    const isPCA = appState.analysisType === 'pca';

    // Group Button (Top): "Set as Factor" or "Group by Color"
    const groupBtnLabel = isPCA ? '➕ 添加为分组 (Group)' : '➕ 设为因子 (X)';
    const groupBtnType = isPCA ? 'pca-group' : 'factor';

    // Trait Button (Bottom): "Set as Trait" or "Set as Variable"
    const traitBtnLabel = isPCA ? '➕ 设为变量 (Var)' : '➕ 设为性状 (Y)';

    if (!batchActionsDiv) {
        batchActionsDiv = document.createElement('div');
        batchActionsDiv.className = 'batch-actions';
        batchActionsDiv.innerHTML = `
            <div class="batch-hint">
                <div class="batch-main-actions">
                    <button class="btn btn-medium btn-purple-dark" id="btn-main-group">${groupBtnLabel}</button>
                    <button class="btn btn-medium btn-purple-light" id="btn-main-trait">${traitBtnLabel}</button>
                </div>
                <div class="batch-secondary-actions">
                    <div class="helper-text">
                        <span class="hint-icon">💡</span> Ctrl/Shift 多选，或双击
                    </div>
                    <div class="action-links">
                        <button class="btn-link" onclick="selectAllVariables()">全选</button>
                        <span class="divider">|</span>
                        <button class="btn-link" onclick="clearSelection()">取消</button>
                    </div>
                </div>
            </div>
        `;
        const sourceBox = elements.sourceList.closest('.variable-box');
        if (sourceBox) {
            sourceBox.appendChild(batchActionsDiv);
        }

        // Bind events using delegation or direct attachment
        // Re-attach listeners every time? No, if we replace innerHTML, listeners are lost.
        // But here we create div only if it doesn't exist.
        // If it exists, we update labels below.
    }

    // Use stable IDs to update text if element exists
    const btnGroup = document.getElementById('btn-main-group');
    const btnTrait = document.getElementById('btn-main-trait');

    if (btnGroup) {
        btnGroup.textContent = groupBtnLabel;
        // Remove old listeners? The simplest way is to clone node or set onclick.
        // For simplicity in this vanilla JS app without event delegation helper:
        btnGroup.onclick = () => addSelectedVariables(groupBtnType);
    }

    if (btnTrait) {
        btnTrait.textContent = traitBtnLabel;
        btnTrait.onclick = () => addSelectedVariables('target');
    }
}

// ===== 更新选择状态 UI =====
function updateSelectionUI() {
    const count = appState.selectedItems.length;

    const btnGroup = document.getElementById('btn-main-group');
    const btnTrait = document.getElementById('btn-main-trait');

    if (btnGroup) {
        btnGroup.disabled = count === 0;
    }
    if (btnTrait) {
        btnTrait.disabled = count === 0;
    }

    // 更新变量项的选中样式
    document.querySelectorAll('#source-list .variable-item').forEach(li => {
        const name = li.dataset.name;
        li.classList.toggle('selected', appState.selectedItems.includes(name));
    });
}

// ===== 清除选择 =====
function clearSelection() {
    appState.selectedItems = [];
    appState.lastSelectedIndex = -1;
    updateSelectionUI();
}

// ===== 批量添加变量 =====
function addSelectedVariables(type) {
    if (appState.selectedItems.length === 0) return;

    const addedCount = appState.selectedItems.length;

    appState.selectedItems.forEach(name => {
        if (type === 'factor') {
            if (!appState.factors.includes(name)) {
                appState.factors.push(name);
            }
        } else if (type === 'pca-group') {
            if (!appState.pcaGroups.includes(name)) {
                appState.pcaGroups.push(name);
            }
        } else {
            if (!appState.targets.includes(name)) {
                appState.targets.push(name);
            }
        }
    });

    // 清除选择并重新渲染
    clearSelection();
    renderSourceList();

    // 渲染 PCA 分组列表
    if (type === 'pca-group') {
        renderPcaGroupList();
    }

    const typeLabel = type === 'factor' ? '因子' : (type === 'pca-group' ? '分组变量' : '性状');
    showToast(`已添加 ${addedCount} 个${typeLabel}`, 'success');
}

// ===== 渲染因子列表 =====
function renderFactorList() {
    const factorList = elements.factorList || document.getElementById('factor-list');
    if (!factorList) {
        console.error('renderFactorList: factor-list element not found');
        return;
    }
    factorList.innerHTML = '';
    console.log('renderFactorList: appState.factors =', appState.factors);
    appState.factors.forEach(col => {
        const li = createVariableItem(col, 'factor');
        factorList.appendChild(li);
    });
}

// ===== 渲染性状列表 =====
function renderTargetList() {
    const targetList = elements.targetList || document.getElementById('target-list');
    if (!targetList) {
        console.error('renderTargetList: target-list element not found');
        return;
    }
    targetList.innerHTML = '';
    console.log('renderTargetList: appState.targets =', appState.targets);
    appState.targets.forEach(col => {
        const li = createVariableItem(col, 'target');
        targetList.appendChild(li);
    });
}

// ===== 创建变量项 =====
function createVariableItem(name, type, index = -1) {
    const li = document.createElement('li');
    li.className = 'variable-item';
    li.dataset.name = name;
    li.dataset.index = index;

    // 内容容器
    const content = document.createElement('span');
    content.textContent = name;
    li.appendChild(content);

    // 针对 PCA 和 Cluster 模式下的性状变量，添加正向化控制
    if (type === 'target' && (appState.analysisType === 'pca' || appState.analysisType === 'cluster')) {
        const controls = document.createElement('div');
        controls.className = 'target-controls';
        controls.style.display = 'flex';
        controls.style.gap = '5px';
        controls.style.marginLeft = '10px';
        controls.style.alignItems = 'center';

        // 类型选择
        const select = document.createElement('select');
        select.className = 'norm-select';
        select.style.padding = '2px';
        select.style.fontSize = '0.8rem';
        select.innerHTML = `
            <option value="benefit">正向</option>
            <option value="cost">负向</option>
            <option value="interval">区间</option>
        `;

        // 区间参数输入框
        const paramsDiv = document.createElement('div');
        paramsDiv.className = 'interval-params';
        paramsDiv.style.display = 'none'; // 默认隐藏
        paramsDiv.style.gap = '2px';

        const inputA = document.createElement('input');
        inputA.type = 'number';
        inputA.className = 'param-a';
        inputA.placeholder = 'Min';
        inputA.style.width = '50px';
        inputA.style.fontSize = '0.8rem';
        inputA.style.padding = '2px';

        const inputB = document.createElement('input');
        inputB.type = 'number';
        inputB.className = 'param-b';
        inputB.placeholder = 'Max';
        inputB.style.width = '50px';
        inputB.style.fontSize = '0.8rem';
        inputB.style.padding = '2px';

        paramsDiv.appendChild(inputA);
        paramsDiv.appendChild(inputB);

        // 事件监听
        select.addEventListener('change', (e) => {
            e.stopPropagation();
            paramsDiv.style.display = select.value === 'interval' ? 'flex' : 'none';
        });

        // 防止点击输入框触发移除
        [select, inputA, inputB].forEach(el => {
            el.addEventListener('click', (e) => e.stopPropagation());
        });

        controls.appendChild(select);
        controls.appendChild(paramsDiv);
        li.appendChild(controls);
    }

    if (type === 'source') {
        // 开启拖拽
        li.draggable = true;

        // 拖拽开始
        li.addEventListener('dragstart', (e) => {
            let dragItems = [];
            // 如果拖拽的是已选中的项，则拖拽所有选中项
            if (appState.selectedItems.includes(name)) {
                dragItems = [...appState.selectedItems];
                // 给所有选中项添加拖拽样式
                document.querySelectorAll('#source-list .variable-item.selected').forEach(item => {
                    item.classList.add('dragging');
                });
            } else {
                // 否则只拖拽当前项
                dragItems = [name];
                li.classList.add('dragging');
            }

            e.dataTransfer.setData('application/json', JSON.stringify(dragItems));
            e.dataTransfer.effectAllowed = 'copy';
        });

        // 拖拽结束
        li.addEventListener('dragend', (e) => {
            document.querySelectorAll('.variable-item.dragging').forEach(item => {
                item.classList.remove('dragging');
            });
        });

        // 支持多选行为
        li.addEventListener('click', (e) => {
            e.stopPropagation();
            handleVariableClick(name, index, e);
        });

        // 双击直接添加为性状（快捷操作）
        li.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            clearSelection();
            addVariable(name, 'target');
            showToast(`"${name}" 已添加为性状`, 'success');
        });
    } else {
        // 添加移除按钮
        const removeBtn = document.createElement('span');
        removeBtn.className = 'remove';
        removeBtn.textContent = '×';
        removeBtn.style.marginLeft = 'auto'; // 确保在最右侧
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            removeVariable(name, type);
        });
        li.appendChild(removeBtn);
    }

    return li;
}

// ===== 处理变量点击（支持多选） =====
function handleVariableClick(name, index, event) {
    // 获取当前渲染的列表项（视觉顺序）
    const allItems = Array.from(document.querySelectorAll('#source-list .variable-item'));
    const visualIndex = allItems.findIndex(item => item.dataset.name === name);

    if (visualIndex === -1) return;

    if (event.ctrlKey || event.metaKey) {
        // Ctrl/Cmd + 点击：切换选择
        const selectedIndex = appState.selectedItems.indexOf(name);
        if (selectedIndex > -1) {
            appState.selectedItems.splice(selectedIndex, 1);
        } else {
            appState.selectedItems.push(name);
        }
        appState.lastSelectedIndex = visualIndex; // 记录视觉索引
    } else if (event.shiftKey && appState.lastSelectedIndex !== -1) {
        // Shift + 点击：范围选择 (基于视觉及其)
        const start = Math.min(appState.lastSelectedIndex, visualIndex);
        const end = Math.max(appState.lastSelectedIndex, visualIndex);

        // 清除之前的选择（Shift通常是连续选择，或者保留之前的？通常行为是保留Ctrl选的，但这里简化为扩展当前范围）
        // 简单实现：保留已选的，添加范围内的
        // 或者：如果只想选范围，可以先清空。这里采用添加模式。
        if (!event.ctrlKey) {
            appState.selectedItems = []; // 如果没按Ctrl，重置选择
        }

        for (let i = start; i <= end; i++) {
            const itemName = allItems[i].dataset.name;
            if (!appState.selectedItems.includes(itemName)) {
                appState.selectedItems.push(itemName);
            }
        }
    } else {
        // 普通点击：单选
        appState.selectedItems = [name];
        appState.lastSelectedIndex = visualIndex;
    }

    updateSelectionUI();
}

// ===== 显示变量添加菜单 =====
function showVariableMenu(name, element) {
    // 简化处理：直接显示选项
    const rect = element.getBoundingClientRect();

    // 创建临时菜单
    const menu = document.createElement('div');
    menu.style.cssText = `
        position: fixed;
        top: ${rect.bottom + 5}px;
        left: ${rect.left}px;
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 1000;
        overflow: hidden;
    `;

    const btnFactor = document.createElement('button');
    btnFactor.textContent = '📌 添加为因子 (X)';
    btnFactor.style.cssText = 'display: block; width: 100%; padding: 10px 16px; border: none; background: none; text-align: left; cursor: pointer;';
    btnFactor.addEventListener('click', () => {
        addVariable(name, 'factor');
        document.body.removeChild(menu);
    });
    btnFactor.addEventListener('mouseenter', () => btnFactor.style.background = '#e3f2fd');
    btnFactor.addEventListener('mouseleave', () => btnFactor.style.background = 'none');

    const btnTarget = document.createElement('button');
    btnTarget.textContent = '📈 添加为性状 (Y)';
    btnTarget.style.cssText = 'display: block; width: 100%; padding: 10px 16px; border: none; background: none; text-align: left; cursor: pointer;';
    btnTarget.addEventListener('click', () => {
        addVariable(name, 'target');
        document.body.removeChild(menu);
    });
    btnTarget.addEventListener('mouseenter', () => btnTarget.style.background = '#e8f5e9');
    btnTarget.addEventListener('mouseleave', () => btnTarget.style.background = 'none');

    menu.appendChild(btnFactor);
    menu.appendChild(btnTarget);
    document.body.appendChild(menu);

    // 点击其他地方关闭
    const closeMenu = (e) => {
        if (!menu.contains(e.target)) {
            if (document.body.contains(menu)) {
                document.body.removeChild(menu);
            }
            document.removeEventListener('click', closeMenu);
        }
    };
    setTimeout(() => document.addEventListener('click', closeMenu), 0);
}

// ===== 添加变量 =====
function addVariable(name, type) {
    if (type === 'factor') {
        appState.factors.push(name);
    } else {
        appState.targets.push(name);
    }
    renderSourceList();
}

// ===== 移除变量 =====
function removeVariable(name, type) {
    if (type === 'factor') {
        appState.factors = appState.factors.filter(f => f !== name);
    } else {
        appState.targets = appState.targets.filter(t => t !== name);
    }
    renderSourceList();
}

// ===== 清除数据 =====
function clearData() {
    const currentAnalysisType = appState.analysisType;
    appState = {
        dataId: null,
        columns: [],
        factors: [],
        targets: [],
        results: null,
        analysisType: currentAnalysisType,  // 保留分析类型
        selectedItems: [],
        lastSelectedIndex: -1
    };

    elements.fileInput.value = '';
    elements.fileInfo.hidden = true;
    elements.variableSection.hidden = true;
    elements.resultSection.hidden = true;
}

// ===== 执行分析 =====
async function runAnalysis() {
    const isPCA = appState.analysisType === 'pca';
    const isCluster = appState.analysisType === 'cluster';

    // 聚类分析使用单独的函数
    if (isCluster) {
        await runClusterAnalysis();
        return;
    }

    // 方差分析需要因子
    if (!isPCA && appState.factors.length === 0) {
        showToast('请至少选择1个因子 (X)', 'error');
        return;
    }

    // 检查变量选择
    if (appState.targets.length === 0) {
        showToast(isPCA ? '请至少选择1个数值变量' : '请至少选择1个性状 (Y)', 'error');
        return;
    }

    // PCA 至少需要2个变量
    if (isPCA && appState.targets.length < 2) {
        showToast('主成分分析至少需要 2 个数值变量', 'error');
        return;
    }

    // 显示加载状态
    elements.loadingSection.hidden = false;
    elements.resultSection.hidden = true;
    elements.btnAnalyze.disabled = true;

    try {
        // 根据分析类型选择 API
        const apiUrl = isPCA ? '/api/analyze_pca' : '/api/analyze';
        const requestBody = {
            data_id: appState.dataId,
            factors: appState.factors,
            targets: appState.targets
        };

        // PCA 模式下处理配置
        if (isPCA || isCluster) {
            // 1. 添加分组变量 (仅 PCA)
            if (isPCA && appState.pcaGroups.length > 0) {
                requestBody.group_by = appState.pcaGroups;
            }

            // 2. 收集正向化配置
            const targetConfigs = {};
            const targetItems = document.querySelectorAll('#target-list .variable-item');

            targetItems.forEach(item => {
                const name = item.dataset.name;
                const select = item.querySelector('.norm-select');

                if (select) {
                    const type = select.value;
                    const config = { type: type };

                    if (type === 'interval') {
                        const inputA = item.querySelector('.param-a');
                        const inputB = item.querySelector('.param-b');
                        config.a = inputA ? parseFloat(inputA.value) : 0;
                        config.b = inputB ? parseFloat(inputB.value) : 0;
                    }

                    targetConfigs[name] = config;
                }
            });

            requestBody.target_configs = targetConfigs;
        }

        // 添加聚类过滤器（如果有）
        if (appState.clusterFilter && appState.clusterFilter !== 'all') {
            requestBody.cluster_filter = appState.clusterFilter;
        }

        const response = await fetch(`${apiUrl}?t=${new Date().getTime()}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.error) {
            showToast(data.error, 'error');
            elements.loadingSection.hidden = true;
            elements.btnAnalyze.disabled = false;
            return;
        }

        // 保存结果
        appState.results = data;
        appState.results.analysisType = appState.analysisType;

        // 渲染结果
        if (isPCA) {
            renderPCAResults(data);
        } else {
            renderResults(data);
        }

        // 切换结果 Tab 显示
        updateResultTabsForAnalysisType();

        // 显示结果区域
        elements.loadingSection.hidden = true;
        elements.resultSection.hidden = false;
        elements.btnAnalyze.disabled = false;

        // 滚动到结果
        elements.resultSection.scrollIntoView({ behavior: 'smooth' });

        showToast(isPCA ? 'PCA 分析完成！' : '分析完成！', 'success');

    } catch (error) {
        showToast('分析失败: ' + error.message, 'error');
        elements.loadingSection.hidden = true;
        elements.btnAnalyze.disabled = false;
    }
}

// ===== 渲染结果 =====
function renderResults(data) {
    // 组内比较 (分列) - 默认显示
    if (data.sliced_sep) {
        renderDataTable(elements.slicedSepTable, data.sliced_sep);
    }

    // 组内比较 (组合)
    if (data.sliced_comb) {
        renderDataTable(elements.slicedTable, data.sliced_comb);
    }

    // 主效应
    if (data.main) {
        renderDataTable(elements.mainTable, data.main);
    }

    // 方差分析
    if (data.anova) {
        renderDataTable(elements.anovaTable, data.anova);
    }

    // 相关分析
    if (data.corr) {
        renderDataTable(elements.corrTable, data.corr);
    }
}

// ===== 渲染 PCA 结果 (增强版) =====
function renderPCAResults(data) {
    // 主成分载荷
    if (data.loadings && elements.pcaLoadingsTable) {
        renderDataTable(elements.pcaLoadingsTable, data.loadings);
    }

    // 方差贡献
    if (data.variance && elements.pcaVarianceTable) {
        renderDataTable(elements.pcaVarianceTable, data.variance);
    }

    // 特征权重
    if (data.weights && elements.pcaWeightsTable) {
        renderDataTable(elements.pcaWeightsTable, data.weights);
    }

    // 综合得分
    if (data.scores && elements.pcaScoresTable) {
        renderDataTable(elements.pcaScoresTable, data.scores);
    }

    // 碎石图
    if (data.scree_plot && elements.pcaScreePlot) {
        renderPCAPlot(elements.pcaScreePlot, data.scree_plot);
    }

    // 2D 双标图
    if (data.biplot_2d && elements.pcaBiplot2d) {
        renderPCAPlot(elements.pcaBiplot2d, data.biplot_2d);
    }

    // 3D 双标图
    if (data.biplot_3d && elements.pcaBiplot3d) {
        renderPCAPlot(elements.pcaBiplot3d, data.biplot_3d);
    } else if (elements.pcaBiplot3d) {
        elements.pcaBiplot3d.innerHTML = '<p style="color: #94a3b8;">3D 双标图需要至少3个主成分</p>';
    }

    // 初始化双标图坐标轴控件
    if (data.summary && data.summary.n_components) {
        initBiplotControls(data.summary.n_components);
    }
}

// ===== 渲染 PCA 图表 =====
function renderPCAPlot(container, plotData) {
    if (!plotData || !plotData.data) {
        container.innerHTML = '<p style="color: #94a3b8;">图表生成失败</p>';
        return;
    }

    if (plotData.format === 'png') {
        container.innerHTML = `<img src="data:image/png;base64,${plotData.data}" alt="PCA Plot">`;
    } else if (plotData.format === 'svg') {
        container.innerHTML = plotData.data;
    }
}

// ===== 切换 Biplot 视图 (2D/3D) =====
function showBiplot(type) {
    const btn2d = document.getElementById('btn-biplot-2d');
    const btn3d = document.getElementById('btn-biplot-3d');
    const plot2d = elements.pcaBiplot2d;
    const plot3d = elements.pcaBiplot3d;

    if (type === '2d') {
        btn2d.classList.add('active');
        btn3d.classList.remove('active');
        if (plot2d) plot2d.hidden = false;
        if (plot3d) plot3d.hidden = true;
    } else {
        btn2d.classList.remove('active');
        btn3d.classList.add('active');
        if (plot2d) plot2d.hidden = true;
        if (plot3d) plot3d.hidden = false;
    }

    // 更新 Z 轴选择器可见性
    if (elements.biplotZLabel) {
        elements.biplotZLabel.hidden = (type !== '3d');
    }
}

// ===== 初始化双标图坐标轴控件 =====
function initBiplotControls(n_components) {
    if (!elements.biplotControls) return;

    elements.biplotControls.hidden = false;
    const comps = Array.from({ length: n_components }, (_, i) => i + 1);

    // 填充下拉框
    const updateSelect = (select, selected) => {
        if (!select) return;
        select.innerHTML = comps.map(i =>
            `<option value="${i}" ${i === selected ? 'selected' : ''}>PC${i}</option>`
        ).join('');
    };

    updateSelect(elements.biplotXSelect, 1);
    updateSelect(elements.biplotYSelect, 2);
    updateSelect(elements.biplotZSelect, 3);
}

// ===== 更新双标图坐标轴 =====
async function updateBiplotAxis() {
    const is3D = !elements.pcaBiplot3d.hidden;
    const pcX = parseInt(elements.biplotXSelect.value);
    const pcY = parseInt(elements.biplotYSelect.value);
    const pcZ = is3D ? parseInt(elements.biplotZSelect.value) : null;

    // 验证
    if (pcX === pcY || (is3D && (pcX === pcZ || pcY === pcZ))) {
        showToast('坐标轴不能选择相同的主成分', 'warning');
        return;
    }

    const container = is3D ? elements.pcaBiplot3d : elements.pcaBiplot2d;
    container.innerHTML = '<div class="loading-spinner"></div><p class="loading-text">正在更新图表...</p>';

    try {
        // 获取椭圆参数
        const drawEllipseCheckbox = document.getElementById('pca-draw-ellipse');
        const ellipseGroupSelect = document.getElementById('pca-ellipse-group');
        const confidenceSlider = document.getElementById('pca-confidence-level');

        const drawEllipse = drawEllipseCheckbox ? drawEllipseCheckbox.checked : false;
        const ellipseGroup = ellipseGroupSelect ? ellipseGroupSelect.value : '';
        const confidenceLevel = confidenceSlider ? parseInt(confidenceSlider.value) / 100 : 0.95;

        const response = await fetch('/api/pca_plot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: appState.dataId,
                targets: appState.targets,
                group_by: appState.pcaGroups,
                plot_type: is3D ? 'biplot_3d' : 'biplot_2d',
                format: 'png',
                pc_x: pcX,
                pc_y: pcY,
                pc_z: pcZ,
                // 椭圆参数
                draw_ellipse: drawEllipse,
                ellipse_group: ellipseGroup || (appState.pcaGroups.length > 0 ? appState.pcaGroups[0] : ''),
                confidence_level: confidenceLevel
            })
        });

        const data = await response.json();
        if (data.error) throw new Error(data.error);

        renderPCAPlot(container, data);

    } catch (error) {
        container.innerHTML = `<p style="color: var(--error-color)">更新失败: ${error.message}</p>`;
    }
}

// ===== 下载 PCA 图表 =====
async function downloadPCAPlot(plotType, format) {
    if (!appState.results || !appState.dataId) {
        showToast('请先执行分析', 'error');
        return;
    }

    try {
        showToast(`正在生成 ${format.toUpperCase()} 图表...`, 'info');

        const response = await fetch('/api/pca_plot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: appState.dataId,
                targets: appState.targets,
                plot_type: plotType,
                format: format
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast(data.error, 'error');
            return;
        }

        // 解码并下载
        const blob = base64ToBlob(data.data, data.mime);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `pca_${plotType}.${format}`;
        a.click();
        URL.revokeObjectURL(url);

        showToast('下载完成！', 'success');

    } catch (error) {
        showToast('下载失败: ' + error.message, 'error');
    }
}

// ===== 下载当前 Biplot =====
function downloadCurrentBiplot(format) {
    const plot3d = elements.pcaBiplot3d;
    const is3d = plot3d && !plot3d.hidden;
    downloadPCAPlot(is3d ? 'biplot_3d' : 'biplot_2d', format);
}

// ===== Base64 转 Blob =====
function base64ToBlob(base64, mime) {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mime });
}

// ===== 动态隐藏 Tab 辅助函数 =====
function hideEmptyTabs(container, dataMap) {
    container.querySelectorAll('.tab-btn').forEach(btn => {
        const key = btn.dataset.tab;
        // 如果 dataMap 中有这个 key，且对应的值为空，则隐藏
        // 特殊处理：有些 tab key 和 data key 不完全一致，需要映射
        // 在调用处传正确的 map 即可
        if (dataMap.hasOwnProperty(key)) {
            const hasData = dataMap[key] && dataMap[key].length > 0;
            btn.style.display = hasData ? '' : 'none';
        }
    });
}

// ===== 根据分析类型更新结果 Tab 显示 =====
function updateResultTabsForAnalysisType() {
    const isPCA = appState.analysisType === 'pca';
    const isCluster = appState.analysisType === 'cluster';
    const isANOVA = appState.analysisType === 'anova';

    // 切换结果 Tab 导航显示
    if (elements.resultTabs) {
        elements.resultTabs.hidden = !isANOVA;
        if (isANOVA && appState.results) {
            // 动态隐藏无数据的 Tab
            hideEmptyTabs(elements.resultTabs, {
                'sliced-sep': appState.results.sliced_sep,
                'sliced': appState.results.sliced_comb, // 注意 ID 通常是 sliced 但这里 tab 是 sliced
                'main': appState.results.main,
                'anova': appState.results.anova,
                'corr': appState.results.corr
            });
        }
    }
    if (elements.pcaResultTabs) {
        elements.pcaResultTabs.hidden = !isPCA;
    }
    if (elements.clusterResultTabs) {
        elements.clusterResultTabs.hidden = !isCluster;
    }

    // 重置 Tab 面板显示
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
    });

    // 激活默认 Tab
    if (isCluster) {
        if (elements.clusterResultTabs) {
            const visibleBtn = Array.from(elements.clusterResultTabs.querySelectorAll('.tab-btn'))
                .find(btn => btn.style.display !== 'none');
            if (visibleBtn) visibleBtn.click();
        }
    } else if (isPCA) {
        if (elements.pcaResultTabs) {
            const visibleBtn = Array.from(elements.pcaResultTabs.querySelectorAll('.tab-btn'))
                .find(btn => btn.style.display !== 'none');
            if (visibleBtn) visibleBtn.click();
        }
    } else {
        // ANOVA
        if (elements.resultTabs) {
            // 找到第一个可见的 tab
            const visibleBtn = Array.from(elements.resultTabs.querySelectorAll('.tab-btn'))
                .find(btn => btn.style.display !== 'none');

            if (visibleBtn) {
                visibleBtn.click();
            }
        }
    }
}


// ===== 渲染数据表格 (虚拟滚动优化版) =====
function renderDataTable(container, data) {
    if (!data || data.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #94a3b8; padding: 2rem;">暂无数据</p>';
        return;
    }

    const columns = Object.keys(data[0]);
    const MAX_ROWS = 500; // 性能阈值：默认只渲染前 500 行
    const isTruncated = data.length > MAX_ROWS;
    const displayData = isTruncated ? data.slice(0, MAX_ROWS) : data;

    let html = '<table class="data-table">';
    html += '<thead><tr>';
    columns.forEach(col => {
        html += `<th>${escapeHtml(col)}</th>`;
    });
    html += '</tr></thead>';

    html += '<tbody>';
    displayData.forEach(row => {
        html += '<tr>';
        columns.forEach(col => {
            html += `<td>${escapeHtml(row[col] !== null ? row[col] : '')}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table>';

    // 如果数据被截断，添加提示信息
    if (isTruncated) {
        html += `
            <div style="text-align: center; padding: 12px; color: #64748b; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 0.9rem;">
                ⚠️ 为保证性能，仅显示前 ${MAX_ROWS} 行数据 (共 ${data.length} 行) <br>
                <small>完整结果请导出 Excel 查看</small>
            </div>
        `;
    }

    container.innerHTML = html;
}

// ===== Tab 切换 =====
// ===== Tab 切换 =====
function initTabs() {
    // 方差分析结果 Tab
    elements.resultTabs.addEventListener('click', (e) => {
        if (e.target.classList.contains('tab-btn')) {
            handleTabClick(e.target, elements.resultTabs);
        }
    });

    // PCA 结果 Tab
    if (elements.pcaResultTabs) {
        elements.pcaResultTabs.addEventListener('click', (e) => {
            if (e.target.classList.contains('tab-btn')) {
                handleTabClick(e.target, elements.pcaResultTabs);
            }
        });
    }

    // 聚类结果 Tab
    if (elements.clusterResultTabs) {
        elements.clusterResultTabs.addEventListener('click', (e) => {
            if (e.target.classList.contains('tab-btn')) {
                handleTabClick(e.target, elements.clusterResultTabs);
            }
        });
    }
}

// ===== 处理 Tab 点击 =====
function handleTabClick(clickedBtn, tabContainer) {
    const tabId = clickedBtn.dataset.tab;

    // 更新当前容器内按钮状态
    tabContainer.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });

    // 更新面板显示
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `panel-${tabId}`);
    });
}


// ===== 导出 Excel =====
function initExport() {
    elements.btnExport.addEventListener('click', async () => {
        if (!appState.results) {
            showToast('请先执行分析', 'error');
            return;
        }

        // 根据分析类型选择不同的导出方式
        if (appState.analysisType === 'pca') {
            await exportPCAResults();
        } else {
            await exportANOVAResults();
        }
    });
}

// ===== 导出 PCA 结果 =====
async function exportPCAResults() {
    try {
        showToast('正在生成 PCA 分析结果 Excel，请稍候...', 'info');

        const response = await fetch('/api/export_pca', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                save_directory: elements.savePathInput ? elements.savePathInput.value : '',
                loadings: appState.results.loadings,
                variance: appState.results.variance,
                weights: appState.results.weights,
                scores: appState.results.scores,
                include_loadings: true,
                include_variance: true,
                include_weights: true,
                include_scores: true
            })
        });

        const contentType = response.headers.get('content-type');

        if (!response.ok) {
            const errorText = await response.text();
            try {
                const errorData = JSON.parse(errorText);
                throw new Error(errorData.error || `导出请求失败 (${response.status})`);
            } catch (e) {
                throw new Error(`导出请求失败 (${response.status})`);
            }
        }

        // 处理 JSON 响应 (本地保存成功)
        if (contentType && contentType.includes('application/json')) {
            const result = await response.json();
            if (result.success) {
                showToast(result.message, 'success');
                return;
            } else if (result.error) {
                throw new Error(result.error);
            }
        }

        // 下载文件
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'PCA分析结果.xlsx';
        a.click();
        URL.revokeObjectURL(url);

        showToast('PCA 分析结果导出成功！', 'success');

    } catch (error) {
        showToast('PCA 导出失败: ' + error.message, 'error');
    }
}

// ===== 导出 ANOVA 结果 =====
async function exportANOVAResults() {
    try {
        showToast('正在生成 Excel，请稍候...', 'info');

        // 构造数据
        // const threeLineData = getTableData(elements.threeLineTable); // 用户要求移除
        const threeLineData = [];
        const factors = appState.results.factors || [];
        const targets = appState.results.targets || [];

        // 添加表头
        const header = {};
        factors.forEach(f => header[f] = f);
        targets.forEach(t => header[t] = t);
        threeLineData.push(header);

        // 添加组内比较
        if (appState.results.sliced_comb) {
            const sectionRow = {};
            factors.forEach((f, i) => sectionRow[f] = i === 0 ? '【组内比较】' : '');
            targets.forEach(t => sectionRow[t] = '');
            threeLineData.push(sectionRow);

            appState.results.sliced_comb.forEach(row => {
                const newRow = {};
                factors.forEach(f => newRow[f] = row[f] || '');
                targets.forEach(t => newRow[t] = row[t] || '');
                threeLineData.push(newRow);
            });
        }

        // 添加主效应
        if (appState.results.main) {
            const sectionRow = {};
            factors.forEach((f, i) => sectionRow[f] = i === 0 ? '【主效应多重比较】' : '');
            targets.forEach(t => sectionRow[t] = '');
            threeLineData.push(sectionRow);

            appState.results.main.forEach(row => {
                const newRow = {};
                newRow[factors[0]] = row['Factor'] || '';
                newRow[factors[1] || 'Level'] = row['Level'] || '';
                for (let i = 2; i < factors.length; i++) newRow[factors[i]] = '';
                targets.forEach(t => newRow[t] = row[t] || '');
                threeLineData.push(newRow);
            });
        }

        // 添加方差分析
        if (appState.results.anova) {
            const sectionRow = {};
            factors.forEach((f, i) => sectionRow[f] = i === 0 ? '【方差分析 (F值)】' : '');
            targets.forEach(t => sectionRow[t] = '');
            threeLineData.push(sectionRow);

            appState.results.anova.forEach(row => {
                const newRow = {};
                newRow[factors[0]] = row['Source'] || '';
                for (let i = 1; i < factors.length; i++) newRow[factors[i]] = '';
                targets.forEach(t => newRow[t] = row[t] || '');
                threeLineData.push(newRow);
            });
        }

        console.log('Starting export request...');

        const response = await fetch('/api/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                // three_line_table: threeLineData, // 用户要求移除
                save_directory: elements.savePathInput ? elements.savePathInput.value : '',
                sliced_comb: appState.results.sliced_comb,
                sliced_sep: appState.results.sliced_sep,
                main: appState.results.main,
                anova: appState.results.anova,
                corr: appState.results.corr
            })
        });

        const contentType = response.headers.get('content-type');
        console.log('Export response status:', response.status);
        console.log('Export content-type:', contentType);

        if (!response.ok) {
            // 尝试读取错误信息
            const errorText = await response.text();
            console.error('Export error body:', errorText);
            try {
                const errorData = JSON.parse(errorText);
                throw new Error(errorData.error || `导出请求失败 (${response.status})`);
            } catch (e) {
                throw new Error(`导出请求失败 (${response.status}): ${errorText.substring(0, 100)}`);
            }
        }

        // 处理 JSON 响应 (可能是错误，也可能是本地保存成功)
        if (contentType && contentType.includes('application/json')) {
            const result = await response.json();
            if (result.success) {
                showToast(result.message, 'success');
                console.log('Saved locally to:', result.local_path);
                return; // 本地保存成功，无需下载
            } else {
                console.error('Export JSON error:', result);
                throw new Error(result.error || '导出失败: 后端返回了错误信息');
            }
        }

        // 下载文件
        const blob = await response.blob();
        console.log('Blob size:', blob.size);

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = '分析结果.xlsx';
        a.click();
        URL.revokeObjectURL(url);

        showToast('Excel 导出成功！', 'success');

    } catch (error) {
        console.error('Export exception:', error);
        showToast('导出失败: ' + error.message, 'error');
    }
}

// ===== Toast 提示 =====
function showToast(message, type = 'info') {
    elements.toastMessage.textContent = message;
    elements.toast.className = 'toast ' + type;
    elements.toast.classList.add('show');

    setTimeout(() => {
        elements.toast.classList.remove('show');
    }, 3000);
}

// ===== HTML 转义 =====
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// ===== 启动应用 =====
document.addEventListener('DOMContentLoaded', init);


// =====================================================
// 聚类分析功能
// =====================================================

// ===== 初始化聚类控制 =====
function initClusterControls() {
    // 算法切换
    if (elements.clusterAlgorithm) {
        elements.clusterAlgorithm.addEventListener('change', () => {
            const isHierarchical = elements.clusterAlgorithm.value === 'hierarchical';
            if (elements.linkageGroup) {
                elements.linkageGroup.hidden = !isHierarchical;
            }
            appState.clusterParams.algorithm = elements.clusterAlgorithm.value;
        });
    }

    // 聚类数变化
    if (elements.clusterK) {
        elements.clusterK.addEventListener('change', () => {
            appState.clusterParams.n_clusters = parseInt(elements.clusterK.value) || 3;
        });
    }

    // 连接方法变化
    if (elements.linkageMethod) {
        elements.linkageMethod.addEventListener('change', () => {
            appState.clusterParams.linkage_method = elements.linkageMethod.value;
        });
    }

    // 肘部图按钮
    if (elements.btnElbow) {
        elements.btnElbow.addEventListener('click', fetchElbowPlot);
    }

    // 导出聚类数据按钮
    if (elements.btnExportCluster) {
        elements.btnExportCluster.addEventListener('click', exportClusterData);
    }

    // 数据过滤器变化
    if (elements.clusterFilterSelect) {
        elements.clusterFilterSelect.addEventListener('change', () => {
            appState.clusterFilter = elements.clusterFilterSelect.value;
            updateFilterInfo();
        });
    }
}

// ===== 执行聚类分析 =====
async function runClusterAnalysis() {
    if (appState.targets.length < 2) {
        showToast('聚类分析至少需要选择2个数值特征', 'warning');
        return;
    }

    elements.loadingSection.hidden = false;
    elements.resultSection.hidden = true;
    elements.btnAnalyze.disabled = true;

    // 收集正向化配置
    const targetConfigs = {};
    const targetItems = document.querySelectorAll('#target-list .variable-item');

    targetItems.forEach(item => {
        const name = item.dataset.name;
        const select = item.querySelector('.norm-select');

        if (select) {
            const type = select.value;
            const config = { type: type };

            if (type === 'interval') {
                const inputA = item.querySelector('.param-a');
                const inputB = item.querySelector('.param-b');
                config.a = inputA ? parseFloat(inputA.value) : 0;
                config.b = inputB ? parseFloat(inputB.value) : 0;
            }

            targetConfigs[name] = config;
        }
    });

    try {
        const response = await fetch('/api/analyze_cluster', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: appState.dataId,
                features: appState.targets,
                factors: appState.factors,  // 发送选定的因子
                algorithm: appState.clusterParams.algorithm,
                n_clusters: appState.clusterParams.n_clusters,
                linkage_method: appState.clusterParams.linkage_method,
                use_means: document.getElementById('cluster-use-means') ? document.getElementById('cluster-use-means').checked : false,
                target_configs: targetConfigs // 添加正向化配置
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast(data.error, 'error');
            elements.loadingSection.hidden = true;
            elements.btnAnalyze.disabled = false;
            return;
        }

        // 保存结果
        appState.results = data;
        appState.results.analysisType = 'cluster';

        // 渲染结果
        renderClusterResults(data);

        // 更新全局过滤器
        await updateClusterFilterOptions();

        // 显示结果区域
        elements.loadingSection.hidden = true;
        elements.resultSection.hidden = false;
        elements.btnAnalyze.disabled = false;

        // 更新结果标签页显示
        updateResultTabsForAnalysisType();

        showToast('聚类分析完成！', 'success');

    } catch (error) {
        console.error('聚类分析失败:', error);
        showToast('分析失败: ' + error.message, 'error');
        elements.loadingSection.hidden = true;
        elements.btnAnalyze.disabled = false;
    }
}

// ===== 渲染聚类结果 =====
function renderClusterResults(data) {
    // 聚类摘要
    if (data.summary && elements.clusterSummary) {
        const summary = data.summary;
        let html = `
            <div class="cluster-summary-grid">
                <div class="summary-card">
                    <div class="label">聚类算法</div>
                    <div class="value">${summary.algorithm === 'kmeans' ? 'K-Means' : '层次聚类'}</div>
                </div>
                <div class="summary-card">
                    <div class="label">聚类数量</div>
                    <div class="value">${summary.n_clusters}</div>
                </div>
                <div class="summary-card">
                    <div class="label">样本数量</div>
                    <div class="value">${summary.n_samples}</div>
                </div>
                <div class="summary-card">
                    <div class="label">特征数量</div>
                    <div class="value">${summary.n_features}</div>
                </div>
            </div>
            ${summary.note ? `<div class="alert alert-info" style="margin: 1rem 0; padding: 0.75rem; background: #e3f2fd; border-radius: 6px; color: #0d47a1; font-size: 0.9rem;">ℹ️ ${summary.note}</div>` : ''}
            <h5>各聚类样本分布</h5>
            <div class="cluster-sizes">
        `;

        summary.cluster_sizes.forEach(cs => {
            html += `
                <div class="cluster-badge">
                    <span class="dot"></span>
                    聚类 ${cs.cluster}: ${cs.size} 样本 (${cs.percentage}%)
                </div>
            `;
        });

        html += '</div>';
        elements.clusterSummary.innerHTML = html;
    }

    // 聚类散点图
    if (data.scatter_plot && elements.clusterScatterPlot) {
        renderClusterPlot(elements.clusterScatterPlot, data.scatter_plot);
    }

    // 聚类热图 (新增)
    const heatmapContainer = document.getElementById('cluster-heatmap-plot');
    if (data.heatmap_plot && heatmapContainer) {
        renderClusterPlot(heatmapContainer, data.heatmap_plot);
    } else if (heatmapContainer) {
        heatmapContainer.innerHTML = '<div style="text-align:center; padding:20px; color:#888;">热图生成失败</div>';
    }

    // 相关性热图 (新增 - 参考用户图片)
    const corrHeatmapContainer = document.getElementById('cluster-corr-heatmap-plot');
    if (data.corr_heatmap_plot && corrHeatmapContainer) {
        renderClusterPlot(corrHeatmapContainer, data.corr_heatmap_plot);
    } else if (corrHeatmapContainer) {
        corrHeatmapContainer.innerHTML = '<div style="text-align:center; padding:20px; color:#888;">相关性热图生成失败</div>';
    }

    // 聚类数据表
    if (data.labeled_data && elements.clusterDataTable) {
        renderClusterDataTable(elements.clusterDataTable, data.labeled_data);
    }
}

// ===== 渲染聚类数据表 =====
function renderClusterDataTable(container, data) {
    if (!data || !data.headers || !data.rows || data.rows.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #94a3b8; padding: 2rem;">暂无数据</p>';
        return;
    }

    const headers = data.headers;
    const rows = data.rows;

    let html = '<table class="data-table">';
    html += '<thead><tr>';
    headers.forEach(col => {
        html += `<th>${escapeHtml(col)}</th>`;
    });
    html += '</tr></thead>';

    html += '<tbody>';
    rows.forEach(row => {
        html += '<tr>';
        row.forEach((cell, idx) => {
            // 高亮聚类标签列
            const isClusterCol = headers[idx] === 'Cluster_Label';
            const cellClass = isClusterCol ? ` class="cluster-label-${cell}"` : '';
            html += `<td${cellClass}>${escapeHtml(cell !== null ? cell : '')}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table>';

    container.innerHTML = html;
}

// ===== 渲染聚类图表 =====
function renderClusterPlot(container, plotData) {
    if (!plotData || !plotData.data) {
        container.innerHTML = '<p style="color: #94a3b8;">图表生成失败</p>';
        return;
    }

    if (plotData.format === 'png') {
        container.innerHTML = `<img src="data:image/png;base64,${plotData.data}" alt="Cluster Plot">`;
    } else if (plotData.format === 'svg') {
        container.innerHTML = plotData.data;
    }
}

// ===== 获取肘部图 =====
async function fetchElbowPlot() {
    if (appState.targets.length < 2) {
        showToast('请先选择至少2个数值特征', 'warning');
        return;
    }

    elements.btnElbow.disabled = true;
    elements.btnElbow.textContent = '⏳ 计算中...';

    try {
        const response = await fetch('/api/cluster_elbow', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: appState.dataId,
                features: appState.targets,
                max_k: 10
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast(data.error, 'error');
        } else if (data.elbow_plot && elements.clusterElbowPlot) {
            renderClusterPlot(elements.clusterElbowPlot, data.elbow_plot);
            showToast('肘部图已生成', 'success');
        }

    } catch (error) {
        showToast('获取肘部图失败: ' + error.message, 'error');
    } finally {
        elements.btnElbow.disabled = false;
        elements.btnElbow.textContent = '📈 查看肘部图';
    }
}

// ===== 导出聚类数据 =====
async function exportClusterData() {
    try {
        showToast('正在生成聚类数据...', 'info');

        const response = await fetch('/api/export_cluster', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: appState.dataId,
                features: appState.targets,
                algorithm: appState.clusterParams.algorithm,
                n_clusters: appState.clusterParams.n_clusters,
                linkage_method: appState.clusterParams.linkage_method
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '导出失败');
        }

        // 下载文件
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `聚类结果_${appState.clusterParams.algorithm}_k${appState.clusterParams.n_clusters}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        showToast('聚类数据已导出', 'success');

    } catch (error) {
        showToast('导出失败: ' + error.message, 'error');
    }
}

// ===== 更新聚类过滤器选项 =====
async function updateClusterFilterOptions() {
    if (!elements.clusterFilterSelect || !elements.dataFilterPanel) return;

    try {
        const response = await fetch(`/api/get_cluster_subsets?data_id=${appState.dataId}`);
        const data = await response.json();

        if (data.available) {
            elements.dataFilterPanel.hidden = false;

            let html = '';
            data.subsets.forEach(subset => {
                html += `<option value="${subset.value}">${subset.label} (n=${subset.count})</option>`;
            });
            elements.clusterFilterSelect.innerHTML = html;

            updateFilterInfo();
        }

    } catch (error) {
        console.error('获取聚类子集失败:', error);
    }
}

// ===== 更新过滤器信息 =====
function updateFilterInfo() {
    if (!elements.filterInfo) return;

    const filter = appState.clusterFilter;
    if (filter === 'all') {
        elements.filterInfo.textContent = '使用全部数据进行分析';
    } else {
        elements.filterInfo.textContent = `仅使用聚类 ${parseInt(filter) + 1} 的数据`;
    }
}

// ===== 下载聚类图表 =====
function downloadClusterPlot(plotType, format) {
    // 简单实现：目前只支持保存当前显示的图像
    showToast('图表下载功能开发中', 'info');
}
