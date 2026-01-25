"""
聚类分析模块 (Clustering Analysis Module)
支持 K-Means 和层次聚类，包含可视化功能
"""

import numpy as np
import pandas as pd
from io import BytesIO
import base64
import warnings

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
    from scipy.cluster.hierarchy import dendrogram, linkage
    from scipy.spatial.distance import pdist
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# Matplotlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 字体配置
plt.rcParams['font.sans-serif'] = ['SimSun', 'SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['font.family'] = ['Times New Roman', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False


class ClusterAnalyzer:
    """聚类分析器"""
    
    def __init__(self, df, features, factors=None):
        """
        初始化聚类分析器
        
        Args:
            df: 原始数据 DataFrame
            features: 用于聚类的特征列名列表 (数值变量)
            factors: 用于标记的因子列名列表 (分类变量, 可选)
        """
        self.df = df.copy()
        self.features = features
        self.factors = factors if factors else []
        self.valid_features = []
        self.labels_ = None
        self.n_clusters = None
        self.algorithm = None
        self.scaler = StandardScaler()
        self.scaled_data = None
        self.linkage_matrix = None
        
        # 验证和准备数据
        self._prepare_data()
    
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
        ax.grid(True, alpha=0.3)
        
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
        ax.grid(True, alpha=0.3)
        
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
