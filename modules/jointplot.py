"""
联合分布图模块 (Joint Plot Module)
功能：生成带边际分布的分组回归散点图
支持 KDE 密度曲线和直方图两种边际分布类型
"""

import io
import numpy as np
import pandas as pd
from scipy import stats

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.ticker import MaxNLocator

# 字体配置: 英文/数字 Times New Roman, 中文逐字形回退宋体
plt.rcParams['font.family'] = ['Times New Roman', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False

# 学术配色方案（柔和清新风格）
GROUP_COLORS = [
    '#5B9BD5',  # 蓝
    '#70AD47',  # 绿
    '#ED7D31',  # 橙
    '#FFC000',  # 金
    '#9B59B6',  # 紫
    '#E74C3C',  # 红
    '#1ABC9C',  # 青
    '#34495E',  # 灰蓝
]


def _compute_regression(x, y):
    """计算线性回归及其统计量。"""
    mask = np.isfinite(x) & np.isfinite(y)
    x_clean, y_clean = x[mask], y[mask]
    n = len(x_clean)
    if n < 3:
        return None

    slope, intercept, r_value, p_value, std_err = stats.linregress(x_clean, y_clean)

    x_pred = np.linspace(x_clean.min(), x_clean.max(), 200)
    y_pred = slope * x_pred + intercept

    # 95% 置信区间
    x_mean = x_clean.mean()
    ss_x = np.sum((x_clean - x_mean) ** 2)
    # 残差标准误差
    y_hat = slope * x_clean + intercept
    residuals = y_clean - y_hat
    s_e = np.sqrt(np.sum(residuals ** 2) / (n - 2)) if n > 2 else 0

    ci = 1.96 * s_e * np.sqrt(1.0 / n + (x_pred - x_mean) ** 2 / ss_x)

    return {
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_value ** 2,
        'p_value': p_value,
        'x_pred': x_pred,
        'y_pred': y_pred,
        'ci_lower': y_pred - ci,
        'ci_upper': y_pred + ci,
    }


def _format_p(p):
    """格式化 p 值显示。"""
    if p < 0.001:
        return '<0.001'
    return f'{p:.3f}'


def _significance_star(p):
    """根据 p 值返回显著性星号。"""
    if p < 0.001:
        return '***'
    if p < 0.01:
        return '**'
    if p < 0.05:
        return '*'
    return 'ns'


def generate_jointplot(df, x_col, y_col, group_col=None, marginal_type='kde',
                       format='png', dpi=150):
    """
    生成联合分布图（带边际分布的分组回归散点图）。

    Args:
        df: pandas DataFrame
        x_col: X轴变量名（数值型）
        y_col: Y轴变量名（数值型）
        group_col: 分组变量名（因子型，可选）
        marginal_type: 边际分布类型 ('kde' 或 'histogram')
        format: 输出格式 ('png', 'pdf', 'svg')
        dpi: 图像分辨率

    Returns:
        io.BytesIO: 图片字节流
    """
    # 数据准备
    cols_needed = [x_col, y_col]
    if group_col:
        cols_needed.append(group_col)

    plot_df = df[cols_needed].copy()
    plot_df[x_col] = pd.to_numeric(plot_df[x_col], errors='coerce')
    plot_df[y_col] = pd.to_numeric(plot_df[y_col], errors='coerce')
    plot_df = plot_df.dropna(subset=[x_col, y_col])

    if len(plot_df) < 3:
        raise ValueError('有效数据点不足（至少需要 3 个）')

    # 分组
    if group_col and group_col in plot_df.columns:
        groups = list(pd.unique(plot_df[group_col].astype(str)))
    else:
        groups = [None]
        group_col = None

    # 创建图形布局
    fig = plt.figure(figsize=(8, 8))
    gs = gridspec.GridSpec(2, 2, width_ratios=[4, 1], height_ratios=[1, 4],
                           hspace=0.06, wspace=0.06)

    ax_main = fig.add_subplot(gs[1, 0])
    ax_top = fig.add_subplot(gs[0, 0], sharex=ax_main)
    ax_right = fig.add_subplot(gs[1, 1], sharey=ax_main)

    # 隐藏边际图的刻度标签和刻度线
    plt.setp(ax_top.get_xticklabels(), visible=False)
    plt.setp(ax_right.get_yticklabels(), visible=False)
    ax_top.tick_params(axis='x', labelbottom=False, bottom=False)
    ax_top.tick_params(axis='y', left=False, labelleft=False)
    ax_right.tick_params(axis='y', labelleft=False, left=False)
    ax_right.tick_params(axis='x', bottom=False, labelbottom=False)

    # 统计标注列表
    annotations = []

    for idx, group_name in enumerate(groups):
        color = GROUP_COLORS[idx % len(GROUP_COLORS)]

        if group_col is not None:
            mask = plot_df[group_col].astype(str) == group_name
            sub = plot_df[mask]
        else:
            sub = plot_df
            group_name = None

        x_data = sub[x_col].values.astype(float)
        y_data = sub[y_col].values.astype(float)

        if len(x_data) < 3:
            continue

        # ===== 中心散点图 =====
        ax_main.scatter(x_data, y_data, c=color, alpha=0.55, s=35,
                        edgecolors='white', linewidths=0.3, zorder=5,
                        label=group_name if group_name else None)

        # ===== 回归线 + 置信带 =====
        reg = _compute_regression(x_data, y_data)
        if reg is not None:
            ax_main.plot(reg['x_pred'], reg['y_pred'], color=color,
                         linewidth=2, zorder=6)
            ax_main.fill_between(reg['x_pred'], reg['ci_lower'], reg['ci_upper'],
                                 color=color, alpha=0.12, zorder=4)

            # 收集标注
            label = group_name if group_name else ''
            annotations.append({
                'label': label,
                'r2': reg['r_squared'],
                'p': reg['p_value'],
                'color': color
            })

        # ===== 边际分布 =====
        if marginal_type == 'kde':
            # KDE 密度曲线
            try:
                kde_x = stats.gaussian_kde(x_data, bw_method='scott')
                x_grid = np.linspace(x_data.min(), x_data.max(), 200)
                ax_top.plot(x_grid, kde_x(x_grid), color=color, linewidth=1.5)
                ax_top.fill_between(x_grid, kde_x(x_grid), alpha=0.25, color=color)
            except Exception:
                pass

            try:
                kde_y = stats.gaussian_kde(y_data, bw_method='scott')
                y_grid = np.linspace(y_data.min(), y_data.max(), 200)
                ax_right.plot(kde_y(y_grid), y_grid, color=color, linewidth=1.5)
                ax_right.fill_betweenx(y_grid, kde_y(y_grid), alpha=0.25, color=color)
            except Exception:
                pass
        else:
            # 直方图
            bins_x = min(25, max(8, int(np.sqrt(len(x_data)))))
            bins_y = min(25, max(8, int(np.sqrt(len(y_data)))))

            ax_top.hist(x_data, bins=bins_x, alpha=0.45, color=color,
                        edgecolor='white', linewidth=0.5)
            ax_right.hist(y_data, bins=bins_y, alpha=0.45, color=color,
                          edgecolor='white', linewidth=0.5,
                          orientation='horizontal')

    # ===== R² / p 值标注 =====
    for i, ann in enumerate(annotations):
        stars = _significance_star(ann['p'])
        if ann['label']:
            text = f"{ann['label']}: R² = {ann['r2']:.3f}{stars} , p = {_format_p(ann['p'])}"
        else:
            text = f"R² = {ann['r2']:.3f}{stars} , p = {_format_p(ann['p'])}"

        ax_main.text(0.03, 0.97 - i * 0.06, text,
                     transform=ax_main.transAxes, fontsize=9,
                     color=ann['color'], fontweight='bold',
                     verticalalignment='top',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                               edgecolor='none', alpha=0.75),
                     zorder=10)

    # ===== 坐标轴标签 =====
    ax_main.set_xlabel(x_col, fontsize=12, fontweight='bold')
    ax_main.set_ylabel(y_col, fontsize=12, fontweight='bold')

    # 控制刻度数量 (~5个)
    ax_main.xaxis.set_major_locator(MaxNLocator(nbins=5))
    ax_main.yaxis.set_major_locator(MaxNLocator(nbins=5))

    # 隐藏边际图的坐标轴标签
    ax_top.set_ylabel('')
    ax_right.set_xlabel('')

    # 移除边际图外框线
    ax_top.spines['top'].set_visible(False)
    ax_top.spines['right'].set_visible(False)
    ax_top.spines['left'].set_visible(False)
    ax_top.tick_params(left=False)
    ax_top.set_yticks([])

    ax_right.spines['top'].set_visible(False)
    ax_right.spines['right'].set_visible(False)
    ax_right.spines['bottom'].set_visible(False)
    ax_right.tick_params(bottom=False)
    ax_right.set_xticks([])

    # 图例（仅分组时显示）
    if group_col is not None and len(groups) > 1:
        ax_main.legend(loc='lower right', fontsize=9, framealpha=0.8,
                       edgecolor='none')

    # 空白区域（右上角）
    ax_empty = fig.add_subplot(gs[0, 1])
    ax_empty.axis('off')

    plt.tight_layout()

    # 输出
    buf = io.BytesIO()
    fig.savefig(buf, format=format, dpi=dpi, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf
