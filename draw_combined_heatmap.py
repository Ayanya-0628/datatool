import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
from scipy.stats import pearsonr
import os

# ================= 配置区 =================
COLOR_LOW = "#2166AC"
COLOR_MID = "#FFFFFF"
COLOR_HIGH = "#B2182B"

# 字体设置
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False

def calculate_correlations(df, x_cols, y_cols):
    """计算相关系数矩阵(R)和P值矩阵(P)"""
    r_matrix = np.zeros((len(y_cols), len(x_cols)))
    p_matrix = np.zeros((len(y_cols), len(x_cols)))

    for i, y in enumerate(y_cols):
        for j, x in enumerate(x_cols):
            if x in df.columns and y in df.columns:
                valid = df[[x, y]].dropna()
                if len(valid) > 2:
                    r, p = pearsonr(valid[x], valid[y])
                    r_matrix[i, j] = r
                    p_matrix[i, j] = p
                else:
                    r_matrix[i, j] = np.nan
                    p_matrix[i, j] = np.nan
    return r_matrix, p_matrix

def get_star(p):
    if pd.isna(p): return ""
    if p < 0.001: return "***"
    if p < 0.01: return "**"
    if p < 0.05: return "*"
    return ""

def draw_panel(ax, df, x_cols, y_cols, title, show_y_labels=True):
    """在指定的 ax 上绘制单个热图"""
    r_mat, p_mat = calculate_correlations(df, x_cols, y_cols)
    rows, cols = r_mat.shape

    # 1. 设置网格和比例
    ax.set_aspect('equal')
    ax.set_xlim(-0.5, cols - 0.5)
    ax.set_ylim(rows - 0.5, -0.5)

    # 2. 绘制网格线
    for x in np.arange(cols + 1) - 0.5:
        ax.axvline(x, color='#E5E5E5', linewidth=1, zorder=0)
    for y in np.arange(rows + 1) - 0.5:
        ax.axhline(y, color='#E5E5E5', linewidth=1, zorder=0)

    # 3. 绘制圆圈
    cmap = mcolors.LinearSegmentedColormap.from_list("corr_cmap", [COLOR_LOW, COLOR_MID, COLOR_HIGH], N=200)
    norm = mcolors.Normalize(vmin=-1, vmax=1)
    max_radius = 0.35 # 保持之前调整后的大小

    for y in range(rows):
        for x in range(cols):
            r_val = r_mat[y, x]
            p_val = p_mat[y, x]
            if np.isnan(r_val): continue

            # 圆圈
            radius = max_radius * np.sqrt(abs(r_val))
            color = cmap(norm(r_val))
            circle = patches.Circle((x, y), radius, facecolor=color, edgecolor=None, zorder=10)
            ax.add_patch(circle)

            # 显著性星号
            star = get_star(p_val)
            if star:
                text_color = 'white' if abs(r_val) > 0.15 else 'black'
                ax.text(x, y + 0.05, star, ha='center', va='center',
                        color=text_color, fontsize=18, fontweight='bold', zorder=20)

    # 4. 标签设置
    ax.xaxis.tick_top() # X轴在顶部
    ax.set_xticks(np.arange(cols))
    ax.set_xticklabels(x_cols, fontsize=14, rotation=0, ha='center')

    ax.set_yticks(np.arange(rows))
    if show_y_labels:
        ax.set_yticklabels(y_cols, fontsize=14)
    else:
        ax.set_yticklabels([]) # 右边的图可能不需要重复Y轴标签? 还是保留比较好? 这里默认保留

    ax.tick_params(axis='both', which='both', length=0)
    for spine in ax.spines.values(): spine.set_visible(False)

    # 5. 添加标题 (时期)
    ax.set_title(title, fontsize=16, pad=25, fontweight='bold')

    # 6. 添加 Colorbar (使用 inset_axes 确保与 ax 等宽)
    # 位置: [x, y, width, height] 这里的坐标是相对于 ax 的 (transAxes)
    # y=-0.15 放在下方, height=0.08 适当高度
    # 注意: aspect='equal' 会影响 transAxes 的实际形状，但在 box 内部是对齐的
    cax = ax.inset_axes([0, -0.25, 1, 0.1], transform=ax.transAxes)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, cax=cax, orientation='horizontal')
    cbar.set_ticks([-1, -0.5, 0, 0.5, 1])
    cbar.ax.tick_params(labelsize=10)
    cbar.outline.set_visible(False)

def main():
    file_path = "相关分析图.xlsx"
    x_vars = ['GS', 'NR', 'GOGAT']
    y_vars = ['TN', 'NUEg']

    sheet_names = ['Anthesis', '15DAA'] # 指定顺序

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    # 计算画布大小
    # 2个图，每个图宽约3单位，高约2单位。
    # 估算 figsize (英寸)
    fig_width = 8
    fig_height = 4.5

    # 创建画布，1行2列
    fig, axes = plt.subplots(1, 2, figsize=(fig_width, fig_height))

    xl = pd.ExcelFile(file_path)

    # 遍历绘制
    for i, sheet in enumerate(sheet_names):
        if sheet not in xl.sheet_names:
            print(f"Warning: Sheet {sheet} not found.")
            continue

        print(f"Processing sheet: {sheet}")
        df = pd.read_excel(file_path, sheet_name=sheet)

        # 绘制到对应的 ax 上
        # 这里两个图都显示 Y 轴标签，方便阅读
        draw_panel(axes[i], df, x_vars, y_vars, title=sheet, show_y_labels=True)

    # 调整整体布局，防止标签重叠
    plt.tight_layout()

    # 额外增加一点间距，防止左图的colorbar数字和右图打架(虽然tight_layout通常够了)
    plt.subplots_adjust(wspace=0.3)

    output_file = "Combined_Heatmap.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Success! Combined image saved to: {output_file}")

if __name__ == "__main__":
    main()
