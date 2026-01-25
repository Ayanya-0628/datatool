# 分析模块 (Analysis Modules)

**最后更新:** 2026-01-25

## 模块概览

| 模块 | 文件 | 行数 | 功能 |
|------|------|------|------|
| PCA 分析 | `pca_analysis.py` | 651 | 主成分分析、可视化、权重计算 |
| 聚类分析 | `clustering.py` | 444 | K-Means、层次聚类、树状图 |

---

## PCA 分析模块 (pca_analysis.py)

### 类结构

```python
class PCAAnalyzer:
    """
    PCA 分析器类

    属性:
        df: 原始 DataFrame
        targets: 数值变量列表
        valid_targets: 有效变量列表
        work_df: 处理后的工作数据
        scaled_data: 标准化数据
        pca: sklearn PCA 对象
        scaler: StandardScaler 对象
        n_components: 主成分数量
        n_samples: 样本数量
    """
```

### 主要方法

| 方法 | 功能 | 返回值 |
|------|------|--------|
| `fit()` | 执行 PCA 分析 | self |
| `get_loadings()` | 获取主成分载荷 | list of dict |
| `get_variance()` | 获取方差贡献 | list of dict |
| `get_weights()` | 计算特征权重 | list of dict |
| `get_scores()` | 计算综合得分 | list of dict |
| `plot_scree()` | 生成碎石图 | dict (base64) |
| `plot_biplot_2d()` | 生成 2D 双标图 | dict (base64) |
| `plot_biplot_3d()` | 生成 3D 双标图 | dict (base64) |

### 权重计算公式

```
weight_j = SUM(|loading_ij| * variance_ratio_i)

其中:
- i: 主成分索引
- j: 变量索引
- loading_ij: 第i个主成分对第j个变量的载荷
- variance_ratio_i: 第i个主成分的方差贡献率
```

### 综合得分公式

```
score_k = SUM(PC_score_ik * variance_ratio_i)

其中:
- k: 样本索引
- PC_score_ik: 第k个样本在第i个主成分上的得分
```

### 置信椭圆

```python
def draw_confidence_ellipse(x, y, ax, n_std=2.0, ...):
    """
    绘制置信椭圆

    原理:
        1. 计算协方差矩阵
        2. 特征值分解
        3. 根据置信水平计算椭圆尺寸

    n_std=2.0 约对应 95% 置信区间
    """
```

### 图表配置

```python
# 字体配置 (跨平台)
Windows: ['SimSun', 'Microsoft YaHei']
macOS: ['Songti SC', 'PingFang SC']
Linux: ['Noto Serif CJK SC']

# 通用设置
plt.rcParams['axes.unicode_minus'] = False  # 负号显示
plt.rcParams['mathtext.fontset'] = 'stix'   # 数学公式字体
```

---

## 聚类分析模块 (clustering.py)

### 类结构

```python
class ClusterAnalyzer:
    """
    聚类分析器

    属性:
        df: 原始 DataFrame
        features: 聚类特征列表
        factors: 标签列列表 (可选)
        valid_features: 有效特征列表
        labels_: 聚类标签
        n_clusters: 聚类数量
        algorithm: 使用的算法
        scaled_data: 标准化数据
        linkage_matrix: 层次聚类连接矩阵
    """
```

### 主要方法

| 方法 | 功能 | 返回值 |
|------|------|--------|
| `fit_kmeans()` | 执行 K-Means 聚类 | self |
| `fit_hierarchical()` | 执行层次聚类 | self |
| `get_elbow_data()` | 计算肘部法则数据 | dict |
| `plot_elbow()` | 生成肘部图 | dict (base64) |
| `plot_dendrogram()` | 生成树状图 | dict (base64) |
| `plot_cluster_scatter()` | 生成聚类散点图 | dict (base64) |
| `get_labeled_data()` | 获取带标签数据 | dict |
| `get_cluster_summary()` | 获取聚类摘要 | dict |
| `export_to_csv()` | 导出 CSV | bytes |

### K-Means 参数

```python
fit_kmeans(n_clusters=3, random_state=42)

# 内部使用
KMeans(n_clusters=n, random_state=seed, n_init=10)
```

### 层次聚类参数

```python
fit_hierarchical(n_clusters=3, linkage_method='ward')

# 可选连接方法
- 'ward': 最小方差法 (默认)
- 'complete': 最大距离法
- 'average': 平均距离法
- 'single': 最小距离法
```

### 数据预处理

```python
def _prepare_data(self):
    """
    1. 筛选有效数值列
    2. 使用均值填充缺失值
    3. StandardScaler 标准化
    4. 样本数检查 (最少3个)
    """
```

### 聚类散点图

使用 PCA 降维到 2D 进行可视化:

```python
pca = PCA(n_components=2)
coords = pca.fit_transform(self.scaled_data)
```

---

## 模块依赖

```
pca_analysis.py
├── numpy
├── pandas
├── sklearn.decomposition.PCA
├── sklearn.preprocessing.StandardScaler
├── matplotlib (可选)
└── scipy.stats.chi2 (置信椭圆)

clustering.py
├── numpy
├── pandas
├── sklearn.cluster.KMeans
├── sklearn.cluster.AgglomerativeClustering
├── sklearn.preprocessing.StandardScaler
├── sklearn.decomposition.PCA
├── scipy.cluster.hierarchy (树状图)
└── matplotlib
```

---

## 使用示例

### PCA 分析

```python
from pca_analysis import PCAAnalyzer

analyzer = PCAAnalyzer(df, ['var1', 'var2', 'var3'])
analyzer.fit()

loadings = analyzer.get_loadings()
weights = analyzer.get_weights()
scree_plot = analyzer.plot_scree(format='png')
```

### 聚类分析

```python
from clustering import ClusterAnalyzer

analyzer = ClusterAnalyzer(df, features=['x1', 'x2'], factors=['group'])
analyzer.fit_kmeans(n_clusters=3)

summary = analyzer.get_cluster_summary()
scatter = analyzer.plot_cluster_scatter()
labeled_data = analyzer.get_labeled_data()
```
