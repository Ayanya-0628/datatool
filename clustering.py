"""
聚类分析模块 (Clustering Analysis Module)
支持 K-Means 和层次聚类，包含可视化功能
"""

import numpy as np
import pandas as pd
from io import BytesIO
import base64
import warnings
from datetime import datetime

# Sklearn imports
try:
    from sklearn.cluster import KMeans, AgglomerativeClustering
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# Scipy imports for dendrogram
try:
    from scipy.cluster.hierarchy import dendrogram, linkage, to_tree
    from scipy.spatial.distance import pdist
    from scipy.stats import pearsonr
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# Matplotlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch


# 字体配置
plt.rcParams['font.sans-serif'] = ['SimSun', 'SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['font.family'] = ['Times New Roman', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False


class ClusterAnalyzer:
    """聚类分析器"""

    CLUSTER_COLORS = [
        '#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6',
        '#1ABC9C', '#E67E22', '#34495E', '#E91E63', '#00BCD4',
    ]
    
    def __init__(self, df, features, factors=None, target_configs=None):
        """
        初始化聚类分析器

        Args:
            df: 原始数据 DataFrame
            features: 用于聚类的特征列名列表 (数值变量)
            factors: 用于标记的因子列名列表 (分类变量, 可选)
            target_configs: 变量配置字典，包含正向化类型和参数
        """
        self.df = df.copy()
        self.features = features
        self.factors = factors if factors else []
        self.target_configs = target_configs if target_configs else {}
        self.valid_features = []
        self.labels_ = None
        self.n_clusters = None
        self.algorithm = None
        self.scaler = StandardScaler()
        self.scaled_data = None
        self.linkage_matrix = None

        # 验证和准备数据
        self._prepare_data()
    
    @staticmethod
    def _normalize_max(series):
        """极大型正向化：(x - min)/(max - min)"""
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series(np.ones_like(series), index=series.index)
        return (series - min_val) / (max_val - min_val)

    @staticmethod
    def _normalize_min(series):
        """极小型正向化：(max - x)/(max - min)"""
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series(np.ones_like(series), index=series.index)
        return (max_val - series) / (max_val - min_val)

    @staticmethod
    def _normalize_interval(series, a, b):
        """区间型正向化"""
        min_x = series.min()
        max_x = series.max()
        M = max(a - min_x, max_x - b)
        if M == 0:
            return pd.Series(np.ones_like(series), index=series.index)

        res = []
        for x in series:
            if x < a:
                res.append(1 - (a - x) / M)
            elif a <= x <= b:
                res.append(1)
            else:
                res.append(1 - (x - b) / M)
        return pd.Series(res, index=series.index)

    def _prepare_data(self):
        """数据预处理"""
        # 筛选有效的数值列
        for col in self.features:
            if col in self.df.columns:
                try:
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
                    if self.df[col].notna().sum() > 0:
                        self.valid_features.append(col)
                except:
                    pass

        if len(self.valid_features) < 2:
            raise ValueError(f"需要至少2个有效的数值特征进行聚类，当前只有 {len(self.valid_features)} 个")

        # 提取数据并处理缺失值（使用均值填充）
        self.data_matrix = self.df[self.valid_features].copy()
        for col in self.valid_features:
            col_mean = self.data_matrix[col].mean()
            self.data_matrix[col].fillna(col_mean, inplace=True)

        # === 新增：数据正向化处理 ===
        if self.target_configs:
            for col in self.valid_features:
                if col in self.target_configs:
                    config = self.target_configs[col]
                    norm_type = config.get('type', 'benefit')

                    if norm_type == 'cost':
                        self.data_matrix[col] = self._normalize_min(self.data_matrix[col])
                    elif norm_type == 'interval':
                        try:
                            a = float(config.get('a', 0))
                            b = float(config.get('b', 0))
                            self.data_matrix[col] = self._normalize_interval(self.data_matrix[col], a, b)
                        except:
                            pass
                    else:
                        # 默认 benefit
                        self.data_matrix[col] = self._normalize_max(self.data_matrix[col])
        # ===========================

        # 标准化
        self.scaled_data = self.scaler.fit_transform(self.data_matrix)
        
        # 样本数检查
        self.n_samples = len(self.scaled_data)
        if self.n_samples < 3:
            raise ValueError(f"样本量过少 (n={self.n_samples})，无法进行聚类分析")
    
    def fit_kmeans(self, n_clusters=3, random_state=42):
        """
        执行 K-Means 聚类
        
        Args:
            n_clusters: 聚类数量
            random_state: 随机种子
        
        Returns:
            self
        """
        if not HAS_SKLEARN:
            raise ImportError("K-Means 需要 scikit-learn 库")
        
        if n_clusters < 2:
            raise ValueError("聚类数量必须 >= 2")
        if n_clusters > self.n_samples:
            raise ValueError(f"聚类数量 ({n_clusters}) 不能超过样本数 ({self.n_samples})")
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
        self.labels_ = kmeans.fit_predict(self.scaled_data)
        self.n_clusters = n_clusters
        self.algorithm = 'kmeans'
        self.cluster_centers_ = kmeans.cluster_centers_
        self.inertia_ = kmeans.inertia_
        
        return self
    
    def fit_hierarchical(self, n_clusters=3, linkage_method='ward'):
        """
        执行层次聚类
        
        Args:
            n_clusters: 聚类数量
            linkage_method: 连接方法 ('ward', 'complete', 'average', 'single')
        
        Returns:
            self
        """
        if not HAS_SKLEARN:
            raise ImportError("层次聚类需要 scikit-learn 库")
        
        if n_clusters < 2:
            raise ValueError("聚类数量必须 >= 2")
        if n_clusters > self.n_samples:
            raise ValueError(f"聚类数量 ({n_clusters}) 不能超过样本数 ({self.n_samples})")
        
        # 对于 ward 方法，需要欧氏距离
        affinity = 'euclidean' if linkage_method == 'ward' else 'euclidean'
        
        agg = AgglomerativeClustering(
            n_clusters=n_clusters,
            linkage=linkage_method
        )
        self.labels_ = agg.fit_predict(self.scaled_data)
        self.n_clusters = n_clusters
        self.algorithm = 'hierarchical'
        self.linkage_method = linkage_method
        
        # 计算 linkage matrix 用于树状图
        if HAS_SCIPY:
            self.linkage_matrix = linkage(self.scaled_data, method=linkage_method)
        
        return self

    @staticmethod
    def _encode_plot(fig, format='png', dpi=150):
        buffer = BytesIO()
        fig.savefig(buffer, format=format, dpi=dpi, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        plt.close(fig)
        if format == 'svg':
            return {'data': buffer.getvalue().decode('utf-8'), 'format': 'svg'}
        return {'data': base64.b64encode(buffer.getvalue()).decode('utf-8'), 'format': format}
    
    def get_elbow_data(self, max_k=10):
        """
        计算肘部法则数据
        
        Args:
            max_k: 最大聚类数
        
        Returns:
            dict: {k_values: [...], inertias: [...]}
        """
        if not HAS_SKLEARN:
            raise ImportError("肘部法则需要 scikit-learn 库")
        
        max_k = min(max_k, self.n_samples - 1, 15)  # 限制最大 K
        if max_k < 2:
            max_k = 2
        
        k_values = list(range(2, max_k + 1))
        inertias = []
        
        for k in k_values:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(self.scaled_data)
            inertias.append(kmeans.inertia_)
        
        return {
            'k_values': k_values,
            'inertias': inertias
        }
    
    def plot_elbow(self, max_k=10, format='png'):
        """
        绘制肘部法则图
        
        Args:
            max_k: 最大聚类数
            format: 输出格式 ('png', 'svg', 'pdf')
        
        Returns:
            dict: {data: base64_string, format: format}
        """
        elbow_data = self.get_elbow_data(max_k)
        k_values = elbow_data['k_values']
        inertias = elbow_data['inertias']
        
        fig, ax = plt.subplots(figsize=(8, 5))
        
        # 绘制折线图
        ax.plot(k_values, inertias, 'b-o', linewidth=2, markersize=8)
        ax.set_xlabel('聚类数 (K)', fontsize=12)
        ax.set_ylabel('SSE (簇内平方和)', fontsize=12)
        ax.set_title('肘部法则 - 最优聚类数选择', fontsize=14, fontweight='bold')
        ax.set_xticks(k_values)
        ax.grid(False)

        # 标注建议点（变化率最大的点）
        if len(inertias) > 2:
            # 计算变化率
            diffs = np.diff(inertias)
            diffs2 = np.diff(diffs)
            if len(diffs2) > 0:
                elbow_idx = np.argmax(np.abs(diffs2)) + 2
                suggested_k = k_values[elbow_idx] if elbow_idx < len(k_values) else k_values[-1]
                ax.axvline(x=suggested_k, color='r', linestyle='--', alpha=0.7, 
                          label=f'建议 K={suggested_k}')
                ax.legend()
        
        plt.tight_layout()
        
        # 保存到内存
        buffer = BytesIO()
        fig.savefig(buffer, format=format, dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        plt.close(fig)
        
        if format == 'svg':
            return {'data': buffer.getvalue().decode('utf-8'), 'format': 'svg'}
        else:
            return {'data': base64.b64encode(buffer.getvalue()).decode('utf-8'), 'format': format}
    
    def plot_dendrogram(self, format='png', truncate_mode='lastp', p=30):
        """
        绘制树状图
        
        Args:
            format: 输出格式
            truncate_mode: 截断模式
            p: 显示的叶节点数
        
        Returns:
            dict: {data: base64_string, format: format}
        """
        if not HAS_SCIPY:
            raise ImportError("树状图需要 scipy 库")
        
        # 计算 linkage matrix
        if self.linkage_matrix is None:
            method = getattr(self, 'linkage_method', 'ward')
            self.linkage_matrix = linkage(self.scaled_data, method=method)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 绘制树状图
        dendrogram(
            self.linkage_matrix,
            ax=ax,
            truncate_mode=truncate_mode if self.n_samples > p else None,
            p=p,
            leaf_rotation=90,
            leaf_font_size=8,
            color_threshold=0.7 * max(self.linkage_matrix[:, 2])
        )
        
        ax.set_xlabel('样本', fontsize=12)
        ax.set_ylabel('距离', fontsize=12)
        ax.set_title('层次聚类树状图 (Dendrogram)', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        # 保存
        buffer = BytesIO()
        fig.savefig(buffer, format=format, dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        plt.close(fig)
        
        if format == 'svg':
            return {'data': buffer.getvalue().decode('utf-8'), 'format': 'svg'}
        else:
            return {'data': base64.b64encode(buffer.getvalue()).decode('utf-8'), 'format': format}
    
    def plot_cluster_scatter(self, format='png'):
        """
        绘制聚类散点图（2D PCA 投影）
        
        Args:
            format: 输出格式
        
        Returns:
            dict: {data: base64_string, format: format}
        """
        if self.labels_ is None:
            raise ValueError("请先执行聚类分析")
        
        # PCA 降维到 2D
        pca = PCA(n_components=2)
        coords = pca.fit_transform(self.scaled_data)
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # 颜色映射
        colors = plt.cm.Set1(np.linspace(0, 1, self.n_clusters))
        
        # 绘制各聚类
        for i in range(self.n_clusters):
            mask = self.labels_ == i
            ax.scatter(coords[mask, 0], coords[mask, 1], 
                      c=[colors[i]], label=f'聚类 {i+1} (n={mask.sum()})',
                      s=60, alpha=0.7, edgecolors='white', linewidths=0.5)
        
        # 如果是 K-Means，标注聚类中心
        if self.algorithm == 'kmeans' and hasattr(self, 'cluster_centers_'):
            centers_2d = pca.transform(self.cluster_centers_)
            ax.scatter(centers_2d[:, 0], centers_2d[:, 1], 
                      c='black', marker='X', s=200, edgecolors='white',
                      linewidths=2, label='聚类中心')
        
        # 标签
        var_explained = pca.explained_variance_ratio_ * 100
        ax.set_xlabel(f'PC1 ({var_explained[0]:.1f}%)', fontsize=12)
        ax.set_ylabel(f'PC2 ({var_explained[1]:.1f}%)', fontsize=12)
        ax.set_title('聚类结果可视化 (PCA 2D 投影)', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(False)

        plt.tight_layout()
        
        # 保存
        buffer = BytesIO()
        fig.savefig(buffer, format=format, dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        plt.close(fig)
        
        if format == 'svg':
            return {'data': buffer.getvalue().decode('utf-8'), 'format': 'svg'}
        else:
            return {'data': base64.b64encode(buffer.getvalue()).decode('utf-8'), 'format': format}
    
    def get_labeled_data(self):
        """
        获取带聚类标签的原始数据
        
        Returns:
            dict: {headers: [...], rows: [[...], ...], cluster_counts: {...}}
        """
        if self.labels_ is None:
            raise ValueError("请先执行聚类分析")
        
        # 构建结果 DataFrame
        result_df = self.df.copy()
        
        # 1. 因子列 (最左侧)
        factor_cols = [col for col in self.factors if col in self.df.columns]
        
        # 2. 聚类标签 (中间)
        result_df['Cluster_Label'] = self.labels_ + 1  # 1-indexed
        
        # 3. 特征列 (右侧)
        feature_cols = self.valid_features
        
        # 重新排序列：因子 -> 标签 -> 特征 -> 其他
        ordered_cols = factor_cols + ['Cluster_Label'] + feature_cols
        remaining_cols = [c for c in result_df.columns if c not in ordered_cols]
        final_cols = ordered_cols + remaining_cols
        
        result_df = result_df[final_cols]
        
        # 转换为表格格式（处理 NaN 和特殊值）
        result_df = result_df.replace({np.nan: None})
        headers = list(result_df.columns)
        rows = result_df.values.tolist()
        
        # 统计各聚类样本数
        cluster_counts = {}
        for i in range(self.n_clusters):
            cluster_counts[f'聚类 {i+1}'] = int((self.labels_ == i).sum())
        
        return {
            'headers': headers,
            'rows': rows,
            'cluster_counts': cluster_counts,
            'n_clusters': self.n_clusters,
            'algorithm': self.algorithm
        }
    
    def get_cluster_summary(self):
        """
        获取聚类摘要统计
        
        Returns:
            dict: 各聚类的统计信息
        """
        if self.labels_ is None:
            raise ValueError("请先执行聚类分析")
        
        summary = {
            'algorithm': self.algorithm,
            'n_clusters': self.n_clusters,
            'n_samples': self.n_samples,
            'n_features': len(self.valid_features),
            'features': self.valid_features,
            'cluster_sizes': []
        }
        
        for i in range(self.n_clusters):
            cluster_data = self.data_matrix[self.labels_ == i]
            size = len(cluster_data)
            summary['cluster_sizes'].append({
                'cluster': i + 1,
                'size': size,
                'percentage': round(100 * size / self.n_samples, 1)
            })
        
        return summary
    
    def plot_heatmap(self, format='png', row_cluster=True, col_cluster=True):
        """
        绘制聚类热图 (支持样本聚类和特征聚类)
        模拟 Seaborn clustermap 效果，但仅使用 matplotlib + scipy
        """
        if not HAS_SCIPY:
            return {'error': '绘制热图需要 scipy 库'}

        # 准备数据 (使用标准化后的数据以便于比较)
        # 或者使用归一化后的 data_matrix (0-1范围)
        # 为了热图颜色显示清晰，通常标准化比较好，或者将 data_matrix 归一化到 0-1
        # 这里使用 scaled_data (Z-score)
        data = self.scaled_data

        # 如果数据量太大，进行采样以避免绘图过慢
        if data.shape[0] > 1000:
            indices = np.linspace(0, data.shape[0]-1, 1000, dtype=int)
            data = data[indices]

        fig = plt.figure(figsize=(10, 10))

        # 定义网格布局
        # [树状图(左), 热图(中), 颜色条(右)]
        # [空, 树状图(上), 空]

        # 尺寸比例
        left_margin = 0.1
        bottom_margin = 0.1
        width = 0.6
        height = 0.6
        dendro_size = 0.15

        # 1. 计算行聚类 (样本聚类)
        row_dendro_ax = fig.add_axes([left_margin, bottom_margin, dendro_size, height])
        row_linkage = linkage(data, method='ward')
        row_dendro = dendrogram(row_linkage, orientation='left', ax=row_dendro_ax, no_labels=True)
        row_dendro_ax.set_xticks([])
        row_dendro_ax.set_yticks([])
        # 移除边框
        for spine in row_dendro_ax.spines.values():
            spine.set_visible(False)

        # 根据聚类结果重排数据行
        row_idx = row_dendro['leaves']
        data_ordered = data[row_idx, :]

        # 2. 计算列聚类 (特征聚类)
        col_dendro_ax = fig.add_axes([left_margin + dendro_size, bottom_margin + height, width, dendro_size])
        col_linkage = linkage(data.T, method='ward')
        col_dendro = dendrogram(col_linkage, orientation='top', ax=col_dendro_ax, no_labels=True)
        col_dendro_ax.set_xticks([])
        col_dendro_ax.set_yticks([])
        for spine in col_dendro_ax.spines.values():
            spine.set_visible(False)

        # 根据聚类结果重排数据列
        col_idx = col_dendro['leaves']
        data_ordered = data_ordered[:, col_idx]
        feature_names = [self.valid_features[i] for i in col_idx]

        # 3. 绘制热图
        heatmap_ax = fig.add_axes([left_margin + dendro_size, bottom_margin, width, height])
        im = heatmap_ax.imshow(data_ordered, aspect='auto', cmap='coolwarm', interpolation='nearest')

        # 设置标签
        heatmap_ax.set_xticks(np.arange(len(feature_names)))
        heatmap_ax.set_xticklabels(feature_names, rotation=90, fontsize=10)
        heatmap_ax.set_yticks([]) # 隐藏样本索引

        # 4. 颜色条
        cbar_ax = fig.add_axes([left_margin + dendro_size + width + 0.02, bottom_margin, 0.02, height])
        plt.colorbar(im, cax=cbar_ax, label='Z-Score')

        # 保存
        return self._encode_plot(fig, format=format, dpi=150)

    def plot_corr_heatmap(self, format='png'):
        """
        绘制特征相关性聚类热图 (复刻用户提供的图片样式)
        上半三角显示系数，下半三角显示颜色+显著性标记
        """
        if not HAS_SCIPY:
            return {'error': '绘制热图需要 scipy 库'}

        # 计算相关系数矩阵和 P值矩阵
        n_vars = self.data_matrix.shape[1]
        columns = self.data_matrix.columns.tolist()
        corr_matrix = self.data_matrix.corr()
        p_matrix = pd.DataFrame(np.zeros((n_vars, n_vars)), columns=columns, index=columns)

        # 计算 P 值
        for col1 in columns:
            for col2 in columns:
                if col1 == col2:
                    p_matrix.loc[col1, col2] = 0.0
                else:
                    # 处理可能的 NaN
                    clean_data = self.data_matrix[[col1, col2]].dropna()
                    if len(clean_data) > 2:
                        _, p = pearsonr(clean_data[col1], clean_data[col2])
                        p_matrix.loc[col1, col2] = p
                    else:
                        p_matrix.loc[col1, col2] = 1.0

        data = corr_matrix.values
        p_values = p_matrix.values
        names = corr_matrix.columns.tolist()

        fig = plt.figure(figsize=(12, 10)) #稍微加大一点
        # Add title with timestamp
        current_time = datetime.now().strftime('%H:%M:%S')
        fig.suptitle(f'Feature Correlation Clustering ({current_time})', fontsize=14, fontweight='bold')

        # 布局定义
        left_margin = 0.05
        bottom_margin = 0.10
        width = 0.7
        height = 0.7
        dendro_size = 0.12

        # 1. 顶部树状图 (列聚类)
        col_dendro_ax = fig.add_axes([left_margin + dendro_size, bottom_margin + height + 0.01, width, dendro_size])
        linkage_matrix = linkage(data, method='ward') # 使用相关性数据进行聚类
        col_dendro = dendrogram(linkage_matrix, orientation='top', ax=col_dendro_ax, no_labels=True)
        col_dendro_ax.set_axis_off()

        # 2. 左侧树状图 (行聚类 - 镜像)
        row_dendro_ax = fig.add_axes([left_margin, bottom_margin, dendro_size, height])
        # orientation='left'：根在左，叶子在右（贴近热图），符合要求
        row_dendro = dendrogram(linkage_matrix, orientation='left', ax=row_dendro_ax, no_labels=True)

        # 反转Y轴以匹配 imshow 的 'upper' origin (从上到下)
        row_dendro_ax.invert_yaxis()

        row_dendro_ax.set_axis_off()

        # 获取排序索引
        idx = col_dendro['leaves']
        data_ordered = data[idx, :][:, idx]
        p_ordered = p_values[idx, :][:, idx]
        names_ordered = [names[i] for i in idx]

        # 3. 热图
        heatmap_ax = fig.add_axes([left_margin + dendro_size, bottom_margin, width, height])

        # 准备掩码数据：上三角设为 NaN (不显示颜色)
        mask = np.triu(np.ones_like(data_ordered, dtype=bool), k=1)
        data_masked = data_ordered.copy()
        data_masked[mask] = np.nan

        # 绘制下三角热图
        im = heatmap_ax.imshow(data_masked, aspect='auto', cmap='coolwarm', vmin=-1, vmax=1)

        # 移除边框线 (Spines)
        for spine in heatmap_ax.spines.values():
            spine.set_visible(False)

        # 设置标签
        heatmap_ax.set_xticks(np.arange(len(names_ordered)))
        heatmap_ax.set_yticks(np.arange(len(names_ordered)))
        heatmap_ax.set_xticklabels(names_ordered, rotation=45, ha='right', fontsize=10)
        heatmap_ax.set_yticklabels(names_ordered, fontsize=10)
        heatmap_ax.yaxis.tick_right() # y轴标签在右侧

        # 移除刻度线但保留文字
        heatmap_ax.tick_params(axis='both', which='both', length=0)

        # 绘制网格线 (作为边框)
        heatmap_ax.set_xticks(np.arange(len(names_ordered) + 1) - 0.5, minor=True)
        heatmap_ax.set_yticks(np.arange(len(names_ordered) + 1) - 0.5, minor=True)
        # heatmap_ax.grid(which="minor", color="gray", linestyle='-', linewidth=0.5)
        # 注意：imshow 上层遮挡 grid，所以最好手动画框或者调整 zorder

        # 在格子里显示内容
        n = len(names)
        print(f'DEBUG: plot_corr_heatmap running. n={n}')
        # 字体大小根据变量数量自动调整
        font_size = 10 if n < 10 else (8 if n < 20 else 6)

        if n <= 30: # 变量太多时不显示任何文本
            for i in range(n):
                for j in range(n):
                    val = data_ordered[i, j]

                    # 绘制单元格边框 (每个格子都画) - 黑色边框
                    rect = plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor='black', linewidth=1, zorder=10)
                    heatmap_ax.add_patch(rect)

                    if i < j:
                        # 上三角：显示相关系数数值
                        # 上三角背景是白色的，边框用黑色
                        # 注意：上面的 rect 已经画了边框，这里不需要重复画，除非为了遮挡 fill
                        # 但是 imshow 已经被 mask 了，所以这里是透明的？
                        # 不，imshow masked 区域通常是白色的（因为 facecolor='white'）
                        # 为了确保上三角纯白且有黑框：
                        rect_upper = plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=True, facecolor='white', edgecolor='black', linewidth=1, zorder=10)
                        heatmap_ax.add_patch(rect_upper)

                        heatmap_ax.text(j, i, f"{val:.2f}", ha="center", va="center", color="black", fontsize=font_size, zorder=20)
                    elif i > j:
                        # 下三角：显示显著性标记
                        p_val = p_ordered[i, j]
                        sig = ""
                        if p_val < 0.001: sig = "***"
                        elif p_val < 0.01: sig = "**"
                        elif p_val < 0.05: sig = "*"

                        # 如果有显著性，显示星号；颜色根据背景深浅调整
                        if sig:
                            text_color = "white" if abs(val) > 0.5 else "black"
                            # 调整星号位置，使其略微居中偏下或居中
                            heatmap_ax.text(j, i, sig, ha="center", va="center", color=text_color, fontsize=font_size + 2, fontweight='bold', zorder=20)
                    else:
                        # 对角线
                        pass

        # 4. 颜色条
        cbar_ax = fig.add_axes([left_margin + dendro_size + width + 0.12, bottom_margin + height/4, 0.02, height/2])
        plt.colorbar(im, cax=cbar_ax, label='Correlation')

        # 保存
        return self._encode_plot(fig, format=format, dpi=150)

    def _get_plot_linkage(self):
        """获取或计算用于绘图的 linkage 矩阵"""
        if self.linkage_matrix is not None:
            return self.linkage_matrix
        method = getattr(self, 'linkage_method', 'ward')
        self.linkage_matrix = linkage(self.scaled_data, method=method)
        return self.linkage_matrix

    def _get_sample_labels(self):
        """获取样本标签列表（优先使用因子列组合，否则用行索引）"""
        if self.factors:
            valid = [c for c in self.factors if c in self.df.columns]
            if valid:
                return self.df[valid].astype(str).agg('_'.join, axis=1).tolist()
        return [str(i) for i in range(len(self.df))]

    @staticmethod
    def _normalize_display_frame(df):
        """将 DataFrame 每列归一化到 [0, 1] 用于环形热图显示"""
        result = df.copy()
        for col in result.columns:
            cmin = result[col].min()
            cmax = result[col].max()
            if cmax > cmin:
                result[col] = (result[col] - cmin) / (cmax - cmin)
            else:
                result[col] = 0.5
        return result

    def plot_circular_heatmap(self, format='png'):
        """
        绘制环形聚类热图，复刻 R 脚本中的“圆形树状图 + 外环热图”表现。
        """
        if self.labels_ is None:
            raise ValueError("请先执行聚类分析")
        if not HAS_SCIPY:
            return {'error': '绘制环形聚类热图需要 scipy 库'}

        row_linkage = self._get_plot_linkage()
        dendro_info = dendrogram(row_linkage, no_plot=True)
        sample_order = dendro_info['leaves']
        sample_labels = self._get_sample_labels()
        ordered_labels = [sample_labels[idx] for idx in sample_order]
        ordered_clusters = (self.labels_[sample_order] + 1).astype(int)

        display_frame = self._normalize_display_frame(self.data_matrix[self.valid_features])
        ordered_values = display_frame.iloc[sample_order]

        n_samples = len(sample_order)
        n_features = len(self.valid_features)
        if n_samples < 3:
            raise ValueError("样本数过少，无法绘制环形聚类热图")

        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection='polar')
        ax.set_theta_zero_location('E')
        ax.set_theta_direction(-1)
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['polar'].set_visible(False)

        gap_radians = np.deg2rad(38)
        span = 2 * np.pi - gap_radians
        start_angle = gap_radians / 2
        angle_step = span / n_samples
        ordered_angles = [start_angle + (i + 0.5) * angle_step for i in range(n_samples)]
        leaf_angle_map = {sample_idx: ordered_angles[pos] for pos, sample_idx in enumerate(sample_order)}

        tree = to_tree(row_linkage, rd=False)
        max_dist = max(float(tree.dist), 1e-9)
        tree_inner_radius = 0.16
        tree_outer_radius = 0.58
        cluster_ring_bottom = tree_outer_radius + 0.02
        cluster_ring_height = 0.035
        feature_ring_inner = cluster_ring_bottom + cluster_ring_height + 0.02
        feature_ring_width = min(0.07, 0.34 / max(n_features, 1))
        label_radius = feature_ring_inner + n_features * feature_ring_width + 0.12
        legend_theta = 0.0

        node_angle_cache = {}
        leaf_count_cache = {}
        node_groups_cache = {}
        cluster_color_map = {
            idx + 1: self.CLUSTER_COLORS[idx % len(self.CLUSTER_COLORS)]
            for idx in range(max(int(self.n_clusters or 0), 1))
        }

        def get_leaf_count(node):
            if node.id in leaf_count_cache:
                return leaf_count_cache[node.id]
            if node.is_leaf():
                leaf_count_cache[node.id] = 1
            else:
                leaf_count_cache[node.id] = get_leaf_count(node.left) + get_leaf_count(node.right)
            return leaf_count_cache[node.id]

        def get_node_angle(node):
            if node.id in node_angle_cache:
                return node_angle_cache[node.id]
            if node.is_leaf():
                node_angle_cache[node.id] = leaf_angle_map[node.id]
            else:
                left_angle = get_node_angle(node.left)
                right_angle = get_node_angle(node.right)
                left_count = get_leaf_count(node.left)
                right_count = get_leaf_count(node.right)
                node_angle_cache[node.id] = (
                    left_angle * left_count + right_angle * right_count
                ) / (left_count + right_count)
            return node_angle_cache[node.id]

        def get_node_radius(node):
            if node.is_leaf():
                return tree_outer_radius
            return tree_outer_radius - (float(node.dist) / max_dist) * (tree_outer_radius - tree_inner_radius)

        def get_node_groups(node):
            if node.id in node_groups_cache:
                return node_groups_cache[node.id]
            if node.is_leaf():
                node_groups_cache[node.id] = {int(self.labels_[node.id]) + 1}
            else:
                node_groups_cache[node.id] = get_node_groups(node.left) | get_node_groups(node.right)
            return node_groups_cache[node.id]

        def get_branch_color(node):
            groups = get_node_groups(node)
            if len(groups) == 1:
                return cluster_color_map[next(iter(groups))]
            return '#222222'

        def draw_tree(node):
            if node.is_leaf():
                return

            left_node = node.left
            right_node = node.right
            node_radius = get_node_radius(node)
            left_theta = get_node_angle(left_node)
            right_theta = get_node_angle(right_node)

            theta_arc = np.linspace(left_theta, right_theta, 120)
            ax.plot(theta_arc, np.full_like(theta_arc, node_radius), color=get_branch_color(node), linewidth=1.0, alpha=0.95)
            ax.plot([left_theta, left_theta], [get_node_radius(left_node), node_radius], color=get_branch_color(left_node), linewidth=1.0, alpha=0.95)
            ax.plot([right_theta, right_theta], [get_node_radius(right_node), node_radius], color=get_branch_color(right_node), linewidth=1.0, alpha=0.95)

            draw_tree(left_node)
            draw_tree(right_node)

        draw_tree(tree)

        for theta, cluster_id in zip(ordered_angles, ordered_clusters):
            ax.bar(
                theta,
                cluster_ring_height,
                width=angle_step * 0.98,
                bottom=cluster_ring_bottom,
                color=cluster_color_map[int(cluster_id)],
                edgecolor='none',
                align='center',
            )

        cmap = mcolors.LinearSegmentedColormap.from_list('circular_cluster_heatmap', ['#2166AC', '#FFFFFF', '#B2182B'])
        norm = mcolors.TwoSlopeNorm(vmin=0.0, vcenter=0.5, vmax=1.0)

        for feature_idx, feature_name in enumerate(self.valid_features):
            ring_bottom = feature_ring_inner + feature_idx * feature_ring_width
            values = ordered_values[feature_name].to_numpy(dtype=float)
            colors = [cmap(norm(value)) for value in values]
            ax.bar(
                ordered_angles,
                np.full(n_samples, feature_ring_width * 0.96),
                width=angle_step * 0.98,
                bottom=ring_bottom,
                color=colors,
                edgecolor='white',
                linewidth=0.25,
                align='center',
            )
            ax.text(
                legend_theta,
                ring_bottom + feature_ring_width * 0.5,
                feature_name,
                ha='left',
                va='center',
                fontsize=10,
                fontweight='bold',
                color='#334155',
            )

        show_labels = n_samples <= 80
        label_font_size = 10 if n_samples <= 24 else 8 if n_samples <= 40 else 6
        if show_labels:
            for theta, label, cluster_id in zip(ordered_angles, ordered_labels, ordered_clusters):
                theta_deg = np.degrees(theta)
                rotation = theta_deg - 90
                ha = 'left'
                if 90 < theta_deg < 270:
                    rotation += 180
                    ha = 'right'
                ax.text(
                    theta,
                    label_radius,
                    label,
                    rotation=rotation,
                    rotation_mode='anchor',
                    ha=ha,
                    va='center',
                    fontsize=label_font_size,
                    color=cluster_color_map[int(cluster_id)],
                )
        else:
            ax.text(
                legend_theta,
                label_radius,
                f'样本数 {n_samples}，为保证可读性已隐藏外圈标签',
                ha='left',
                va='center',
                fontsize=10,
                color='#475569',
            )

        legend_handles = [
            Patch(facecolor=cluster_color_map[idx + 1], edgecolor='none', label=f'聚类 {idx + 1}')
            for idx in range(int(self.n_clusters or 0))
        ]
        if legend_handles:
            fig.legend(handles=legend_handles, loc='upper right', bbox_to_anchor=(0.98, 0.98), frameon=False, title='聚类分组')

        cax = fig.add_axes([0.84, 0.14, 0.02, 0.22])
        colorbar = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax)
        colorbar.set_label('指标相对水平', fontsize=10)
        colorbar.ax.tick_params(labelsize=9)

        ax.set_ylim(0, label_radius + 0.14)
        fig.suptitle('环形聚类热图', fontsize=16, fontweight='bold', y=0.98)
        return self._encode_plot(fig, format=format, dpi=120)

    def export_to_csv(self):
        """
        导出带聚类标签的数据为 CSV 字节流
        
        Returns:
            bytes: CSV 数据
        """
        if self.labels_ is None:
            raise ValueError("请先执行聚类分析")
        
        result_df = self.df.copy()
        result_df['Cluster_Label'] = self.labels_ + 1
        
        buffer = BytesIO()
        result_df.to_csv(buffer, index=False, encoding='utf-8-sig')
        buffer.seek(0)
        return buffer.getvalue()
