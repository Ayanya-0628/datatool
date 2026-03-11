"""
分组柱状图模块 - 支持多级分组标签、误差棒、显著性字母标记、自定义颜色

字体规范：中文宋体，西文 Times New Roman（与 PCA 模块保持一致）
多级 X 轴采用论文风格色带分组标签（矩形表格样式 + 亮色背景）
背景透明输出
"""
import io
import base64
import platform
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
from matplotlib import rcParams

# ── 字体配置：中文宋体 + 西文 Times New Roman ──
_system = platform.system()
if _system == 'Windows':
    rcParams['font.sans-serif'] = ['SimSun', 'STSong', 'Microsoft YaHei', 'SimHei']
    rcParams['font.serif'] = ['Times New Roman', 'SimSun']
elif _system == 'Darwin':
    rcParams['font.sans-serif'] = ['Songti SC', 'STSong', 'PingFang SC']
    rcParams['font.serif'] = ['Times New Roman', 'Songti SC']
else:
    rcParams['font.sans-serif'] = ['Noto Serif CJK SC', 'WenQuanYi Micro Hei']
    rcParams['font.serif'] = ['Times New Roman', 'Noto Serif CJK SC']

rcParams['font.family'] = ['serif', 'sans-serif']
rcParams['axes.unicode_minus'] = False
rcParams['mathtext.fontset'] = 'stix'


def generate_bar_chart(df, group_cols, value_col, bar_colors=None,
                       band_colors=None, show_error_bars=True,
                       show_letters=False, letter_col=None,
                       y_label=None, title=None, fig_width=None,
                       fig_height=6, dpi=300, bar_width=0.6,
                       font_size=10, output_format='png',
                       y_min=None, y_max=None, y_step=None):
    """
    生成分组柱状图

    Parameters
    ----------
    df : pd.DataFrame
    group_cols : list[str]
        分组列名列表，从外到内排列（如 ['品种', '氮肥水平', '氮肥管理方式']）
        最内层为柱子的颜色分组（图例）
    value_col : str
    bar_colors : list[str] | None
    show_error_bars : bool
    show_letters : bool
    letter_col : str | None
    y_label, title : str | None
    fig_width, fig_height, dpi, bar_width, font_size : numeric
    output_format : str ('png', 'pdf', 'svg')

    Returns
    -------
    dict: { 'data': base64_string, 'format': output_format }
    """

    # 1. 数据预处理
    work_df = df.copy()
    for col in group_cols:
        work_df[col] = work_df[col].astype(str).replace('nan', np.nan)
        work_df[col] = work_df[col].ffill()

    work_df[value_col] = pd.to_numeric(work_df[value_col], errors='coerce')
    work_df = work_df.dropna(subset=[value_col])

    if work_df.empty:
        raise ValueError(f"数值列 '{value_col}' 没有有效数据")

    # 2. 按分组计算均值和标准差
    stats = work_df.groupby(group_cols, sort=False, observed=True)[value_col].agg(
        ['mean', 'std', 'count']
    ).reset_index()

    if show_letters and letter_col and letter_col in work_df.columns:
        letter_data = work_df.groupby(group_cols, sort=False, observed=True)[letter_col].first().reset_index()
        stats = stats.merge(letter_data, on=group_cols, how='left')
    elif show_letters and len(group_cols) >= 2:
        # 自动计算显著性字母：在每个外层分组内，对内层分组做 LSD 多重比较
        letter_col = '__auto_letter__'
        stats[letter_col] = ''
        stats = _auto_compute_letters(work_df, stats, group_cols, value_col, letter_col)

    n_groups = len(group_cols)

    if n_groups == 1:
        return _draw_single_group(stats, group_cols[0], value_col, bar_colors,
                                  show_error_bars, show_letters, letter_col,
                                  y_label, title, fig_width, fig_height, dpi,
                                  bar_width, font_size, output_format,
                                  y_min, y_max, y_step)
    else:
        return _draw_multi_group(stats, group_cols, value_col, bar_colors,
                                 band_colors, show_error_bars, show_letters,
                                 letter_col, y_label, title, fig_width,
                                 fig_height, dpi, bar_width, font_size,
                                 output_format, y_min, y_max, y_step)


def _draw_single_group(stats, group_col, value_col, bar_colors,
                        show_error_bars, show_letters, letter_col,
                        y_label, title, fig_width, fig_height, dpi,
                        bar_width, font_size, output_format,
                        y_min=None, y_max=None, y_step=None):
    """绘制单层分组柱状图"""
    n = len(stats)
    if fig_width is None:
        fig_width = max(6, n * 0.8 + 2)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)

    x = np.arange(n)
    colors = bar_colors or _default_colors(n)

    ax.bar(x, stats['mean'], width=bar_width,
           color=colors[:n], edgecolor='black', linewidth=0.5, zorder=3)

    if show_error_bars:
        ax.errorbar(x, stats['mean'], yerr=stats['std'],
                     fmt='none', ecolor='black', elinewidth=1,
                     capsize=3, capthick=1, zorder=4)

    if show_letters and letter_col and letter_col in stats.columns:
        for i, (_, row) in enumerate(stats.iterrows()):
            letter = str(row.get(letter_col, ''))
            if letter and letter != 'nan':
                y_pos = row['mean'] + (row['std'] if show_error_bars and not np.isnan(row['std']) else 0) + stats['mean'].max() * 0.02
                ax.text(i, y_pos, letter, ha='center', va='bottom',
                        fontsize=font_size - 1, color='black', fontname='Times New Roman')

    ax.set_xticks(x)
    ax.set_xticklabels(stats[group_col].astype(str), fontsize=font_size - 1)

    _apply_clean_style(ax, y_label, title, font_size, stats,
                       y_min=y_min, y_max=y_max, y_step=y_step)

    plt.tight_layout()
    return _fig_to_base64(fig, output_format, dpi)


def _draw_multi_group(stats, group_cols, value_col, bar_colors,
                       band_colors, show_error_bars, show_letters,
                       letter_col, y_label, title, fig_width,
                       fig_height, dpi, bar_width, font_size,
                       output_format, y_min=None, y_max=None, y_step=None):
    """
    绘制多层分组柱状图（论文风格矩形色带分组标签）

    X 轴结构（从上到下）：
    - 柱子底部：最内层分组值 tick labels
    - 第一行色带（白底黑框）：次内层分组值
    - 第二行色带（亮色底黑框）：最外层分组值
    """
    inner_col = group_cols[-1]   # 最内层 = 柱子颜色分组（图例）
    outer_cols = group_cols[:-1]  # 外层 = X 轴色带分组

    # 获取内层唯一值
    inner_vals = list(pd.unique(stats[inner_col].astype(str)))
    n_inner = len(inner_vals)

    # 获取外层组合
    if len(outer_cols) == 1:
        outer_keys = [(g,) for g in pd.unique(stats[outer_cols[0]].astype(str))]
    else:
        raw_keys = list(stats[outer_cols].drop_duplicates().itertuples(index=False, name=None))
        seen = set()
        outer_keys = []
        for k in raw_keys:
            k_str = tuple(str(x) for x in k)
            if k_str not in seen:
                seen.add(k_str)
                outer_keys.append(k_str)

    n_outer = len(outer_keys)

    # 颜色
    colors = bar_colors if bar_colors and len(bar_colors) >= n_inner else _default_colors(n_inner)

    # 计算位置
    cluster_gap = bar_width * 0.5  # 簇间间距（稍大一些以便分隔组）
    group_width = n_inner * bar_width + cluster_gap

    if fig_width is None:
        fig_width = max(8, n_outer * group_width * 0.9 + 3)

    # 色带需要额外底部空间
    n_band_levels = len(outer_cols)
    bottom_margin = 0.15 + n_band_levels * 0.065

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)

    # ── 绘制柱子 ──
    group_centers = []
    all_tick_positions = []
    all_tick_labels = []

    for g_idx, outer_key in enumerate(outer_keys):
        group_center = g_idx * group_width
        group_centers.append(group_center)

        for i_idx, inner_val in enumerate(inner_vals):
            x_pos = group_center + (i_idx - n_inner / 2 + 0.5) * bar_width
            all_tick_positions.append(x_pos)
            all_tick_labels.append(inner_val)

            # 查找对应数据
            mask = stats[inner_col].astype(str) == inner_val
            for c_idx, col in enumerate(outer_cols):
                mask = mask & (stats[col].astype(str) == outer_key[c_idx])

            row_data = stats[mask]

            if not row_data.empty:
                mean_val = row_data['mean'].values[0]
                std_val = row_data['std'].values[0] if show_error_bars else 0

                ax.bar(x_pos, mean_val, width=bar_width * 0.85,
                       color=colors[i_idx], edgecolor='black',
                       linewidth=0.5, zorder=3,
                       label=inner_val if g_idx == 0 else '')

                if show_error_bars and not np.isnan(std_val):
                    ax.errorbar(x_pos, mean_val, yerr=std_val,
                                fmt='none', ecolor='black', elinewidth=1,
                                capsize=2.5, capthick=0.8, zorder=4)

                # 显著性字母标记（在误差棒上方）
                if show_letters and letter_col and letter_col in stats.columns:
                    letter = str(row_data[letter_col].values[0])
                    if letter and letter != 'nan':
                        y_top = mean_val + (std_val if show_error_bars and not np.isnan(std_val) else 0)
                        ax.text(x_pos, y_top + stats['mean'].max() * 0.015,
                                letter, ha='center', va='bottom',
                                fontsize=font_size - 1, color='black',
                                fontname='Times New Roman')

    # ── X 轴刻度：用完美表格替代原来的 tick labels 和 色带 ──
    ax.set_xticks([])

    # ── 样式 ──
    _apply_clean_style(ax, y_label, title, font_size, stats,
                       y_min=y_min, y_max=y_max, y_step=y_step)

    # 图例：固定右上角、无边框
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, loc='upper right', fontsize=font_size - 2,
                  frameon=False,
                  title=inner_col, title_fontsize=font_size - 1)

    # 适当调整 Y 轴上限（如果用户没有手动指定）
    if y_max is None:
        auto_y_max = stats['mean'].max() + stats['std'].max() * 1.5
        ax.set_ylim(top=auto_y_max * 1.15)
    if y_min is None:
        ax.set_ylim(bottom=0)

    # 强制 X 轴范围完美包裹表格，表格的左侧将与左 y 轴贴合
    table_left_edge = group_centers[0] - group_width / 2
    table_right_edge = group_centers[-1] + group_width / 2
    ax.set_xlim(table_left_edge, table_right_edge)

    # 底部边界控制：为表格留出空间
    n_rows = len(outer_cols) + 1
    bottom_margin = 0.08 + n_rows * 0.06

    # 先做 tight_layout，再调整底部空间
    plt.tight_layout()
    fig.subplots_adjust(bottom=bottom_margin)

    # ── 绘制无缝的三行表格（不在同一图层问题修复）──
    _draw_perfect_table(ax, outer_keys, outer_cols, inner_vals, group_centers,
                        group_width, n_inner, font_size, band_colors)

    return _fig_to_base64(fig, output_format, dpi)


def _fmt_label(val):
    """将数值格式化为整洁的标签字符串：140.0 → '140'，'140.0' → '140'，3.5 → '3.5'"""
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    s = str(val)
    # 处理字符串形式的 "140.0" → "140"
    if '.' in s:
        try:
            f = float(s)
            if f == int(f):
                return str(int(f))
        except (ValueError, OverflowError):
            pass
    return s


def _draw_perfect_table(ax, outer_keys, outer_cols, inner_vals, group_centers,
                        group_width, n_inner, font_size, band_colors):
    """
    绘制底部的完美拼接表格（三行表格）

    每一列无缝拼接，共享边框，彻底解决矩形不在同一图层的问题。
    """
    n_levels = len(outer_cols)
    trans = ax.get_xaxis_transform()
    
    row_height = 0.07  # 每行高度 (axes fraction)
    n_outer = len(outer_keys)
    table_left_edge = group_centers[0] - group_width / 2
    col_w = group_width / n_inner  # 每个最小单元格（列）的宽度
    
    if not band_colors or len(band_colors) == 0:
        actual_band_colors = [
            '#FFFFFF',   # r=0: 最内部标签（刻度）
            '#FFFFCC',   # r=1: 次外层（浅黄）
            '#00CED1',   # r=2: 最外层（青色）
            '#E0E0E0',   # r=3: 默认浅灰
        ]
    else:
        # 用户指定的颜色，直接按层级使用（最内层往往固定，但允许用户传进来）
        actual_band_colors = band_colors
    
    table_levels = []
    
    # 构建各行的单元格合并信息
    # r = 0: 最内部（柱子本身的类别表示）
    row_0 = []
    c = 0
    for g_idx in range(n_outer):
        for val in inner_vals:
            row_0.append({'text': _fmt_label(val), 'start_col': c, 'end_col': c})
            c += 1
    table_levels.append(row_0)
    
    # r > 0: 外部分组层级
    for r in range(1, n_levels + 1):
        outer_lvl_idx = n_levels - r
        row_intervals = []
        i = 0
        while i < n_outer:
            val = outer_keys[i][outer_lvl_idx]
            start_g = i
            while i < n_outer and outer_keys[i][outer_lvl_idx] == val:
                i += 1
            end_g = i - 1
            row_intervals.append({
                'text': _fmt_label(val),
                'start_col': start_g * n_inner,
                'end_col': end_g * n_inner + (n_inner - 1)
            })
        table_levels.append(row_intervals)
        
    # 绘制表格
    for r, intervals in enumerate(table_levels):
        y_top = 0 - r * row_height
        y_bottom = y_top - row_height
        bg_color = actual_band_colors[r % len(actual_band_colors)]
        
        for cell in intervals:
            x_left = table_left_edge + cell['start_col'] * col_w
            x_right = table_left_edge + (cell['end_col'] + 1) * col_w
            width = x_right - x_left
            
            # 绘制无缝矩形单元格，clip_on=False 否则会被图形边缘裁剪
            rect = Rectangle((x_left, y_bottom), width, row_height,
                             transform=trans,
                             facecolor=bg_color, edgecolor='black',
                             linewidth=0.8, clip_on=False, zorder=10)
            ax.add_patch(rect)
            
            weight = 'normal' if r == 0 else 'bold'
            fsize = font_size - (1 if r == 0 else 0)
            
            ax.text((x_left + x_right)/2, y_top - row_height/2,
                    cell['text'],
                    transform=trans, ha='center', va='center',
                    fontsize=fsize, fontweight=weight,
                    clip_on=False, zorder=11)


def _apply_clean_style(ax, y_label, title, font_size, stats,
                       y_min=None, y_max=None, y_step=None):
    """应用干净的论文风格 —— 四边轴线可见，无网格线"""
    # 去掉网格线
    ax.grid(False)

    # 四边轴线全部显示
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(True)
        ax.spines[spine].set_linewidth(0.8)

    # Y 轴刻度朝内，X 轴底部刻度朝外
    ax.tick_params(axis='y', direction='in', length=4, width=0.8)
    ax.tick_params(axis='x', direction='out', length=3, width=0.8)
    # 上轴和右轴显示刻度线但不显示标签
    ax.tick_params(axis='x', top=True, labeltop=False, direction='in', length=3, width=0.8)
    ax.tick_params(axis='y', right=True, labelright=False, direction='in', length=4, width=0.8)

    # Y 轴范围和刻度间距
    if y_min is not None:
        ax.set_ylim(bottom=y_min)
    if y_max is not None:
        ax.set_ylim(top=y_max)
    if y_step is not None and y_step > 0:
        import matplotlib.ticker as ticker
        ax.yaxis.set_major_locator(ticker.MultipleLocator(y_step))

    if y_label:
        ax.set_ylabel(y_label, fontsize=font_size, fontweight='bold')
    if title:
        ax.set_title(title, fontsize=font_size + 2, fontweight='bold', pad=15)


def _default_colors(n):
    """生成默认颜色列表"""
    palette = [
        '#4472C4',  # 蓝色
        '#ED7D31',  # 橙色
        '#A5A5A5',  # 灰色
        '#FFC000',  # 金色
        '#5B9BD5',  # 浅蓝
        '#70AD47',  # 绿色
        '#264478',  # 深蓝
        '#9B59B6',  # 紫色
        '#E74C3C',  # 红色
        '#1ABC9C',  # 青绿
        '#F39C12',  # 琥珀
        '#2ECC71',  # 翡翠绿
    ]
    if n <= len(palette):
        return palette[:n]
    cmap = plt.cm.get_cmap('tab20', n)
    return [matplotlib.colors.rgb2hex(cmap(i)) for i in range(n)]


def _fig_to_base64(fig, output_format='png', dpi=300):
    """将 matplotlib figure 转为 base64（透明背景）"""
    buf = io.BytesIO()
    fig.savefig(buf, format=output_format, dpi=dpi, bbox_inches='tight',
                facecolor='none', edgecolor='none', transparent=True)
    plt.close(fig)
    buf.seek(0)
    b64_data = base64.b64encode(buf.getvalue()).decode('utf-8')
    return {
        'data': b64_data,
        'format': output_format
    }


# ═══════════════════════════════════════════════════════════
#  自动显著性字母计算 (LSD 多重比较 + CLD 紧凑字母显示)
# ═══════════════════════════════════════════════════════════

def _auto_compute_letters(work_df, stats, group_cols, value_col, letter_col,
                           alpha=0.05):
    """
    自动计算显著性字母标记

    对每个外层分组组合内，用内层分组做单因素方差分析 + LSD 多重比较，
    生成 CLD 紧凑字母显示。

    Parameters
    ----------
    work_df : pd.DataFrame   原始数据（已清洗）
    stats : pd.DataFrame      stats 表（含 mean/std/count）
    group_cols : list[str]    所有分组列（从外到内）
    value_col : str           数值列名
    letter_col : str          字母列名（将被写入 stats 中）
    alpha : float             显著性水平

    Returns
    -------
    stats with letter_col filled
    """
    from scipy.stats import t as t_dist
    import itertools

    inner_col = group_cols[-1]
    outer_cols = group_cols[:-1]

    # 获取外层分组组合
    if len(outer_cols) == 0:
        # 只有一层分组 → 全局做一次 LSD
        outer_combos = [None]
    elif len(outer_cols) == 1:
        outer_combos = list(pd.unique(work_df[outer_cols[0]].astype(str)))
        outer_combos = [(c,) for c in outer_combos]
    else:
        outer_combos = list(
            work_df[outer_cols].drop_duplicates().itertuples(index=False, name=None)
        )
        outer_combos = [tuple(str(x) for x in c) for c in outer_combos]
        # 去重并保持顺序
        seen = set()
        unique = []
        for c in outer_combos:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        outer_combos = unique

    for combo in outer_combos:
        # 筛选该外层组合的数据
        if combo is None:
            sub_df = work_df
        else:
            mask = pd.Series(True, index=work_df.index)
            for i, col in enumerate(outer_cols):
                mask = mask & (work_df[col].astype(str) == combo[i])
            sub_df = work_df[mask]

        if sub_df.empty:
            continue

        # 按内层分组
        inner_groups = list(pd.unique(sub_df[inner_col].astype(str)))
        if len(inner_groups) < 2:
            # 只有一个组，无法比较
            continue

        # 收集每组数据
        group_data = {}
        for g in inner_groups:
            vals = sub_df[sub_df[inner_col].astype(str) == g][value_col].dropna().values
            if len(vals) > 0:
                group_data[g] = vals

        if len(group_data) < 2:
            continue

        # 计算统计量
        all_vals = np.concatenate(list(group_data.values()))
        grand_mean = np.mean(all_vals)
        n_total = len(all_vals)
        k = len(group_data)

        # 组内平方和
        ss_within = 0
        for g, vals in group_data.items():
            ss_within += np.sum((vals - np.mean(vals)) ** 2)

        df_resid = n_total - k
        if df_resid <= 0:
            continue

        mse = ss_within / df_resid

        # 计算每组统计量
        group_stats = {}
        for g, vals in group_data.items():
            group_stats[g] = {'mean': np.mean(vals), 'count': len(vals)}

        # LSD 两两比较
        pairwise_results = []
        for g1, g2 in itertools.combinations(group_data.keys(), 2):
            m1 = group_stats[g1]['mean']
            m2 = group_stats[g2]['mean']
            n1 = group_stats[g1]['count']
            n2 = group_stats[g2]['count']
            diff = m1 - m2
            se = np.sqrt(mse * (1.0 / n1 + 1.0 / n2))
            t_stat = abs(diff) / se if se > 1e-10 else 0
            p_val = 2 * (1 - t_dist.cdf(t_stat, df_resid))
            reject = p_val < alpha
            pairwise_results.append([g1, g2, diff, p_val, reject])

        # CLD 紧凑字母显示 (Bron-Kerbosch)
        means_series = pd.Series(
            {g: group_stats[g]['mean'] for g in inner_groups if g in group_stats},
        )
        letters = _solve_cld(means_series, pairwise_results)

        # 写入 stats 表
        for g_name, letter in letters.items():
            if combo is None:
                mask_s = stats[inner_col].astype(str) == g_name
            else:
                mask_s = stats[inner_col].astype(str) == g_name
                for i, col in enumerate(outer_cols):
                    mask_s = mask_s & (stats[col].astype(str) == combo[i])
            stats.loc[mask_s, letter_col] = letter

    return stats


def _solve_cld(means, pairwise_data):
    """
    计算 CLD 紧凑字母显示（Bron-Kerbosch 最大团算法）

    与 app.py 中 solve_clique_cld 逻辑一致
    """
    groups = [str(g).strip() for g in means.index.tolist()]
    n = len(groups)
    g_to_i = {g: i for i, g in enumerate(groups)}

    # 相容矩阵（True = 无显著差异）
    adj = np.ones((n, n), dtype=bool)
    if pairwise_data:
        for row in pairwise_data:
            g1, g2, reject = str(row[0]).strip(), str(row[1]).strip(), row[4]
            if reject:
                if g1 in g_to_i and g2 in g_to_i:
                    i, j = g_to_i[g1], g_to_i[g2]
                    adj[i, j] = False
                    adj[j, i] = False
    np.fill_diagonal(adj, False)

    # Bron-Kerbosch 找最大团
    cliques = []
    def bron_kerbosch(R, P, X):
        if len(P) == 0 and len(X) == 0:
            cliques.append(R)
            return
        u = next(iter(P.union(X))) if P.union(X) else None
        nu = {idx for idx in range(n) if adj[u, idx]} if u is not None else set()
        for v in list(P - nu):
            bron_kerbosch(
                R.union({v}),
                P.intersection({i for i in range(n) if adj[v, i]}),
                X.intersection({i for i in range(n) if adj[v, i]})
            )
            P.remove(v)
            X.add(v)

    bron_kerbosch(set(), set(range(n)), set())

    # 按均值降序给团分配字母
    clique_means = sorted(
        [(np.mean([means.iloc[i] for i in clq]), clq) for clq in cliques],
        key=lambda x: x[0],
        reverse=True
    )

    letters_abc = "abcdefghijklmnopqrstuvwxyz"
    group_letters = {i: "" for i in range(n)}
    for idx, (avg, clq) in enumerate(clique_means):
        char = letters_abc[idx] if idx < len(letters_abc) else "?"
        for node_idx in clq:
            group_letters[node_idx] += char

    return {str(means.index[i]).strip(): "".join(sorted(group_letters[i])) for i in range(n)}
