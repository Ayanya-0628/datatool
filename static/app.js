/**
 * 数据分析工具 - 前端交互逻辑
 */

// ===== 全局状态 =====
let appState = {
    dataId: null,
    columns: [],
    factors: [],
    targets: [],
    results: null,
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

    // Toast
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toast-message')
};

// ===== 初始化 =====
function init() {
    initUpload();
    initTabs();
    initExport();
    initModal();
    initMultiSelect();
    initBrowse();
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
    // 点击上传
    elements.uploadZone.addEventListener('click', () => {
        elements.fileInput.click();
    });

    // 文件选择
    elements.fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadFile(e.target.files[0]);
        }
    });

    // 拖拽上传
    elements.uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.uploadZone.classList.add('drag-over');
    });

    elements.uploadZone.addEventListener('dragleave', () => {
        elements.uploadZone.classList.remove('drag-over');
    });

    elements.uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.uploadZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            uploadFile(e.dataTransfer.files[0]);
        }
    });

    // 清除文件
    elements.clearFile.addEventListener('click', clearData);

    // 分析按钮
    elements.btnAnalyze.addEventListener('click', runAnalysis);
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
        if (data.status === 'select_sheet') {
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
    // 保存状态
    appState.dataId = data.data_id;
    appState.columns = data.columns;
    appState.factors = [];
    appState.targets = [];

    // 更新UI
    elements.fileName.textContent = fileNameDisplay;
    elements.fileRows.textContent = `共 ${data.rows} 行`;
    elements.fileInfo.hidden = false;

    // 填充变量池
    renderSourceList();
    elements.variableSection.hidden = false;

    // 隐藏结果区域
    elements.resultSection.hidden = true;

    showToast('数据加载成功！', 'success');
}

// ===== 渲染变量池 =====
function renderSourceList() {
    elements.sourceList.innerHTML = '';

    const availableColumns = appState.columns.filter(
        col => !appState.factors.includes(col) && !appState.targets.includes(col)
    );

    availableColumns.forEach((col, index) => {
        const li = createVariableItem(col, 'source', index);
        elements.sourceList.appendChild(li);
    });

    // 渲染批量操作按钮
    renderBatchActions();

    renderFactorList();
    renderTargetList();

    // 更新选择状态显示
    updateSelectionUI();
}

// ===== 渲染批量操作按钮 =====
function renderBatchActions() {
    // 检查是否已存在批量操作区域
    let batchActionsDiv = document.querySelector('.batch-actions');
    if (!batchActionsDiv) {
        // 创建批量操作区域（添加到变量池后面）
        batchActionsDiv = document.createElement('div');
        batchActionsDiv.className = 'batch-actions';
        batchActionsDiv.innerHTML = `
            <div class="batch-hint">
                💡 提示：按住 <kbd>Ctrl</kbd> 点击可多选，按住 <kbd>Shift</kbd> 点击可范围选择
            </div>
            <div class="batch-buttons">
                <button class="btn btn-small btn-factor" id="btn-add-as-factor" disabled>
                    📌 添加为因子 (<span id="selected-count-factor">0</span>)
                </button>
                <button class="btn btn-small btn-target" id="btn-add-as-target" disabled>
                    📈 添加为性状 (<span id="selected-count-target">0</span>)
                </button>
                <button class="btn btn-small btn-outline" id="btn-clear-selection" disabled>
                    ✕ 清除选择
                </button>
            </div>
        `;

        // 插入到变量池 box 后面
        const sourceBox = elements.sourceList.closest('.variable-box');
        sourceBox.appendChild(batchActionsDiv);

        // 绑定事件
        document.getElementById('btn-add-as-factor').addEventListener('click', (e) => {
            e.stopPropagation();
            addSelectedVariables('factor');
        });

        document.getElementById('btn-add-as-target').addEventListener('click', (e) => {
            e.stopPropagation();
            addSelectedVariables('target');
        });

        document.getElementById('btn-clear-selection').addEventListener('click', (e) => {
            e.stopPropagation();
            clearSelection();
        });
    }
}

// ===== 更新选择状态 UI =====
function updateSelectionUI() {
    const count = appState.selectedItems.length;

    const btnFactor = document.getElementById('btn-add-as-factor');
    const btnTarget = document.getElementById('btn-add-as-target');
    const btnClear = document.getElementById('btn-clear-selection');
    const countFactor = document.getElementById('selected-count-factor');
    const countTarget = document.getElementById('selected-count-target');

    if (btnFactor && btnTarget && btnClear) {
        btnFactor.disabled = count === 0;
        btnTarget.disabled = count === 0;
        btnClear.disabled = count === 0;

        if (countFactor) countFactor.textContent = count;
        if (countTarget) countTarget.textContent = count;
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

    appState.selectedItems.forEach(name => {
        if (type === 'factor') {
            if (!appState.factors.includes(name)) {
                appState.factors.push(name);
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

    showToast(`已添加 ${appState.selectedItems.length || '所选'} 个变量`, 'success');
}

// ===== 渲染因子列表 =====
function renderFactorList() {
    elements.factorList.innerHTML = '';
    appState.factors.forEach(col => {
        const li = createVariableItem(col, 'factor');
        elements.factorList.appendChild(li);
    });
}

// ===== 渲染性状列表 =====
function renderTargetList() {
    elements.targetList.innerHTML = '';
    appState.targets.forEach(col => {
        const li = createVariableItem(col, 'target');
        elements.targetList.appendChild(li);
    });
}

// ===== 创建变量项 =====
function createVariableItem(name, type, index = -1) {
    const li = document.createElement('li');
    li.className = 'variable-item';
    li.textContent = name;
    li.dataset.name = name;
    li.dataset.index = index;

    if (type === 'source') {
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
    const availableColumns = appState.columns.filter(
        col => !appState.factors.includes(col) && !appState.targets.includes(col)
    );

    if (event.ctrlKey || event.metaKey) {
        // Ctrl/Cmd + 点击：切换选择
        const selectedIndex = appState.selectedItems.indexOf(name);
        if (selectedIndex > -1) {
            appState.selectedItems.splice(selectedIndex, 1);
        } else {
            appState.selectedItems.push(name);
        }
        appState.lastSelectedIndex = index;
    } else if (event.shiftKey && appState.lastSelectedIndex !== -1) {
        // Shift + 点击：范围选择
        const start = Math.min(appState.lastSelectedIndex, index);
        const end = Math.max(appState.lastSelectedIndex, index);

        // 添加范围内所有项
        for (let i = start; i <= end; i++) {
            const col = availableColumns[i];
            if (col && !appState.selectedItems.includes(col)) {
                appState.selectedItems.push(col);
            }
        }
    } else {
        // 普通点击：显示添加菜单（单个变量）或直接选择
        // 如果之前没有选择，显示菜单；如果有选择，切换到单选此项
        appState.selectedItems = [name];
        appState.lastSelectedIndex = index;

        // 延迟显示菜单（给双击留时间）
        clearTimeout(window.variableClickTimer);
        window.variableClickTimer = setTimeout(() => {
            if (appState.selectedItems.length === 1 && appState.selectedItems[0] === name) {
                // 可选：此处可以选择是否显示菜单，或者只依赖批量按钮
                // showVariableMenu(name, event.target);
            }
        }, 200);
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
    appState = {
        dataId: null,
        columns: [],
        factors: [],
        targets: [],
        results: null
    };

    elements.fileInput.value = '';
    elements.fileInfo.hidden = true;
    elements.variableSection.hidden = true;
    elements.resultSection.hidden = true;
}

// ===== 执行分析 =====
async function runAnalysis() {
    if (appState.factors.length === 0) {
        showToast('请至少选择1个因子 (X)', 'error');
        return;
    }

    if (appState.targets.length === 0) {
        showToast('请至少选择1个性状 (Y)', 'error');
        return;
    }

    // 显示加载状态
    elements.loadingSection.hidden = false;
    elements.resultSection.hidden = true;
    elements.btnAnalyze.disabled = true;

    try {
        const response = await fetch(`/api/analyze?t=${new Date().getTime()}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data_id: appState.dataId,
                factors: appState.factors,
                targets: appState.targets
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

        // 渲染结果
        renderResults(data);

        // 显示结果区域
        elements.loadingSection.hidden = true;
        elements.resultSection.hidden = false;
        elements.btnAnalyze.disabled = false;

        // 滚动到结果
        elements.resultSection.scrollIntoView({ behavior: 'smooth' });

        showToast('分析完成！', 'success');

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


// ===== 渲染数据表格 =====
function renderDataTable(container, data) {
    if (!data || data.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #94a3b8; padding: 2rem;">暂无数据</p>';
        return;
    }

    const columns = Object.keys(data[0]);

    let html = '<table class="data-table">';
    html += '<thead><tr>';
    columns.forEach(col => {
        html += `<th>${escapeHtml(col)}</th>`;
    });
    html += '</tr></thead>';

    html += '<tbody>';
    data.forEach(row => {
        html += '<tr>';
        columns.forEach(col => {
            html += `<td>${escapeHtml(row[col] !== null ? row[col] : '')}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table>';

    container.innerHTML = html;
}

// ===== Tab 切换 =====
function initTabs() {
    elements.resultTabs.addEventListener('click', (e) => {
        if (e.target.classList.contains('tab-btn')) {
            const tabId = e.target.dataset.tab;

            // 更新按钮状态
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.tab === tabId);
            });

            // 更新面板显示
            document.querySelectorAll('.tab-panel').forEach(panel => {
                panel.classList.toggle('active', panel.id === `panel-${tabId}`);
            });
        }
    });
}

// ===== 导出 Excel =====
function initExport() {
    elements.btnExport.addEventListener('click', async () => {
        if (!appState.results) {
            showToast('请先执行分析', 'error');
            return;
        }

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
    });
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
