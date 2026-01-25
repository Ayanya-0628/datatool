# 后端架构 (Backend)

**最后更新:** 2026-01-25
**入口文件:** `app.py` (1558 行)

## 架构概览

```
app.py
├── Flask 应用初始化
├── 全局配置 & 错误处理
├── 数据存储管理 (内存 + 过期清理)
├── 核心统计逻辑
│   ├── ANOVA 方差分析
│   ├── LSD 多重比较
│   └── CLD 紧凑字母显示
└── API 路由
    ├── /api/upload
    ├── /api/load_sheet
    ├── /api/analyze
    ├── /api/analyze_pca
    ├── /api/analyze_cluster
    └── /api/export
```

## 核心组件

### 1. 数据存储

```python
# 全局数据存储 (内存字典)
data_store = {}           # {uuid: DataFrame}
data_timestamps = {}      # {uuid: timestamp}
temp_file_store = {}      # 多Sheet文件暂存
cluster_store = {}        # 聚类结果缓存

DATA_EXPIRE_SECONDS = 3600  # 1小时过期
```

**清理机制:** 后台守护线程每5分钟检查并清理过期数据

### 2. 可选模块加载

```python
# 优雅降级模式
HAS_SKLEARN = True/False      # scikit-learn
HAS_PCA_MODULE = True/False   # pca_analysis.py
HAS_CLUSTER_MODULE = True/False  # clustering.py
HAS_TKINTER = True/False      # 本地目录选择
HAS_MATPLOTLIB = True/False   # 图表生成
```

## API 路由详解

### 文件上传

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/upload` | POST | 上传 CSV/Excel 文件 |
| `/api/load_sheet` | POST | 加载指定 Excel 工作表 |

**上传响应结构:**
```json
{
  "data_id": "uuid",
  "columns": ["col1", "col2"],
  "rows": 100,
  "column_types": {"col1": "numeric", "col2": "categorical"},
  "suggested_factors": ["col2"],
  "suggested_indicators": ["col1"]
}
```

### 方差分析

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/analyze` | POST | 执行 ANOVA + LSD 多重比较 |

**请求参数:**
```json
{
  "data_id": "uuid",
  "factors": ["品种", "处理"],
  "targets": ["产量", "株高"]
}
```

**响应结构:**
```json
{
  "factors": [...],
  "targets": [...],
  "anova": [...],        // 方差分析表
  "main": [...],         // 主效应表
  "sliced_sep": [...],   // 组内比较(分列)
  "sliced_comb": [...],  // 组内比较(组合)
  "corr": [...]          // 相关分析
}
```

### PCA 分析

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/analyze_pca` | POST | 执行主成分分析 |
| `/api/pca_plot` | POST | 生成 PCA 图表 |
| `/api/export_pca` | POST | 导出 PCA 结果 |

### 聚类分析

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/analyze_cluster` | POST | 执行聚类分析 |
| `/api/cluster_elbow` | POST | 生成肘部图 |
| `/api/export_cluster` | POST | 导出聚类数据 |
| `/api/get_cluster_subsets` | GET | 获取聚类子集列表 |

### 导出

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/export` | POST | 导出分析结果到 Excel |
| `/api/select_directory` | GET | 打开本地目录选择对话框 |

## 核心统计函数

### LSD 多重比较

```python
def pairwise_lsd_test_with_mse(stats_df, mse, df_resid, alpha=0.05):
    """
    LSD 多重比较检验

    参数:
        stats_df: 分组统计表 (mean, std, count)
        mse: 残差均方
        df_resid: 残差自由度
        alpha: 显著性水平

    返回:
        [(g1, g2, diff, p_val, is_significant), ...]
    """
```

### CLD 紧凑字母显示

```python
def solve_clique_cld(means, pairwise_data):
    """
    使用 Bron-Kerbosch 算法计算紧凑字母显示

    原理:
        1. 构建邻接矩阵 (非显著差异 = 相邻)
        2. 寻找所有极大团
        3. 按均值排序分配字母

    返回:
        {group_name: letter_string, ...}
    """
```

### 主分析流程

```python
def run_analysis(df, factors, targets):
    """
    完整分析流程

    步骤:
        1. 保持文件原始行顺序 (pd.Categorical)
        2. 对每个性状执行 ANOVA
        3. 计算主效应 LSD
        4. 计算组内切片分析
        5. 计算相关矩阵
    """
```

## 关键设计模式

### 1. 行顺序保持

```python
# 所有 groupby 使用 sort=False
df.groupby(factors, observed=True, sort=False)

# 使用 Categorical 保持首次出现顺序
original_order = pd.unique(clean_col)
df[f] = pd.Categorical(clean_col, categories=original_order, ordered=True)
```

### 2. 列顺序规范

结果表格遵循严格排序:
- 因子列在最左侧
- 指标列按 `Mean | Letter | SD` 模式排列

### 3. JSON 键顺序保持

```python
app.config['JSON_SORT_KEYS'] = False
app.json.sort_keys = False
```

## 错误处理

```python
@app.errorhandler(Exception)
def handle_exception(e):
    """全局错误捕获，返回 JSON 而非 HTML"""
    return jsonify({'error': f'服务器内部错误: {str(e)}'}), 500
```

## 依赖关系

```
app.py
├── pca_analysis.py (可选)
│   └── PCAAnalyzer 类
├── clustering.py (可选)
│   └── ClusterAnalyzer 类
└── 标准库
    ├── pandas
    ├── numpy
    ├── scipy.stats
    └── statsmodels
```
