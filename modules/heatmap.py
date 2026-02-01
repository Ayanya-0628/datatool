import matplotlib
matplotlib.use('Agg')  # Must be before importing pyplot

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
import pandas as pd
import numpy as np
from scipy.stats import pearsonr
import io

# ================= Configuration =================
COLOR_LOW = "#2166AC"
COLOR_MID = "#FFFFFF"
COLOR_HIGH = "#B2182B"

# Font settings
plt.rcParams['font.family'] = 'sans-serif'
# 优先使用无衬线字体以支持中文，涵盖 Windows/Linux/Mac 常用中文字体
font_list = ['Microsoft YaHei', 'SimHei', 'WenQuanYi Micro Hei', 'PingFang SC', 'Heiti TC', 'SimSun', 'DejaVu Sans', 'Arial', 'sans-serif']
plt.rcParams['font.sans-serif'] = font_list + plt.rcParams['font.sans-serif']
plt.rcParams['font.serif'] = ['Times New Roman', 'SimSun'] + font_list
plt.rcParams['axes.unicode_minus'] = False

def calculate_correlations(df, x_cols, y_cols):
    """
    Calculate Correlation Matrix (R) and P-value Matrix (P).
    Handles NaNs and non-numeric data robustly.
    """
    r_matrix = np.zeros((len(y_cols), len(x_cols)))
    p_matrix = np.zeros((len(y_cols), len(x_cols)))

    for i, y in enumerate(y_cols):
        for j, x in enumerate(x_cols):
            # Check if columns exist
            if x not in df.columns or y not in df.columns:
                r_matrix[i, j] = np.nan
                p_matrix[i, j] = np.nan
                continue

            # Extract valid data
            try:
                # Ensure data is numeric, coercing errors to NaN
                valid_data = df[[x, y]].apply(pd.to_numeric, errors='coerce').dropna()

                if len(valid_data) > 2:
                    r, p = pearsonr(valid_data[x], valid_data[y])
                    r_matrix[i, j] = r
                    p_matrix[i, j] = p
                else:
                    r_matrix[i, j] = np.nan
                    p_matrix[i, j] = np.nan
            except Exception:
                r_matrix[i, j] = np.nan
                p_matrix[i, j] = np.nan

    return r_matrix, p_matrix

def get_star(p):
    """Return significance stars based on p-value."""
    if pd.isna(p): return ""
    if p < 0.001: return "***"
    if p < 0.01: return "**"
    if p < 0.05: return "*"
    return ""

def draw_heatmap(ax, df, x_cols, y_cols, title=None):
    """
    Draw the correlation bubble heatmap on the provided axes.
    """
    r_mat, p_mat = calculate_correlations(df, x_cols, y_cols)
    rows, cols = r_mat.shape

    # 1. Grid and Aspect Ratio
    ax.set_aspect('equal')
    ax.set_xlim(-0.5, cols - 0.5)
    ax.set_ylim(rows - 0.5, -0.5)

    # 2. Draw Grid Lines
    for x in np.arange(cols + 1) - 0.5:
        ax.axvline(x, color='#E5E5E5', linewidth=1, zorder=0)
    for y in np.arange(rows + 1) - 0.5:
        ax.axhline(y, color='#E5E5E5', linewidth=1, zorder=0)

    # 3. Draw Circles
    cmap = mcolors.LinearSegmentedColormap.from_list("corr_cmap", [COLOR_LOW, COLOR_MID, COLOR_HIGH], N=200)
    norm = mcolors.Normalize(vmin=-1, vmax=1)
    max_radius = 0.35

    for y in range(rows):
        for x in range(cols):
            r_val = r_mat[y, x]
            p_val = p_mat[y, x]

            if np.isnan(r_val):
                continue

            # Draw Circle
            radius = max_radius * np.sqrt(abs(r_val))
            color = cmap(norm(r_val))
            circle = patches.Circle((x, y), radius, facecolor=color, edgecolor=None, zorder=10)
            ax.add_patch(circle)

            # Draw Stars
            star = get_star(p_val)
            if star:
                text_color = 'white' if abs(r_val) > 0.15 else 'black'
                # Adjust fontsize slightly for better readability
                ax.text(x, y + 0.05, star, ha='center', va='center',
                        color=text_color, fontsize=18, fontweight='bold', zorder=20)

    # 4. Axis Labels
    ax.xaxis.tick_top()
    ax.set_xticks(np.arange(cols))
    ax.set_xticklabels(x_cols, fontsize=14, rotation=0, ha='center')

    ax.set_yticks(np.arange(rows))
    ax.set_yticklabels(y_cols, fontsize=14)

    ax.tick_params(axis='both', which='both', length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # 5. Title
    if title:
        ax.set_title(title, fontsize=16, pad=25, fontweight='bold')

    # 6. Colorbar (Inset)
    # Position: [x, y, width, height] relative to ax
    cax = ax.inset_axes([0, -0.25, 1, 0.1], transform=ax.transAxes)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, cax=cax, orientation='horizontal')
    cbar.set_ticks([-1, -0.5, 0, 0.5, 1])
    cbar.ax.tick_params(labelsize=10)
    cbar.outline.set_visible(False)

def generate_heatmap_image(df, x_cols, y_cols, format='png', dpi=300):
    """
    Generate the heatmap image and return as a BytesIO buffer.

    Args:
        df: DataFrame containing the data
        x_cols: List of column names for X axis
        y_cols: List of column names for Y axis
        format: Image format (default: 'png')
        dpi: DPI for saving (default: 300)

    Returns:
        io.BytesIO object containing the image data
    """
    # Estimate figure size
    # Base size + contribution from number of rows/cols
    width = max(6, len(x_cols) * 1.5)
    height = max(5, len(y_cols) * 1.5)

    fig, ax = plt.subplots(figsize=(width, height))

    draw_heatmap(ax, df, x_cols, y_cols)

    plt.tight_layout()
    # Add extra space for colorbar at bottom
    plt.subplots_adjust(bottom=0.2)

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format=format, dpi=dpi, bbox_inches='tight')
    plt.close(fig)

    img_buffer.seek(0)
    return img_buffer
