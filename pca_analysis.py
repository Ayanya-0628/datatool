"""
PCA 分析模块
功能：主成分分析、可视化图表生成、权重和综合得分计算
"""

import io
import base64
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# 图表库 (延迟导入以避免在无头环境中出错)
try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse
    from mpl_toolkits.mplot3d import Axes3D
    
    # 配置字体：中文宋体，西文 Times New Roman
    import platform
    if platform.system() == 'Windows':
        # Windows 系统使用宋体
        plt.rcParams['font.sans-serif'] = ['SimSun', 'STSong', 'Microsoft YaHei', 'SimHei']
        plt.rcParams['font.serif'] = ['Times New Roman', 'SimSun']
    elif platform.system() == 'Darwin':
        # macOS 系统
        plt.rcParams['font.sans-serif'] = ['Songti SC', 'STSong', 'PingFang SC']
        plt.rcParams['font.serif'] = ['Times New Roman', 'Songti SC']
    else:
        # Linux 系统
        plt.rcParams['font.sans-serif'] = ['Noto Serif CJK SC', 'WenQuanYi Micro Hei']
        plt.rcParams['font.serif'] = ['Times New Roman', 'Noto Serif CJK SC']
    
    # 设置默认字体族
    plt.rcParams['font.family'] = ['serif', 'sans-serif']
    # 解决负号显示问题
    plt.rcParams['axes.unicode_minus'] = False
    # 数学文本使用 Times New Roman
    plt.rcParams['mathtext.fontset'] = 'stix'
    
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def draw_confidence_ellipse(x, y, ax, n_std=2.0, facecolor='none', **kwargs):
    """
    绘制置信椭圆 (Confidence Ellipse)
    
    Args:
        x, y: 数据点 (PC1 和 PC2 得分)
        ax: matplotlib axes 对象
        n_std: 标准差倍数，2.0 约对应 95% 置信区间
        facecolor: 填充颜色
        **kwargs: 传递给 Ellipse 的其他参数 (edgecolor, linewidth 等)
        
    Returns:
        Ellipse 对象，如果数据点不足则返回 None
    """
    if len(x) < 3 or len(y) < 3:
        # 数据点不足以计算协方差
        return None
    
    # 计算协方差矩阵
    cov = np.cov(x, y)
    
    # 处理协方差矩阵奇异的情况
    if cov[0, 0] == 0 or cov[1, 1] == 0:
        return None
    
    # 计算特征值和特征向量
    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    vals, vecs = vals[order], vecs[:, order]
    
    # 计算椭圆角度
    theta = np.degrees(np.arctan2(*vecs[:, 0][::-1]))
    
    # 计算椭圆宽度和高度 (n_std 个标准差)
    width, height = 2 * n_std * np.sqrt(vals)
    
    # 创建椭圆
    ellipse = Ellipse(
        xy=(np.mean(x), np.mean(y)),
        width=width,
        height=height,
        angle=theta,
        facecolor=facecolor,
        **kwargs
    )
    
    ax.add_patch(ellipse)
    return ellipse



class PCAAnalyzer:
    """
    PCA 分析器类
    
    使用方法:
        analyzer = PCAAnalyzer(df, targets)
        analyzer.fit()
        loadings = analyzer.get_loadings()
        variance = analyzer.get_variance()
        weights = analyzer.get_weights()
        scores = analyzer.get_scores()
    """
    
    def __init__(self, df, targets, group_by=None):
        """
        初始化 PCA 分析器
        
        Args:
            df: 原始 DataFrame
            targets: 用于分析的数值变量名列表
            group_by: 分组列名列表，如果提供则先按组计算均值
        """
        self.df = df
        self.targets = targets
        self.group_by = group_by if group_by else []
        self.valid_targets = []
        self.work_df = None
        self.scaled_data = None
        self.pca = None
        self.scaler = None
        self.n_components = 0
        self.n_samples = 0
        self.is_fitted = False
        self.missing_info = {}
        self.group_labels = None  # 保存分组标签（如果有分组）
        
    def fit(self, auto_aggregate=True):
        """
        执行 PCA 分析
        
        Args:
            auto_aggregate: 若有分组列且数据有重复，自动计算均值
        """
        # 1. 验证并提取有效的数值列
        for col in self.targets:
            if col in self.df.columns:
                numeric_series = pd.to_numeric(self.df[col], errors='coerce')
                valid_count = numeric_series.notna().sum()
                missing_count = numeric_series.isna().sum()
                if valid_count > 0:
                    self.valid_targets.append(col)
                    self.missing_info[col] = {
                        'valid': int(valid_count), 
                        'missing': int(missing_count)
                    }
        
        if len(self.valid_targets) < 2:
            raise ValueError('有效的数值变量少于2个，无法进行 PCA 分析')
        
        # 2. 提取数据并转换为数值
        self.work_df = self.df[self.valid_targets].copy()
        for col in self.valid_targets:
            self.work_df[col] = pd.to_numeric(self.work_df[col], errors='coerce')
        
        original_samples = len(self.work_df)
        
        # 3. 使用均值填充缺失值
        for col in self.valid_targets:
            col_mean = self.work_df[col].mean()
            if pd.notna(col_mean):
                self.work_df[col] = self.work_df[col].fillna(col_mean)
            else:
                self.work_df[col] = self.work_df[col].fillna(0)
        
        # 删除仍然存在缺失值的行
        self.work_df = self.work_df.dropna()
        self.n_samples = len(self.work_df)
        
        if self.n_samples < 3:
            info_str = ", ".join([
                f"{k}: {v['valid']}有效/{v['missing']}缺失" 
                for k, v in list(self.missing_info.items())[:5]
            ])
            raise ValueError(f'有效样本数少于3（当前: {self.n_samples}），变量缺失情况: {info_str}')
        
        # 4. 标准化数据
        self.scaler = StandardScaler()
        self.scaled_data = self.scaler.fit_transform(self.work_df)
        
        # 5. 执行 PCA
        self.n_components = min(len(self.valid_targets), self.n_samples)
        self.pca = PCA(n_components=self.n_components)
        self.pca.fit(self.scaled_data)
        
        self.is_fitted = True
        return self
    
    def get_loadings(self, sort_by_abs=True):
        """
        获取主成分载荷表
        
        Args:
            sort_by_abs: 是否按 PC1 载荷的绝对值降序排列
        
        Returns:
            list of dict: 载荷数据，每行是一个变量
        """
        self._check_fitted()
        
        loadings_data = []
        pc_names = [f'PC{i+1}' for i in range(self.n_components)]
        
        for i, var_name in enumerate(self.valid_targets):
            row = {
                '变量': var_name,
                '_abs_pc1': abs(self.pca.components_[0, i])  # 用于排序的临时字段
            }
            for j, pc_name in enumerate(pc_names):
                row[pc_name] = round(self.pca.components_[j, i], 4)
            loadings_data.append(row)
        
        # 按 PC1 载荷绝对值降序排列
        if sort_by_abs:
            loadings_data.sort(key=lambda x: x['_abs_pc1'], reverse=True)
        
        # 移除临时排序字段
        for row in loadings_data:
            del row['_abs_pc1']
        
        return loadings_data
    
    def get_variance(self):
        """
        获取方差贡献表
        
        Returns:
            list of dict: 方差贡献数据
        """
        self._check_fitted()
        
        variance_data = []
        cumulative = 0
        
        for i in range(self.n_components):
            cumulative += self.pca.explained_variance_ratio_[i]
            variance_data.append({
                '主成分': f'PC{i+1}',
                '特征值': round(self.pca.explained_variance_[i], 4),
                '方差贡献率 (%)': round(self.pca.explained_variance_ratio_[i] * 100, 2),
                '累计贡献率 (%)': round(cumulative * 100, 2)
            })
        
        return variance_data
    
    def get_weights(self):
        """
        计算特征权重 (基于方差贡献率加权的载荷系数)
        
        公式: weight_j = Σ(|loading_ij| × variance_ratio_i)
        其中 i 为主成分索引，j 为变量索引
        
        Returns:
            list of dict: 权重数据
        """
        self._check_fitted()
        
        weights = np.zeros(len(self.valid_targets))
        
        for i in range(self.n_components):
            # 使用载荷绝对值 × 方差贡献率
            weights += np.abs(self.pca.components_[i, :]) * self.pca.explained_variance_ratio_[i]
        
        # 归一化权重 (总和为1)
        weights_normalized = weights / weights.sum()
        
        # 构建结果
        weights_data = []
        for j, var_name in enumerate(self.valid_targets):
            weights_data.append({
                '变量': var_name,
                '原始权重': round(weights[j], 6),
                '归一化权重': round(weights_normalized[j], 6),
                '权重百分比 (%)': round(weights_normalized[j] * 100, 2)
            })
        
        # 按权重降序排列
        weights_data.sort(key=lambda x: x['归一化权重'], reverse=True)
        
        return weights_data
    
    def get_scores(self):
        """
        计算样本综合得分和排名
        
        公式: score_k = Σ(PC_score_ik × variance_ratio_i)
        其中 k 为样本索引，i 为主成分索引
        
        Returns:
            list of dict: 得分和排名数据
        """
        self._check_fitted()
        
        # 获取主成分得分
        pc_scores = self.pca.transform(self.scaled_data)
        
        # 计算综合得分 (加权)
        composite_scores = np.zeros(self.n_samples)
        for i in range(self.n_components):
            composite_scores += pc_scores[:, i] * self.pca.explained_variance_ratio_[i]
        
        # 构建结果
        scores_data = []
        for k in range(self.n_samples):
            row = {
                '样本序号': k + 1,
                '综合得分': round(composite_scores[k], 4)
            }
            # 添加前3个主成分得分
            for i in range(min(3, self.n_components)):
                row[f'PC{i+1}得分'] = round(pc_scores[k, i], 4)
            scores_data.append(row)
        
        # 按综合得分降序排列并添加排名
        scores_data.sort(key=lambda x: x['综合得分'], reverse=True)
        for rank, row in enumerate(scores_data, 1):
            row['排名'] = rank
        
        # 重新按样本序号排列以便对应原始数据
        scores_data.sort(key=lambda x: x['样本序号'])
        
        return scores_data
    
    def plot_scree(self, format='png', dpi=600):
        """
        生成碎石图 (Scree Plot)
        
        Args:
            format: 输出格式 ('png', 'pdf', 'svg')
            dpi: 图像分辨率
            
        Returns:
            str: Base64 编码的图像数据 (PNG) 或二进制数据 (PDF/SVG)
        """
        self._check_fitted()
        self._check_matplotlib()
        
        fig, ax = plt.subplots(figsize=(10, 6), dpi=dpi)
        
        # 数据
        components = range(1, self.n_components + 1)
        variance_ratio = self.pca.explained_variance_ratio_ * 100
        cumulative = np.cumsum(variance_ratio)
        
        # 条形图 - 方差贡献率
        bars = ax.bar(components, variance_ratio, alpha=0.7, color='#2196F3', label='方差贡献率')
        
        # 折线图 - 累计贡献率
        ax.plot(components, cumulative, 'ro-', linewidth=2, markersize=8, label='累计贡献率')
        
        # 添加数值标签
        for i, (v, c) in enumerate(zip(variance_ratio, cumulative)):
            ax.annotate(f'{v:.1f}%', (i+1, v), ha='center', va='bottom', fontsize=9)
            ax.annotate(f'{c:.1f}%', (i+1, c), ha='center', va='bottom', fontsize=9, color='red')
        
        # 样式
        ax.set_xlabel('主成分', fontsize=12)
        ax.set_ylabel('方差贡献率 (%)', fontsize=12)
        ax.set_title('碎石图 (Scree Plot)', fontsize=14, fontweight='bold')
        ax.set_xticks(components)
        ax.set_xticklabels([f'PC{i}' for i in components])
        ax.legend(loc='center right')
        
        plt.tight_layout()
        
        return self._export_figure(fig, format)
    
    def plot_biplot_2d(self, pc_x=1, pc_y=2, format='png', dpi=600,
                        group_labels=None, draw_ellipse=False, confidence_level=0.95):
        """
        生成 2D 双标图 (Biplot)，支持分组着色和置信椭圆
        
        Args:
            pc_x: X 轴主成分编号 (1-based)
            pc_y: Y 轴主成分编号 (1-based)
            format: 输出格式 ('png', 'pdf', 'svg')
            dpi: 图像分辨率
            group_labels: 分组标签数组，长度应与样本数相同
            draw_ellipse: 是否绘制置信椭圆
            confidence_level: 置信水平 (0.50-0.99)
            
        Returns:
            str: Base64 编码的图像数据 (PNG) 或二进制数据 (PDF/SVG)
        """
        self._check_fitted()
        self._check_matplotlib()
        
        # 转换为 0-based 索引
        idx_x, idx_y = pc_x - 1, pc_y - 1
        
        if idx_x >= self.n_components or idx_y >= self.n_components:
            raise ValueError(f'主成分索引超出范围，最大为 {self.n_components}')
        
        fig, ax = plt.subplots(figsize=(10, 8), dpi=dpi)
        
        # 获取得分
        scores = self.pca.transform(self.scaled_data)
        score_x = scores[:, idx_x]
        score_y = scores[:, idx_y]
        
        # 颜色映射
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#E91E63', '#9C27B0', 
                  '#00BCD4', '#795548', '#607D8B', '#F44336', '#3F51B5']
        
        # 根据是否有分组标签决定绘制方式
        if group_labels is not None and len(group_labels) == len(score_x):
            # 获取唯一分组
            unique_groups = list(dict.fromkeys(group_labels))  # 保持顺序
            
            # 置信水平转换为 n_std
            # 对于 2D 椭圆 (df=2)，95% 对应 chi2.ppf(0.95, 2) ≈ 5.991, sqrt ≈ 2.448
            from scipy.stats import chi2
            n_std = np.sqrt(chi2.ppf(confidence_level, 2))
            
            for i, group in enumerate(unique_groups):
                color = colors[i % len(colors)]
                mask = np.array([g == group for g in group_labels])
                
                # 绘制该组的散点
                ax.scatter(score_x[mask], score_y[mask], 
                          c=color, alpha=0.6, s=50, label=str(group))
                
                # 绘制置信椭圆 (带半透明填充)
                if draw_ellipse and mask.sum() >= 3:
                    draw_confidence_ellipse(
                        score_x[mask], score_y[mask], ax,
                        n_std=n_std,
                        facecolor=color,  # 填充颜色与边框相同
                        edgecolor=color,
                        linewidth=2,
                        linestyle='-',
                        alpha=0.15  # 低透明度实现阴影效果
                    )
            
            ax.legend(title='分组', loc='best', fontsize=9)
        else:
            # 无分组标签，使用单一颜色
            ax.scatter(score_x, score_y, c='#2196F3', alpha=0.6, s=50, label='样本')
        
        # 绘制载荷向量
        loadings = self.pca.components_
        scale_factor = max(np.abs(scores).max(), 1) * 0.8
        
        for i, var_name in enumerate(self.valid_targets):
            ax.arrow(0, 0, 
                     loadings[idx_x, i] * scale_factor, 
                     loadings[idx_y, i] * scale_factor,
                     head_width=0.05 * scale_factor, 
                     head_length=0.03 * scale_factor,
                     fc='#F44336', ec='#F44336', alpha=0.8)
            ax.text(loadings[idx_x, i] * scale_factor * 1.15, 
                    loadings[idx_y, i] * scale_factor * 1.15,
                    var_name, fontsize=9, ha='center', va='center', color='#D32F2F')
        
        # 样式
        var_x = self.pca.explained_variance_ratio_[idx_x] * 100
        var_y = self.pca.explained_variance_ratio_[idx_y] * 100
        
        ax.set_xlabel(f'PC{pc_x} ({var_x:.1f}%)', fontsize=12)
        ax.set_ylabel(f'PC{pc_y} ({var_y:.1f}%)', fontsize=12)
        
        title = '主成分分析双标图 (Biplot)'
        if draw_ellipse:
            title += f' [{int(confidence_level*100)}% 置信椭圆]'
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        
        return self._export_figure(fig, format)
    
    def plot_biplot_3d(self, pc_x=1, pc_y=2, pc_z=3, format='png', dpi=600):
        """
        生成 3D 双标图 (Biplot)
        
        Args:
            pc_x, pc_y, pc_z: 三个轴的主成分编号 (1-based)
            format: 输出格式 ('png', 'pdf', 'svg')
            dpi: 图像分辨率
            
        Returns:
            str: Base64 编码的图像数据 (PNG) 或二进制数据 (PDF/SVG)
        """
        self._check_fitted()
        self._check_matplotlib()
        
        # 检查是否有足够的主成分
        if self.n_components < 3:
            raise ValueError('主成分数量少于3，无法生成 3D 双标图')
        
        # 转换为 0-based 索引
        idx_x, idx_y, idx_z = pc_x - 1, pc_y - 1, pc_z - 1
        
        fig = plt.figure(figsize=(12, 10), dpi=dpi)
        ax = fig.add_subplot(111, projection='3d')
        
        # 获取得分
        scores = self.pca.transform(self.scaled_data)
        
        # 绘制样本点
        ax.scatter(scores[:, idx_x], scores[:, idx_y], scores[:, idx_z],
                   c='#2196F3', alpha=0.6, s=50, label='样本')
        
        # 绘制载荷向量
        loadings = self.pca.components_
        scale_factor = max(np.abs(scores[:, :3]).max(), 1) * 0.8
        
        for i, var_name in enumerate(self.valid_targets):
            ax.quiver(0, 0, 0,
                      loadings[idx_x, i] * scale_factor,
                      loadings[idx_y, i] * scale_factor,
                      loadings[idx_z, i] * scale_factor,
                      color='#F44336', alpha=0.8, arrow_length_ratio=0.1)
            ax.text(loadings[idx_x, i] * scale_factor * 1.2,
                    loadings[idx_y, i] * scale_factor * 1.2,
                    loadings[idx_z, i] * scale_factor * 1.2,
                    var_name, fontsize=9, color='#D32F2F')
        
        # 样式
        var_x = self.pca.explained_variance_ratio_[idx_x] * 100
        var_y = self.pca.explained_variance_ratio_[idx_y] * 100
        var_z = self.pca.explained_variance_ratio_[idx_z] * 100
        
        ax.set_xlabel(f'PC{pc_x} ({var_x:.1f}%)', fontsize=10)
        ax.set_ylabel(f'PC{pc_y} ({var_y:.1f}%)', fontsize=10)
        ax.set_zlabel(f'PC{pc_z} ({var_z:.1f}%)', fontsize=10)
        ax.set_title('3D 主成分分析双标图', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        return self._export_figure(fig, format)
    
    def get_summary(self):
        """
        获取分析摘要
        
        Returns:
            dict: 分析摘要信息
        """
        self._check_fitted()
        
        return {
            'n_samples': self.n_samples,
            'n_variables': len(self.valid_targets),
            'n_components': self.n_components,
            'total_variance_explained': round(sum(self.pca.explained_variance_ratio_) * 100, 2),
            'variables': self.valid_targets,
            'imputation_used': True
        }
    
    def _check_fitted(self):
        """检查是否已执行 fit()"""
        if not self.is_fitted:
            raise RuntimeError('请先调用 fit() 方法执行 PCA 分析')
    
    def _check_matplotlib(self):
        """检查 matplotlib 是否可用"""
        if not HAS_MATPLOTLIB:
            raise ImportError('图表生成需要 matplotlib，请安装: pip install matplotlib')
    
    def _export_figure(self, fig, format='png'):
        """
        导出图表
        
        Args:
            fig: matplotlib Figure 对象
            format: 输出格式 ('png', 'pdf', 'svg')
            
        Returns:
            dict: 包含图像数据和格式信息
        """
        buf = io.BytesIO()
        
        if format.lower() == 'png':
            fig.savefig(buf, format='png', bbox_inches='tight', facecolor='white')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close(fig)
            return {
                'format': 'png',
                'data': img_base64,
                'mime': 'image/png'
            }
        elif format.lower() == 'pdf':
            fig.savefig(buf, format='pdf', bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close(fig)
            return {
                'format': 'pdf',
                'data': img_base64,
                'mime': 'application/pdf'
            }
        elif format.lower() == 'svg':
            fig.savefig(buf, format='svg', bbox_inches='tight')
            buf.seek(0)
            svg_str = buf.getvalue().decode('utf-8')
            plt.close(fig)
            return {
                'format': 'svg',
                'data': svg_str,
                'mime': 'image/svg+xml'
            }
        else:
            plt.close(fig)
            raise ValueError(f'不支持的格式: {format}')


def run_pca_analysis_enhanced(df, targets):
    """
    运行增强版 PCA 分析 (便捷函数)
    
    Args:
        df: 原始 DataFrame
        targets: 用于分析的数值变量名列表
        
    Returns:
        dict: 包含所有分析结果
    """
    analyzer = PCAAnalyzer(df, targets)
    analyzer.fit()
    
    results = {
        'summary': analyzer.get_summary(),
        'loadings': analyzer.get_loadings(),
        'variance': analyzer.get_variance(),
        'weights': analyzer.get_weights(),
        'scores': analyzer.get_scores()
    }
    
    # 尝试生成图表
    if HAS_MATPLOTLIB:
        try:
            results['scree_plot'] = analyzer.plot_scree()
            results['biplot_2d'] = analyzer.plot_biplot_2d()
            if analyzer.n_components >= 3:
                results['biplot_3d'] = analyzer.plot_biplot_3d()
        except Exception as e:
            results['plot_error'] = str(e)
    
    return results
