import matplotlib
matplotlib.use('Agg')  # Must be before importing pyplot

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
import pandas as pd
import numpy as np
from scipy.stats import pearsonr
from scipy.cluster.hierarchy import dendrogram, linkage, to_tree, fcluster
import io

# ================= Configuration =================
COLOR_LOW = "#2166AC"
COLOR_MID = "#FFFFFF"
COLOR_HIGH = "#B2182B"
CLUSTER_COLORS = ['#E41A1C', '#4DAF4A', '#377EB8', '#984EA3', '#FF7F00', '#A65628', '#F781BF', '#999999']

# Font settings
plt.rcParams['font.family'] = 'sans-serif'
# 优先使用无衬线字体以支持中文，涵盖 Windows/Linux/Mac 常用中文字体
font_list = ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'PingFang SC', 'Heiti TC', 'SimSun', 'DejaVu Sans', 'Arial', 'sans-serif']
plt.rcParams['font.sans-serif'] = font_list + plt.rcParams['font.sans-serif']
plt.rcParams['font.serif'] = ['Times New Roman', 'Noto Serif CJK SC', 'SimSun'] + font_list
plt.rcParams['axes.unicode_minus'] = False


def _save_figure(fig, format='png', dpi=300):
    buffer = io.BytesIO()
    fig.savefig(buffer, format=format, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _normalize_frame(frame):
    display = frame.copy()
    for col in display.columns:
        series = pd.to_numeric(display[col], errors='coerce')
        min_val = series.min()
        max_val = series.max()
        if pd.isna(min_val) or pd.isna(max_val) or max_val == min_val:
            display[col] = 0.5
        else:
            display[col] = (series - min_val) / (max_val - min_val)
    return display.fillna(0.5)


def _build_sample_labels(df, label_cols):
    if label_cols:
        valid_label_cols = [col for col in label_cols if col in df.columns]
    else:
        valid_label_cols = []

    if valid_label_cols:
        if len(valid_label_cols) == 1:
            labels = df[valid_label_cols[0]].astype(str).fillna('').tolist()
        else:
            labels = df[valid_label_cols].astype(str).fillna('').agg(' | '.join, axis=1).tolist()
    else:
        labels = [str(idx) for idx in df.index.tolist()]

    counts = {}
    unique_labels = []
    for label in labels:
        base_label = str(label).strip() or 'Sample'
        counts[base_label] = counts.get(base_label, 0) + 1
        if counts[base_label] == 1:
            unique_labels.append(base_label)
        else:
            unique_labels.append(f'{base_label}_{counts[base_label]}')
    return unique_labels

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
    width = max(6, len(x_cols) * 1.5)
    height = max(5, len(y_cols) * 1.5)

    fig, ax = plt.subplots(figsize=(width, height))

    draw_heatmap(ax, df, x_cols, y_cols)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.2)

    return _save_figure(fig, format=format, dpi=dpi)


def generate_circular_cluster_heatmap_image(df, feature_cols, label_cols=None, n_clusters=3, format='png', dpi=180):
    """
    Generate a circular clustered heatmap image similar to the project's R script.

    Args:
        df: Source DataFrame
        feature_cols: Numeric columns used for clustering and outer heatmap rings
        label_cols: Optional columns used to build outer sample labels
        n_clusters: Number of clusters highlighted on the ring
        format: png/pdf/svg
        dpi: export dpi
    """
    valid_feature_cols = [col for col in feature_cols if col in df.columns]
    if len(valid_feature_cols) < 2:
        raise ValueError('At least 2 numeric feature columns are required')

    work_df = df.copy()
    data_matrix = work_df[valid_feature_cols].apply(pd.to_numeric, errors='coerce')
    data_matrix = data_matrix.dropna(how='all')
    if len(data_matrix) < 3:
        raise ValueError('At least 3 valid samples are required')

    for col in valid_feature_cols:
        data_matrix[col] = data_matrix[col].fillna(data_matrix[col].mean())

    aligned_df = work_df.loc[data_matrix.index].copy()
    sample_labels = _build_sample_labels(aligned_df, label_cols or [])
    display_frame = _normalize_frame(data_matrix)

    linkage_matrix = linkage(data_matrix.values, method='ward')
    sample_order = dendrogram(linkage_matrix, no_plot=True)['leaves']
    ordered_labels = [sample_labels[idx] for idx in sample_order]
    ordered_values = display_frame.iloc[sample_order]

    cluster_count = max(2, min(int(n_clusters or 3), len(data_matrix) - 1))
    cluster_assignments = fcluster(linkage_matrix, t=cluster_count, criterion='maxclust')
    ordered_clusters = cluster_assignments[sample_order]

    n_samples = len(sample_order)
    n_features = len(valid_feature_cols)

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

    tree = to_tree(linkage_matrix, rd=False)
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
        idx + 1: CLUSTER_COLORS[idx % len(CLUSTER_COLORS)]
        for idx in range(cluster_count)
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
            node_angle_cache[node.id] = (left_angle * left_count + right_angle * right_count) / (left_count + right_count)
        return node_angle_cache[node.id]

    def get_node_radius(node):
        if node.is_leaf():
            return tree_outer_radius
        return tree_outer_radius - (float(node.dist) / max_dist) * (tree_outer_radius - tree_inner_radius)

    def get_node_groups(node):
        if node.id in node_groups_cache:
            return node_groups_cache[node.id]
        if node.is_leaf():
            node_groups_cache[node.id] = {int(cluster_assignments[node.id])}
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

    cmap = mcolors.LinearSegmentedColormap.from_list('circular_cluster_heatmap', [COLOR_LOW, COLOR_MID, COLOR_HIGH])
    norm = mcolors.TwoSlopeNorm(vmin=0.0, vcenter=0.5, vmax=1.0)

    for feature_idx, feature_name in enumerate(valid_feature_cols):
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
            f'Samples: {n_samples}. Outer labels hidden for readability.',
            ha='left',
            va='center',
            fontsize=10,
            color='#475569',
        )

    legend_handles = [
        Patch(facecolor=cluster_color_map[idx + 1], edgecolor='none', label=f'Cluster {idx + 1}')
        for idx in range(cluster_count)
    ]
    if legend_handles:
        fig.legend(handles=legend_handles, loc='upper right', bbox_to_anchor=(0.98, 0.98), frameon=False, title='Clusters')

    cax = fig.add_axes([0.84, 0.14, 0.02, 0.22])
    colorbar = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax)
    colorbar.set_label('Relative level', fontsize=10)
    colorbar.ax.tick_params(labelsize=9)

    ax.set_ylim(0, label_radius + 0.14)
    fig.suptitle('Circular Cluster Heatmap', fontsize=16, fontweight='bold', y=0.98)
    return _save_figure(fig, format=format, dpi=dpi)
