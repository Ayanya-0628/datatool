"""
数据分析 Web 应用 - Flask 后端
功能：多因子方差分析、LSD多重比较、组内分析、主效应分析、相关性分析
支持在线部署与分享
修改重点：
1. 强制所有 GroupBy 不排序 (sort=False) 以保持文件原始顺序
2. 强制结果表因子列在最左侧
"""

# Flask Application - Data Analysis Tool
# Last Updated: 2026-01-21 (Sidebar Layout)
import os
import uuid
import time
import datetime
import threading
import traceback
import sys

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.formula.api import ols
from scipy.stats import t, pearsonr
import itertools
import base64
from io import BytesIO

# PCA 分析
try:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# 导入增强版 PCA 分析模块
try:
    from pca_analysis import PCAAnalyzer, run_pca_analysis_enhanced
    HAS_PCA_MODULE = True
except ImportError:
    HAS_PCA_MODULE = False

# 导入聚类分析模块
try:
    from clustering import ClusterAnalyzer
    HAS_CLUSTER_MODULE = True
except ImportError:
    HAS_CLUSTER_MODULE = False

# 导入 Heatmap 模块
try:
    from modules.heatmap import generate_heatmap_image
    HAS_HEATMAP_MODULE = True
except ImportError:
    HAS_HEATMAP_MODULE = False

# 导入柱状图模块
try:
    from modules.barchart import generate_bar_chart
    HAS_BARCHART_MODULE = True
except ImportError:
    HAS_BARCHART_MODULE = False

# 导入 Nature 风格 Python 绘图模块
try:
    from modules.nature_plot import generate_nature_plot
    HAS_NATURE_PLOT_MODULE = True
except ImportError:
    HAS_NATURE_PLOT_MODULE = False

# 导入智能数据整理模块
try:
    from smart_tidy import scan_excel_structure, execute_smart_tidy
    HAS_SMART_TIDY = True
except ImportError:
    HAS_SMART_TIDY = False

# 导入 LLM 数据整理模块（AI 万能整理）
try:
    from llm_tidy import analyze_and_transform
    HAS_LLM_TIDY = True
except ImportError:
    HAS_LLM_TIDY = False

# tkinter 仅用于本地运行时的目录选择对话框，云端部署时不可用
try:
    import tkinter as tk
    from tkinter import filedialog
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

from flask import Flask, request, jsonify, send_file, render_template, after_this_request
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
# 关键修复：PyInstaller 单文件打包资源路径适配
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

# 禁止 jsonify 自动排序键 (关键修复: 保持 DataFrame 列顺序)
app.config['JSON_SORT_KEYS'] = False
try:
    app.json.sort_keys = False
except AttributeError:
    pass  # Flask 旧版本兼容


@app.after_request
def add_cache_headers(response):
    """避免前端更新后浏览器继续使用旧的 app.js。"""
    if request.path == '/' or request.path.endswith('/app.js'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


# 全局错误处理器 - 确保所有错误返回 JSON 而不是 HTML
@app.errorhandler(Exception)
def handle_exception(e):
    """捕获所有未处理的异常，返回 JSON 格式错误"""
    import traceback
    error_log_path = os.path.join(APP_DATA_DIR, 'error.log')
    with open(error_log_path, 'a', encoding='utf-8') as f:
        f.write(f'\n=== {datetime.datetime.now()} ===\n')
        f.write(f'Error: {str(e)}\n')
        f.write(traceback.format_exc())
    return jsonify({'error': f'服务器内部错误: {str(e)}'}), 500

@app.errorhandler(500)
def handle_500(e):
    """处理 500 错误"""
    return jsonify({'error': f'服务器内部错误: {str(e)}'}), 500

# 防止浏览器缓存
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# 配置
UPLOAD_FOLDER = 'uploads'
# ==========================================
# 应用配置
# ==========================================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

def get_app_data_dir():
    """获取应用数据存储目录 (解决安装后无权限问题)"""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        # Windows: %LOCALAPPDATA%/DataAnalysisTool
        base_dir = os.path.join(home, "AppData", "Local", "DataAnalysisTool")
    else:
        # Linux/Mac: ~/.data_analysis_tool
        base_dir = os.path.join(home, ".data_analysis_tool")

    if not os.path.exists(base_dir):
        try:
            os.makedirs(base_dir)
        except:
            pass
    return base_dir

APP_DATA_DIR = get_app_data_dir()

# 存储上传的数据 (带时间戳用于清理)
data_store = {}
data_timestamps = {}
DATA_EXPIRE_SECONDS = 3600  # 数据1小时后过期

# 暂存未确认的文件 (用于多Sheet选择)
temp_file_store = {}

# 存储原始 Excel 文件字节（智能整理需要 openpyxl 读取合并单元格）
raw_file_store = {}  # {data_id: {'content': bytes, 'filename': str, 'sheet_name': str|None}}

# 导出文件存放目录（可用环境变量 SLYLAB_EXPORT_DIR 指向对象存储挂载点，如 COS /mnt/cos/...）
EXPORT_DIR = os.environ.get('SLYLAB_EXPORT_DIR') or os.path.join(APP_DATA_DIR, 'exports')
if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR, exist_ok=True)

# 可选：启用「注册后使用」（方式三云端部署时设置 ENABLE_AUTH=1）
if os.environ.get('ENABLE_AUTH', '').lower() in ('1', 'true', 'yes'):
    from auth import init_auth
    init_auth(app, APP_DATA_DIR)


def sanitize_dataframe(df):
    """清理 DataFrame 数据以便导出"""
    if df is None: return None
    df = df.copy()
    
    # 检测是否已经是 MultiIndex
    is_multi = isinstance(df.columns, pd.MultiIndex)
    
    # 辅助函数：处理单个单元格内容
    def clean_val(val):
        if pd.isna(val) or val is None:
            return ""
        if isinstance(val, (int, float)):
            if np.isinf(val):
                return "inf"
            return val
        if isinstance(val, (str, bool, datetime.datetime, datetime.date)):
            return val
        return str(val)

    # 处理数据内容
    for col in df.columns:
        df[col] = df[col].apply(clean_val)
            
    # 如果不是 MultiIndex，则统一将列名转为字符串
    if not is_multi:
        df.columns = [str(c) for c in df.columns]
            
    return df


def cleanup_expired_data():
    """清理过期数据"""
    while True:
        time.sleep(300)  # 每5分钟检查一次
        current_time = time.time()
        expired_keys = [
            key for key, ts in list(data_timestamps.items())
            if current_time - ts > DATA_EXPIRE_SECONDS
        ]
        for key in expired_keys:
            data_store.pop(key, None)
            data_timestamps.pop(key, None)
        
        # 清理暂存文件
        expired_temp = [
            key for key, val in list(temp_file_store.items())
            if current_time - val['timestamp'] > 600  # 暂存文件10分钟过期
        ]
        for key in expired_temp:
            temp_file_store.pop(key, None)
            
        if expired_keys or expired_temp:
            print(f"Cleaned up {len(expired_keys)} data, {len(expired_temp)} temp files")


# 启动清理线程
cleanup_thread = threading.Thread(target=cleanup_expired_data, daemon=True)
cleanup_thread.start()


# ==========================================
# 核心统计逻辑
# ==========================================

def get_stars(p_value):
    """根据p值返回显著性标记"""
    if p_value < 0.001: return '***'
    if p_value < 0.01:  return '**'
    if p_value < 0.05:  return '*'
    return 'ns'


def pairwise_lsd_test_with_mse(stats_df, mse, df_resid, alpha=0.05):
    """LSD多重比较"""
    results = []
    group_names = stats_df.index.tolist()
    for g1, g2 in itertools.combinations(group_names, 2):
        m1, n1 = stats_df.loc[g1, 'mean'], stats_df.loc[g1, 'count']
        m2, n2 = stats_df.loc[g2, 'mean'], stats_df.loc[g2, 'count']
        diff = m1 - m2
        se = np.sqrt(mse * (1/n1 + 1/n2))
        t_stat = abs(diff) / se if se > 1e-10 else 0
        p_val = 2 * (1 - t.cdf(t_stat, df_resid))
        results.append([g1, g2, diff, p_val, p_val < alpha])
    return results


def solve_clique_cld(means, pairwise_data):
    """计算紧凑字母显示（CLD）"""
    groups = [str(g).strip() for g in means.index.tolist()]
    n = len(groups)
    g_to_i = {g: i for i, g in enumerate(groups)}
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
    
    clique_means = sorted(
        [(np.mean([means.iloc[i] for i in clq]), clq) for clq in cliques], 
        key=lambda x: x[0], 
        reverse=True
    )
    
    letters = "abcdefghijklmnopqrstuvwxyz"
    group_letters = {i: "" for i in range(n)}
    for idx, (avg, clq) in enumerate(clique_means):
        char = letters[idx] if idx < len(letters) else "?"
        for node_idx in clq:
            group_letters[node_idx] += char
    
    return {str(means.index[i]).strip(): "".join(sorted(group_letters[i])) for i in range(n)}


def solve_clique_cld_upper(means, pairwise_data):
    """返回大写字母的CLD"""
    res = solve_clique_cld(means, pairwise_data)
    return {k: v.upper() for k, v in res.items()}


def calculate_single_trait(sub_df, factors, t_col, test_factor):
    """计算单个性状的统计分析"""
    res = {
        'anova_rows': [], 
        'main_rows': [], 
        'sliced_sep_rows': [], 
        'sliced_comb_rows': []
    }
    
    try:
        # ANOVA 公式（包含交互作用）
        formula = f"Q('{t_col}') ~ " + " * ".join([f"Q('{f}')" for f in factors])
        model = ols(formula, data=sub_df).fit()
        mse, df_resid = model.mse_resid, model.df_resid
        
        # ANOVA 表
        aov = sm.stats.anova_lm(model, typ=2)
        for src, row in aov.iterrows():
            if src != 'Residual':
                idx_name = src.replace("Q('", "").replace("')", "")
                res['anova_rows'].append({
                    'Source': idx_name, 
                    '指标': t_col, 
                    'Value': f"{row['F']:.2f}{get_stars(row['PR(>F)'])}"
                })
        
        # 主效应分析
        for f in factors:
            # 修改点：sort=False 保持出现顺序
            stats = sub_df.groupby(f, observed=True, sort=False)[t_col].agg(['mean', 'std', 'count'])
            if len(stats) > 1:
                try:
                    sub_model = ols(f"Q('{t_col}') ~ C(Q('{f}'))", data=sub_df).fit()
                    curr_mse, curr_df = sub_model.mse_resid, sub_model.df_resid
                except:
                    curr_mse, curr_df = mse, df_resid
                letters = solve_clique_cld_upper(stats['mean'], pairwise_lsd_test_with_mse(stats, curr_mse, curr_df))
            else:
                letters = {str(k).strip(): 'A' for k in stats.index}
            
            for lvl, row in stats.iterrows():
                lvl_str = str(lvl).strip()
                base_info = {
                    'Factor': f,
                    'Level': lvl_str,
                    '指标': t_col
                }
                res['main_rows'].append({**base_info, 'Type': 'Mean', 'Value': row['mean']})
                res['main_rows'].append({**base_info, 'Type': 'Letter', 'Value': letters.get(lvl_str, '')})
                res['main_rows'].append({**base_info, 'Type': 'SD', 'Value': row['std']})
                res['main_rows'].append({**base_info, 'Type': 'Combined', 'Value': f"{row['mean']:.2f} {letters.get(lvl_str, '')}"})
        
        # 组内分析（切片）
        grp_factors = [x for x in factors if x != test_factor]
        if not grp_factors:
            groups = [("All", sub_df)]
        else:
            # 修改点：sort=False 保持出现顺序
            groups = sub_df.groupby(grp_factors, observed=True, sort=False)
        
        for keys, gdf in groups:
            info = {}
            if grp_factors:
                keys = (keys,) if not isinstance(keys, tuple) else keys
                for k, v in zip(grp_factors, keys):
                    info[k] = str(v).strip()
            
            # 修改点：sort=False 保持出现顺序
            stats = gdf.groupby(test_factor, observed=True, sort=False)[t_col].agg(['mean', 'std', 'count'])
            if len(stats) > 1:
                try:
                    sub_model = ols(f"Q('{t_col}') ~ C(Q('{test_factor}'))", data=gdf).fit()
                    curr_mse, curr_df = sub_model.mse_resid, sub_model.df_resid
                except:
                    curr_mse, curr_df = mse, df_resid
                letters = solve_clique_cld(stats['mean'], pairwise_lsd_test_with_mse(stats, curr_mse, curr_df))
            else:
                letters = {str(k).strip(): 'a' for k in stats.index}
            
            for lvl, row in stats.iterrows():
                lvl_str = str(lvl).strip()
                base_info = info.copy()
                base_info[test_factor] = lvl_str
                base_info['指标'] = t_col
                
                # 分列格式项
                res['sliced_sep_rows'].append({**base_info, 'Type': 'Mean', 'Value': row['mean']})
                res['sliced_sep_rows'].append({**base_info, 'Type': 'Letter', 'Value': letters.get(lvl_str, '')})
                res['sliced_sep_rows'].append({**base_info, 'Type': 'SD', 'Value': row['std']})
                
                # 组合格式项
                res['sliced_comb_rows'].append({
                    **base_info, 
                    'Mean_Letter': f"{row['mean']:.2f} {letters.get(lvl_str, '')}"
                })
    
    except Exception as e:
        err_msg = f"Error in {t_col}: {e}\n{traceback.format_exc()}"
        print(err_msg)
        error_file = os.path.join(APP_DATA_DIR, "last_error.txt")
        with open(error_file, "w", encoding="utf-8") as f:
            f.write(err_msg)
    
    return res



def run_analysis(df, factors, targets):
    """
    运行完整分析 (Clean Re-implementation)
    1. Row Order: Strictly follows appearance order in input file via pd.unique + Categorical.
    2. Column Order: Strictly follows User Selection (factors) and Hardcoded Metrics (Mean, Letter, SD).
    """
    
    # --- 1. Global Pre-processing: Capture File Order ---
    file_orders = {}
    work_df = df.copy()
    
    for f in factors:
        clean_col = work_df[f].astype(str).str.strip()
        # Capture appearance order
        original_order = pd.unique(clean_col)
        # Store for future use (must convert to list)
        file_orders[f] = list(original_order)
        # Apply strict ordering immediately
        work_df[f] = pd.Categorical(clean_col, categories=original_order, ordered=True)

    test_factor = factors[-1]
    
    # --- 2. Prepare Tasks ---
    tasks = []
    valid_targets = []
    
    for t_col in targets:
        # Validate numeric
        numeric_series = pd.to_numeric(work_df[t_col], errors='coerce')
        valid_count = numeric_series.notna().sum()
        
        if valid_count == 0:
            print(f"[WARNING] Skipping target '{t_col}': No valid numeric values found. (Head: {work_df[t_col].head().tolist()})")
            continue
            
        work_df[t_col] = numeric_series
        # Create sub-dataframe excluding NaNs for this specific target
        # Note: Factor columns in sub_df retain Categorical dtype from work_df
        sub_df = work_df.dropna(subset=[t_col] + factors)[[t_col] + factors].copy()
        
        if sub_df.empty:
             print(f"[WARNING] Skipping target '{t_col}': Sub-DataFrame is empty after dropping NaNs (Factors: {factors}).")
             continue

        valid_targets.append(t_col)
        tasks.append((sub_df, factors, t_col, test_factor))

    # 关键：捕获原始 DataFrame 中的列顺序，确保结果表中的指标顺序与输入文件一致
    target_order_map = {t: i for i, t in enumerate(df.columns) if t in targets}
    valid_targets = sorted(valid_targets, key=lambda x: target_order_map.get(x, 999))

    # --- 3. Execute Calculation ---
    # We collect raw rows first, then pivot/format systematically
    raw_results = {
        'anova_rows': [], 
        'main_rows': [], 
        'sliced_sep_rows': [], 
        'sliced_comb_rows': []
    }
    
    for task in tasks:
        # calculate_single_trait returns a dict with same keys as raw_results
        res = calculate_single_trait(*task)
        for key in raw_results:
            raw_results[key].extend(res[key])
            
    results = {}
    
    # --- 4. Result Assembly & Strict Formatting ---
    
    # Helper: Enforce Column Order
    def enforce_columns(df, factor_cols, target_cols, metric_types=['Mean', 'Letter', 'SD']):
        """
        Force DataFrame columns to be:
        [Factor1, Factor2...] + [Target1|Mean, Target1|Letter, Target1|SD, Target2|Mean...]
        """
        current_cols = set(df.columns)
        final_cols = []
        
        # 1. Factors (User Selection Order)
        for f in factor_cols:
            if f in current_cols:
                final_cols.append(f)
        
        # 2. Metrics (Target Order + Fixed Metric Order)
        for t in target_cols:
            for m in metric_types:
                col_name = f"{t} | {m}"
                if col_name in current_cols:
                    final_cols.append(col_name)
                    
        # 3. Any remaining columns (safety net)
        for c in df.columns:
            if c not in final_cols:
                final_cols.append(c)
                
        return df[final_cols]
        
    # Helper: Enforce Row Order
    def enforce_row_order(df, factor_cols):
        """
        Sort DataFrame rows based on the pre-captured file_orders.
        Assumes columns in df are already objects/strings, so we re-apply Categorical.
        """
        df = df.copy()
        sort_by = []
        for f in factor_cols:
            if f in df.columns and f in file_orders:
                df[f] = pd.Categorical(df[f], categories=file_orders[f], ordered=True)
                sort_by.append(f)
        
        if sort_by:
            df = df.sort_values(by=sort_by)
        return df

    # (A) ANOVA
    if raw_results['anova_rows']:
        df_anova = pd.DataFrame(raw_results['anova_rows'])
        df_pivot = df_anova.pivot(index='Source', columns='指标', values='Value').reset_index()

        # 按照原始文件顺序重新排序列 (指标)
        anova_cols = ['Source'] + [t for t in valid_targets if t in df_pivot.columns]
        df_pivot = df_pivot.reindex(columns=anova_cols)

        # 自定义排序逻辑：单因子 -> 交互项 -> 残差
        def get_source_rank(source):
            if source == 'Residual':
                return 1000
            if ":" in source:
                return 500
            if source in factors:
                return factors.index(source)
            return 900

        df_pivot['Rank'] = df_pivot['Source'].map(get_source_rank)
        results['anova'] = df_pivot.sort_values('Rank').drop(columns=['Rank'])

    # (B) Main Effects (Main Table)
    if raw_results['main_rows']:
        df_raw = pd.DataFrame(raw_results['main_rows'])

        # Filter for Combined (Mean + Letter)
        df_comb = df_raw[df_raw['Type'] == 'Combined'].copy()

        # Pivot: Index=[Factor, Level], Columns=[指标]
        df_pivot = df_comb.pivot_table(
            index=['Factor', 'Level'],
            columns='指标',
            values='Value',
            aggfunc='first'
        ).reset_index()

        # Re-sort Rows
        sort_map = {}
        idx = 0
        for f in factors:
            if f in file_orders:
                for val in file_orders[f]:
                    sort_map[(f, val)] = idx
                    idx += 1

        df_pivot['SortKey'] = df_pivot.apply(lambda r: sort_map.get((r['Factor'], r['Level']), 99999), axis=1)
        df_pivot = df_pivot.sort_values('SortKey').drop(columns=['SortKey'])

        # Re-sort Columns (Factor, Level, + Targets in order)
        base_cols = ['Factor', 'Level']
        target_cols = [t for t in valid_targets if t in df_pivot.columns]

        results['main'] = df_pivot[base_cols + target_cols]

    # (C) Sliced Separation (The Core Issue)
    if raw_results['sliced_sep_rows']:
        df_sep = pd.DataFrame(raw_results['sliced_sep_rows'])
        
        # Pivot
        # Index = All Factors
        # Columns = Trait, Type
        df_pivot = df_sep.pivot_table(
            index=factors,
            columns=['指标', 'Type'],
            values='Value',
            aggfunc='first'
        )
        
        # Flatten columns
        df_pivot.columns = [f"{t} | {m}" for t, m in df_pivot.columns]
        df_pivot = df_pivot.reset_index()
        
        # 1. Enforce Row Order (using file_orders)
        df_pivot = enforce_row_order(df_pivot, factors)
        
        # 2. Enforce Column Order (Factors first, then Mean-Letter-SD)
        df_pivot = enforce_columns(df_pivot, factors, valid_targets)
        
        results['sliced_sep'] = df_pivot

    # (D) Sliced Combined
    if raw_results['sliced_comb_rows']:
        df_comb = pd.DataFrame(raw_results['sliced_comb_rows'])
        df_pivot = df_comb.pivot_table(index=factors, columns='指标', values='Mean_Letter', aggfunc='first').reset_index()
        df_pivot = enforce_row_order(df_pivot, factors)
        # Columns here are simple: Factors + Targets. Just put factors first.
        cols = list(df_pivot.columns)
        facs = [c for c in cols if c in factors]
        others = [c for c in cols if c not in factors]
        # 按照原始文件中的指标出现顺序对指标列进行排序
        others_sorted = sorted(others, key=lambda x: target_order_map.get(x, 999))
        # Sort factors by user user selection
        facs_sorted = [f for f in factors if f in facs]
        results['sliced_comb'] = df_pivot[facs_sorted + others_sorted]

    # (E) Correlation
    if len(valid_targets) > 1:
        corr_df = work_df[valid_targets].corr()
        pval_df = work_df[valid_targets].corr(method=lambda x, y: pearsonr(x, y)[1])
        final_corr = corr_df.copy().astype(object)
        for c in final_corr.columns:
            for r in final_corr.index:
                if c == r:
                    final_corr.loc[r, c] = "-"
                else:
                    v = corr_df.loc[r, c]
                    p = pval_df.loc[r, c]
                    final_corr.loc[r, c] = f"{v:.2f}{get_stars(p)}"
        results['corr'] = final_corr.reset_index()
        
    # debug print
    import sys
    sys.stderr.write(f"--- DEBUG: run_analysis finished ---\n")
    for k, v in results.items():
        if isinstance(v, pd.DataFrame):
            sys.stderr.write(f"[run_analysis] {k}: {v.shape}\n")
        else:
            sys.stderr.write(f"[run_analysis] {k}: {len(v) if hasattr(v, '__len__') else 'N/A'}\n")
            
    return results, valid_targets

# ==========================================
# Flask 路由定义
# ==========================================

def analyze_column_types(df):
    """
    分析 DataFrame 列类型，区分因子列和指标列
    
    Returns:
        dict: {
            'column_types': {col: 'numeric'|'categorical'},
            'suggested_factors': [...],
            'suggested_indicators': [...]
        }
    """
    column_types = {}
    suggested_factors = []
    suggested_indicators = []
    
    for col in df.columns:
        # 尝试转换为数值
        numeric_series = pd.to_numeric(df[col], errors='coerce')
        non_null_count = numeric_series.notna().sum()
        total_count = len(df)
        
        # 如果 80% 以上可成功转换为数值，认为是数值列
        if total_count > 0 and (non_null_count / total_count) > 0.8:
            column_types[col] = 'numeric'
            suggested_indicators.append(col)
        else:
            column_types[col] = 'categorical'
            suggested_factors.append(col)
    
    return {
        'column_types': column_types,
        'suggested_factors': suggested_factors,
        'suggested_indicators': suggested_indicators
    }

@app.route('/')
def index():
    auth_enabled = os.environ.get('ENABLE_AUTH', '').lower() in ('1', 'true', 'yes')
    return render_template('dashboard.html', auth_enabled=auth_enabled)


@app.route('/api/upload', methods=['POST'])
def upload():
    """处理文件上传"""
    if 'file' not in request.files:
        return jsonify({'error': '未找到文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    try:
        filename = file.filename
        print(f"DEBUG: Receiving file {filename}")
        
        # 读取文件
        if filename.endswith('.csv'):
            file_content = file.read()
            try:
                df = pd.read_csv(BytesIO(file_content), encoding='utf-8')
            except:
                try:
                    df = pd.read_csv(BytesIO(file_content), encoding='gbk')
                except:
                    df = pd.read_csv(BytesIO(file_content))
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            # 记录上传内容的字节流
            file.seek(0)
            file_content = file.read()
            
            # 根据后缀名指定引擎
            engine = 'openpyxl' if filename.endswith('.xlsx') else 'xlrd'
            
            # 检查是否有多个 sheet
            xl = pd.ExcelFile(BytesIO(file_content), engine=engine)
            if len(xl.sheet_names) > 1:
                # 存入临时存储，等待用户选择 Sheet
                temp_id = str(uuid.uuid4())
                temp_file_store[temp_id] = {
                    'content': file_content,
                    'sheets': xl.sheet_names,
                    'filename': filename,
                    'timestamp': time.time()
                }
                
                return jsonify({
                    'status': 'select_sheet',
                    'need_sheet_selection': True,
                    'sheets': xl.sheet_names,
                    'temp_id': temp_id,
                    'filename': filename
                })
            else:
                # 只有一个 sheet
                df = pd.read_excel(BytesIO(file_content), engine=engine)
        else:
            return jsonify({'error': '不支持的文件格式'}), 400
        
        # 保存数据
        data_id = str(uuid.uuid4())
        data_store[data_id] = df
        data_timestamps[data_id] = time.time()
        
        # 保存原始 Excel 字节（智能整理需要）
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            raw_file_store[data_id] = {
                'content': file_content,
                'filename': filename,
                'sheet_name': None
            }
        
        # 分析列类型
        type_analysis = analyze_column_types(df)
        
        is_excel = filename.endswith('.xlsx') or filename.endswith('.xls')
        response_data = {
            'data_id': data_id,
            'columns': list(df.columns),
            'rows': len(df),
            'is_excel': is_excel
        }
        response_data.update(type_analysis)
        
        return jsonify(response_data)
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'文件解析失败: {str(e)}'}), 500


@app.route('/api/load_sheet', methods=['POST'])
def load_sheet():
    """加载指定的 Sheet"""
    data = request.json
    temp_id = data.get('temp_id')
    sheet_name = data.get('sheet_name')
    
    if not temp_id or not sheet_name:
        return jsonify({'error': '缺少必要参数'}), 400
    
    if temp_id not in temp_file_store:
        return jsonify({'error': '文件已过期，请重新上传'}), 400
    
    try:
        file_data = temp_file_store.pop(temp_id)
        content = BytesIO(file_data['content'])
        
        df = pd.read_excel(content, sheet_name=sheet_name)
        
        # 保存数据
        data_id = str(uuid.uuid4())
        data_store[data_id] = df
        data_timestamps[data_id] = time.time()
        
        # 保存原始 Excel 字节（智能整理需要）
        raw_file_store[data_id] = {
            'content': file_data['content'],
            'filename': file_data['filename'],
            'sheet_name': sheet_name
        }
        
        # 分析列类型
        type_analysis = analyze_column_types(df)
        
        response_data = {
            'data_id': data_id,
            'columns': list(df.columns),
            'rows': len(df),
            'is_excel': True
        }
        response_data.update(type_analysis)
        
        return jsonify(response_data)
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'加载失败: {str(e)}'}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """执行分析"""
    # 最外层异常捕获，确保所有错误都被记录
    log_path = os.path.join(APP_DATA_DIR, 'debug_analyze.log')
    try:
        data = request.json
        data_id = data.get('data_id')
        factors = data.get('factors', [])
        targets = data.get('targets', [])

        # 调试日志 - 写入文件 (使用绝对路径)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f'=== /api/analyze 请求 ===\n')
            f.write(f'data_id: {data_id}\n')
            f.write(f'factors: {factors}\n')
            f.write(f'targets: {targets}\n')
            f.write(f'data_store keys: {list(data_store.keys())}\n')

        if not data_id or data_id not in data_store:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f'ERROR: data_id 不在 data_store 中!\n')
            return jsonify({'error': '数据已过期，请重新上传文件'}), 400

        if not factors or not targets:
            return jsonify({'error': '请选择因子和性状'}), 400

        df = data_store[data_id]
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f'DataFrame shape: {df.shape}\n')
            f.write(f'DataFrame columns: {list(df.columns)}\n')
            f.write(f'检查 targets:\n')
            for t in targets:
                exists = t in df.columns
                f.write(f'  {t}: {"OK" if exists else "NOT FOUND"}\n')

        # 运行分析
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write('开始执行 run_analysis...\n')

        results, valid_targets = run_analysis(df, factors, targets)

        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f'run_analysis 完成! valid_targets={valid_targets}\n')
            f.write(f'results keys: {list(results.keys())}\n')

        # 转换 DataFrame 为 JSON 格式 (records)
        response = {
            'factors': factors,
            'targets': valid_targets
        }

        for key, val in results.items():
            if isinstance(val, pd.DataFrame):
                # 关键修复：使用 orient='records' 保持列顺序
                response[key] = val.to_dict(orient='records')
            else:
                response[key] = val

        with open(log_path, 'a', encoding='utf-8') as f:
            f.write('JSON 序列化完成, 准备返回响应\n')

        try:
            json_response = jsonify(response)
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write('jsonify 成功!\n')
            return json_response
        except Exception as json_err:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f'jsonify 失败: {json_err}\n')
                f.write(traceback.format_exc())
            return jsonify({'error': f'JSON序列化失败: {str(json_err)}'}), 500

    except Exception as e:
        error_msg = f'分析失败: {str(e)}'
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f'\n=== ERROR ===\n{error_msg}\n')
            f.write(traceback.format_exc())
            f.write('=== END ERROR ===\n')
        return jsonify({'error': error_msg}), 500


@app.route('/api/analyze_pca', methods=['POST'])
def analyze_pca():
    """执行主成分分析 (PCA) - 增强版"""
    if not HAS_SKLEARN:
        return jsonify({'error': 'PCA 功能需要 scikit-learn 库，请安装: pip install scikit-learn'}), 500
    
    data = request.json
    data_id = data.get('data_id')
    targets = data.get('targets', [])
    group_by = data.get('group_by', [])  # 分组变量
    target_configs = data.get('target_configs', {})  # 正向化配置
    include_plots = data.get('include_plots', True)  # 是否包含图表
    include_scores = data.get('include_scores', True)  # 是否包含得分
    
    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400
    
    if len(targets) < 2:
        return jsonify({'error': '主成分分析至少需要2个数值变量'}), 400
    
    try:
        df = data_store[data_id].copy()
        
        # 聚类子集过滤
        cluster_filter = data.get('cluster_filter', None)
        
        if cluster_filter and cluster_filter != 'all' and data_id in cluster_store:
            cluster_info = cluster_store[data_id]
            cluster_labels = cluster_info['labels']
            target_cluster = int(cluster_filter)
            
            # 确保标签数量与数据行数匹配
            if len(cluster_labels) == len(df):
                # 获取属于目标聚类的行索引
                indices = [i for i, l in enumerate(cluster_labels) if l == target_cluster]
                
                if len(indices) > 0:
                    # 使用 iloc 筛选并重置索引
                    df = df.iloc[indices].reset_index(drop=True).copy()
                    
                    # 样本量检查
                    n_subset = len(df)
                    n_features = len([t for t in targets if t in df.columns])
                    if n_subset < 5 or n_subset < n_features:
                        return jsonify({
                            'error': f'聚类 {target_cluster + 1} 的样本量过小 (n={n_subset})，无法进行 PCA 分析。请选择更大的聚类或使用全部数据。'
                        }), 400
                else:
                    return jsonify({'error': f'聚类 {target_cluster + 1} 不存在或没有样本'}), 400
        
        # 如果有分组变量，先按组计算均值
        if group_by and len(group_by) > 0:
            # 验证分组列存在
            valid_group_by = [col for col in group_by if col in df.columns]
            if len(valid_group_by) > 0:
                # 按组计算均值（保持原始顺序）
                valid_targets_in_df = [t for t in targets if t in df.columns]
                agg_cols = valid_group_by + valid_targets_in_df
                
                # 确保数值列转换
                work_df = df[agg_cols].copy()
                for col in valid_targets_in_df:
                    work_df[col] = pd.to_numeric(work_df[col], errors='coerce')
                
                # 按组计算均值
                df = work_df.groupby(valid_group_by, sort=False, as_index=False).mean()
                group_info = f"已按 {', '.join(valid_group_by)} 分组计算均值，共 {len(df)} 组"
            else:
                group_info = None
        else:
            group_info = None
        
        # 使用增强版 PCA 模块
        if HAS_PCA_MODULE:
            # 传递配置参数 (target_configs)
            analyzer = PCAAnalyzer(df, targets, group_by=group_by, target_configs=target_configs)
            analyzer.fit()

            results = {
                'summary': analyzer.get_summary(),
                'loadings': analyzer.get_loadings(),
                'variance': analyzer.get_variance(),
                'weights': analyzer.get_weights(),
                'targets': analyzer.valid_targets
            }
            
            # 添加分组信息
            if group_info:
                results['group_info'] = group_info
            
            # 可选包含得分
            if include_scores:
                results['scores'] = analyzer.get_scores()
            
            # 可选包含图表 (仅生成 PNG 用于网页显示)
            if include_plots:
                try:
                    results['scree_plot'] = analyzer.plot_scree(format='png')
                    results['biplot_2d'] = analyzer.plot_biplot_2d(format='png')
                    if analyzer.n_components >= 3:
                        results['biplot_3d'] = analyzer.plot_biplot_3d(format='png')
                except Exception as plot_error:
                    results['plot_error'] = str(plot_error)
            
            return results
        else:
            # 回退到基础版本
            results = run_pca_analysis(df, targets)
            return jsonify(results)
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'PCA 分析失败: {str(e)}'}), 500


@app.route('/api/pca_plot', methods=['POST'])
def pca_plot():
    """获取 PCA 图表 (支持多种格式和置信椭圆)"""
    if not HAS_PCA_MODULE:
        return jsonify({'error': 'PCA 图表功能不可用'}), 500

    data = request.json
    data_id = data.get('data_id')
    targets = data.get('targets', [])
    plot_type = data.get('plot_type', 'scree')  # 'scree', 'biplot_2d', 'biplot_3d'
    format = data.get('format', 'png')  # 'png', 'pdf', 'svg'

    # 椭圆/分组参数
    draw_ellipse = data.get('draw_ellipse', False)
    group_by = data.get('group_by', [])  # 分组变量列表 (用于 PCA fit 时的聚合，暂未启用)
    ellipse_group = data.get('ellipse_group', '') # 用户在图表控件中选择的具体分组变量
    confidence_level = data.get('confidence_level', 0.95)

    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400

    try:
        df = data_store[data_id]
        analyzer = PCAAnalyzer(df, targets)
        analyzer.fit()

        # 准备分组标签
        group_labels = None
        permanova_stats = None

        # 逻辑优化：统一处理分组列
        # 1. 优先使用 ellipse_group (图表控件指定)
        # 2. 其次检查 group_by (侧边栏指定)，如果是单列，也视为有效分组列

        target_group_col = None

        if ellipse_group and ellipse_group in df.columns:
            target_group_col = ellipse_group
        elif group_by:
            valid_groups = [c for c in group_by if c in df.columns]
            if len(valid_groups) == 1:
                target_group_col = valid_groups[0]
                # 顺便把这个自动推断的列名也打日志，方便调试
                print(f"Auto-detected single group column from group_by: {target_group_col}")

        # 如果确定了用于统计的分组列
        if target_group_col:
            # A. 生成标签
            group_labels = df.loc[analyzer.work_df.index, target_group_col].astype(str).tolist()

            # B. 计算 PERMANOVA
            try:
                print(f"Executing PERMANOVA for group: {target_group_col}")
                permanova_stats = analyzer.perform_permanova(target_group_col)
                print(f"PERMANOVA Result: {permanova_stats}")
            except Exception as e:
                print(f"PERMANOVA failed: {e}")
                permanova_stats = {'error': str(e)}

        # 兼容旧逻辑：多列组合 (Combined Groups)
        # 如果前面没能确定 target_group_col (说明可能是多列组合，或者没选)
        elif group_by:
            valid_groups = [c for c in group_by if c in df.columns]
            if valid_groups:
                subset = df.loc[analyzer.work_df.index, valid_groups]
                group_labels = subset.astype(str).agg('_'.join, axis=1).tolist()
                # 多列组合暂不支持 PERMANOVA，除非创建临时列

        if plot_type == 'scree':
            plot_data = analyzer.plot_scree(format=format)
        elif plot_type == 'biplot_2d':
            plot_data = analyzer.plot_biplot_2d(
                format=format,
                group_labels=group_labels,
                draw_ellipse=draw_ellipse,
                confidence_level=confidence_level,
                permanova_stats=permanova_stats
            )
        elif plot_type == 'biplot_3d':
            if analyzer.n_components < 3:
                return jsonify({'error': '主成分数量少于3，无法生成 3D 双标图'}), 400
            plot_data = analyzer.plot_biplot_3d(format=format)
        else:
            return jsonify({'error': f'不支持的图表类型: {plot_type}'}), 400
        
        return jsonify(plot_data)
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'图表生成失败: {str(e)}'}), 500


def run_pca_analysis(df, targets):
    """
    运行主成分分析 (PCA)
    返回: 主成分载荷、方差解释比例
    """
    # 准备数据: 只选择有效的数值列
    valid_targets = []
    missing_info = {}  # 记录缺失值信息
    
    for col in targets:
        if col in df.columns:
            numeric_series = pd.to_numeric(df[col], errors='coerce')
            valid_count = numeric_series.notna().sum()
            missing_count = numeric_series.isna().sum()
            if valid_count > 0:
                valid_targets.append(col)
                missing_info[col] = {'valid': int(valid_count), 'missing': int(missing_count)}
    
    if len(valid_targets) < 2:
        raise ValueError('有效的数值变量少于2个，无法进行 PCA 分析')
    
    # 提取数据并处理缺失值
    work_df = df[valid_targets].copy()
    for col in valid_targets:
        work_df[col] = pd.to_numeric(work_df[col], errors='coerce')
    
    # 记录原始样本数
    original_samples = len(work_df)
    
    # 使用均值填充策略（而非删除整行）
    # 这样可以保留更多样本，适合变量较多的情况
    for col in valid_targets:
        col_mean = work_df[col].mean()
        if pd.notna(col_mean):
            work_df[col] = work_df[col].fillna(col_mean)
        else:
            # 如果整列都是 NaN，用 0 填充
            work_df[col] = work_df[col].fillna(0)
    
    # 删除仍然存在缺失值的行（理论上不应有）
    work_df = work_df.dropna()
    
    if len(work_df) < 3:
        # 提供详细的诊断信息
        info_str = ", ".join([f"{k}: {v['valid']}有效/{v['missing']}缺失" for k, v in list(missing_info.items())[:5]])
        raise ValueError(f'有效样本数少于3（当前: {len(work_df)}），变量缺失情况: {info_str}')
    
    # 标准化数据
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(work_df)
    
    # 执行 PCA
    n_components = min(len(valid_targets), len(work_df))
    pca = PCA(n_components=n_components)
    pca.fit(scaled_data)
    
    # 构建主成分载荷表
    loadings_data = []
    pc_names = [f'PC{i+1}' for i in range(n_components)]
    
    for i, var_name in enumerate(valid_targets):
        row = {'变量': var_name}
        for j, pc_name in enumerate(pc_names):
            row[pc_name] = round(pca.components_[j, i], 4)
        loadings_data.append(row)
    
    # 构建方差贡献表
    variance_data = []
    for i in range(n_components):
        variance_data.append({
            '主成分': f'PC{i+1}',
            '特征值': round(pca.explained_variance_[i], 4),
            '方差贡献率 (%)': round(pca.explained_variance_ratio_[i] * 100, 2),
            '累计贡献率 (%)': round(sum(pca.explained_variance_ratio_[:i+1]) * 100, 2)
        })
    
    return {
        'loadings': loadings_data,
        'variance': variance_data,
        'targets': valid_targets,
        'n_samples': len(work_df),
        'n_components': n_components,
        'imputation_used': True,  # 标记使用了填充
        'original_samples': original_samples
    }



@app.route('/api/select_directory')
def select_directory():
    """打开文件夹选择对话框（仅本地运行时可用）"""
    if not HAS_TKINTER:
        return jsonify({'success': False, 'message': '目录选择功能仅在本地运行时可用'})
    
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        directory = filedialog.askdirectory(title='选择保存目录')
        
        root.destroy()
        
        if directory:
            return jsonify({'success': True, 'directory': directory})
        else:
            return jsonify({'success': False, 'message': '未选择目录'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'目录选择功能仅在本地运行时可用: {str(e)}'})


@app.route('/api/export_pca', methods=['POST'])
def export_pca():
    """导出 PCA 分析结果到 Excel"""
    data = request.json
    save_directory = data.get('save_directory', '').strip()
    
    # 获取要导出的内容选项
    include_loadings = data.get('include_loadings', True)
    include_variance = data.get('include_variance', True)
    include_weights = data.get('include_weights', True)
    include_scores = data.get('include_scores', True)
    
    # 获取分析数据
    loadings = data.get('loadings', [])
    variance = data.get('variance', [])
    weights = data.get('weights', [])
    scores = data.get('scores', [])
    
    temp_path = None
    try:
        # 确定保存路径
        if save_directory and os.path.isdir(save_directory):
            filename = f"PCA分析结果_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            temp_path = os.path.join(save_directory, filename)
            is_local = True
        else:
            filename = f"pca_export_{uuid.uuid4().hex}.xlsx"
            temp_path = os.path.join(EXPORT_DIR, filename)
            is_local = False
        
        # 使用 openpyxl 引擎写入
        with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
            sheets_written = 0
            
            if include_loadings and loadings:
                df = pd.DataFrame(loadings)
                df = sanitize_dataframe(df)
                df.to_excel(writer, sheet_name='主成分载荷', index=False)
                sheets_written += 1
            
            if include_variance and variance:
                df = pd.DataFrame(variance)
                df = sanitize_dataframe(df)
                df.to_excel(writer, sheet_name='方差贡献', index=False)
                sheets_written += 1
            
            if include_weights and weights:
                df = pd.DataFrame(weights)
                df = sanitize_dataframe(df)
                df.to_excel(writer, sheet_name='特征权重', index=False)
                sheets_written += 1
            
            if include_scores and scores:
                df = pd.DataFrame(scores)
                df = sanitize_dataframe(df)
                df.to_excel(writer, sheet_name='综合得分', index=False)
                sheets_written += 1
            
            if sheets_written == 0:
                pd.DataFrame({"提示": ["未选择任何导出内容"]}).to_excel(writer, sheet_name="注意事项", index=False)
        
        if is_local:
            return jsonify({
                'success': True,
                'message': f'PCA 分析结果已保存到: {temp_path}',
                'local_path': temp_path
            })
        else:
            return send_file(
                temp_path,
                as_attachment=True,
                download_name=f"PCA分析结果_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'PCA 导出失败: {str(e)}'}), 500


@app.route('/api/export', methods=['POST'])
def export_excel():
    sys.stderr.write("Received export request\n")
    data = request.json
    save_directory = data.get('save_directory', '').strip()
    
    # Debug: Check input data size for key sheets
    for k in ['sliced_sep', 'main', 'anova']:
        if k in data:
            sys.stderr.write(f"[export_excel INPUT] {k}: {len(data[k])} rows\n")
        else:
            sys.stderr.write(f"[export_excel INPUT] {k}: MISSING\n")

    temp_path = None
    try:
        # 1. 确定保存路径
        if save_directory and os.path.isdir(save_directory):
            filename = f"分析结果_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            temp_path = os.path.join(save_directory, filename)
            is_local = True
        else:
            filename = f"export_{uuid.uuid4().hex}.xlsx"
            temp_path = os.path.join(EXPORT_DIR, filename)
            is_local = False

        print(f"Writing to {temp_path} (is_local={is_local})")
        
        # 使用 openpyxl 引擎写入
        with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
            sheets_written = 0
            def write_sheet(data_key, sheet_name):
                nonlocal sheets_written
                if data_key in data and data[data_key]:
                    try:
                        print(f"Writing sheet: {sheet_name} (Rows: {len(data[data_key])})")
                        df = pd.DataFrame(data[data_key])
                        print(f"  DataFrame created: {df.shape}, columns: {list(df.columns)[:5]}...")
                        
                        # 检测列是否为空
                        if df.empty:
                            print(f"Warning: DataFrame for {sheet_name} is empty despite input data having {len(data[data_key])} rows?")
                        
                        # 强制列排序：因子列(无"|")在前，数据列(有"|")在后
                        # 仅针对 sliced_sep 和 main 这种扁平化结构的表
                        if data_key in ['sliced_sep', 'main']:
                            cols = list(df.columns)
                            factor_cols = [c for c in cols if " | " not in str(c)]
                            metric_cols = [c for c in cols if " | " in str(c)]
                            new_order = factor_cols + metric_cols
                            print(f"  Reordering: factors={factor_cols}, metrics_count={len(metric_cols)}")
                            if new_order:
                                df = df[new_order]
                            print(f"  After reorder: {df.shape}")

                        # 注意：不再转换为 MultiIndex，因为 to_excel(index=False) 不支持 MultiIndex 列
                        # 直接使用 " | " 分隔的列名写入 Excel，更简洁可靠
                        
                        # 深度清洗数据
                        df = sanitize_dataframe(df)
                        
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        sheets_written += 1
                        print(f"Successfully wrote {sheet_name}")
                    except Exception as e:
                        print(f"Error writing sheet {sheet_name}: {e}")
                        import traceback
                        traceback.print_exc()
            
            # 按顺序写入各个 Sheet
            write_sheet('sliced_comb', '组内比较(组合)')
            write_sheet('sliced_sep', '组内比较(分列)')
            write_sheet('main', '主效应')
            write_sheet('anova', '方差分析')
            write_sheet('corr', '相关分析')
            
            if sheets_written == 0:
                print("No sheets written! Creating warning sheet.")
                pd.DataFrame({"提示": ["本次导出未包含任何有效数据，请确保已执行分析并生成了结果。"]}).to_excel(writer, sheet_name="注意事项", index=False)
            
        print(f"File written successfully: {sheets_written} sheets")

        # 如果是本地保存，直接返回成功信息
        if is_local:
            return jsonify({
                'success': True, 
                'message': f'文件已成功保存至本地：{temp_path}',
                'local_path': temp_path
            })

        # 否则发送文件供浏览器下载
        return send_file(
            temp_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='分析结果.xlsx'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# =====================================================
# 聚类分析 API
# =====================================================

# 存储聚类结果（用于全局过滤）
cluster_store = {}  # {data_id: {'labels': [...], 'n_clusters': int}}


@app.route('/api/analyze_cluster', methods=['POST'])
def analyze_cluster():
    """执行聚类分析"""
    if not HAS_CLUSTER_MODULE:
        return jsonify({'error': '聚类分析模块未安装'}), 500
    
    data = request.json
    data_id = data.get('data_id')
    features = data.get('features', [])  # 数值特征
    factors = data.get('factors', [])    # 因子特征 (用于标记)
    target_configs = data.get('target_configs', {})  # 正向化配置
    algorithm = data.get('algorithm', 'kmeans')
    n_clusters = int(data.get('n_clusters', 3))

    # 额外参数
    linkage_method = data.get('linkage', 'ward')
    random_state = int(data.get('random_state', 42))
    
    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400
    
    if len(features) < 2:
        return jsonify({'error': '聚类分析至少需要2个数值变量'}), 400
    
    try:
        df = data_store[data_id]
        
        # 是否使用均值聚类
        use_means = data.get('use_means', False)
        
        # 数据聚合逻辑
        if use_means and len(factors) > 0:
            # 验证因子列存在
            valid_factors = [f for f in factors if f in df.columns]
            if not valid_factors:
                 return jsonify({'error': '无法使用均值聚类：未找到有效的因子列'}), 400
            
            # 按因子分组计算数值特征的均值
            # 注意：sort=False 保持原始出现顺序
            agg_df = df.groupby(valid_factors, sort=False, as_index=False)[features].mean()
            
            # 使用聚合后的数据进行分析
            analyzer = ClusterAnalyzer(agg_df, features, valid_factors, target_configs)

            # 提示信息
            results_note = f"基于 {', '.join(valid_factors)} 的均值进行聚类 (共 {len(agg_df)} 个组合)"
        else:
            # 使用原始数据
            analyzer = ClusterAnalyzer(df, features, factors, target_configs)
            results_note = ""

        # 执行聚类
        if algorithm == 'kmeans':
            analyzer.fit_kmeans(n_clusters=n_clusters, random_state=random_state)
        else:
            analyzer.fit_hierarchical(n_clusters=n_clusters, linkage_method=linkage_method)
        
        # 存储聚类结果用于全局过滤
        # 当使用均值聚类时，需要将标签映射回原始数据的每一行
        if use_means and len(factors) > 0:
            # 创建分组到聚类标签的映射
            valid_factors = [f for f in factors if f in df.columns]
            agg_labels = analyzer.labels_.tolist()
            
            # 获取聚合数据的分组键
            agg_df = df.groupby(valid_factors, sort=False, as_index=False)[features].mean()
            
            # 为每个聚合行创建一个键
            agg_keys = agg_df[valid_factors].apply(lambda row: tuple(row), axis=1).tolist()
            key_to_label = dict(zip(agg_keys, agg_labels))
            
            # 将原始数据的每一行映射到对应的聚类标签
            original_labels = df[valid_factors].apply(
                lambda row: key_to_label.get(tuple(row), -1), axis=1
            ).tolist()
            
            cluster_store[data_id] = {
                'labels': original_labels,
                'n_clusters': analyzer.n_clusters
            }
        else:
            cluster_store[data_id] = {
                'labels': analyzer.labels_.tolist(),
                'n_clusters': analyzer.n_clusters
            }
        
        # 获取结果
        cluster_summary = analyzer.get_cluster_summary()
        if 'results_note' in locals() and results_note:
             cluster_summary['note'] = results_note
             
        results = {
            'summary': cluster_summary,
            'labeled_data': analyzer.get_labeled_data(),
            'scatter_plot': analyzer.plot_cluster_scatter(format='png'),
            'heatmap_plot': analyzer.plot_heatmap(format='png'),
            'corr_heatmap_plot': analyzer.plot_corr_heatmap(format='png')
        }

        # 层次聚类时添加树状图
        if algorithm == 'hierarchical':
            try:
                results['dendrogram'] = analyzer.plot_dendrogram(format='png')
            except Exception as e:
                results['dendrogram_error'] = str(e)
            try:
                results['circular_heatmap_plot'] = analyzer.plot_circular_heatmap(format='png')
            except Exception as e:
                results['circular_heatmap_error'] = str(e)

        return jsonify(results)
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'聚类分析失败: {str(e)}'}), 500


@app.route('/api/cluster_elbow', methods=['POST'])
def cluster_elbow():
    """获取肘部法则图"""
    if not HAS_CLUSTER_MODULE:
        return jsonify({'error': '聚类分析模块未安装'}), 500
    
    data = request.json
    data_id = data.get('data_id')
    features = data.get('features', [])
    max_k = data.get('max_k', 10)
    
    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400
    
    try:
        df = data_store[data_id]
        analyzer = ClusterAnalyzer(df, features)
        
        elbow_plot = analyzer.plot_elbow(max_k=max_k, format='png')
        elbow_data = analyzer.get_elbow_data(max_k=max_k)
        
        return jsonify({
            'elbow_plot': elbow_plot,
            'elbow_data': elbow_data
        })
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'肘部法则计算失败: {str(e)}'}), 500


@app.route('/api/export_cluster', methods=['POST'])
def export_cluster():
    """导出带聚类标签的数据"""
    if not HAS_CLUSTER_MODULE:
        return jsonify({'error': '聚类分析模块未安装'}), 500
    
    data = request.json
    data_id = data.get('data_id')
    features = data.get('features', [])
    algorithm = data.get('algorithm', 'kmeans')
    n_clusters = data.get('n_clusters', 3)
    linkage_method = data.get('linkage_method', 'ward')
    
    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400
    
    try:
        df = data_store[data_id]
        analyzer = ClusterAnalyzer(df, features)
        
        # 执行聚类
        if algorithm == 'kmeans':
            analyzer.fit_kmeans(n_clusters=n_clusters)
        else:
            analyzer.fit_hierarchical(n_clusters=n_clusters, linkage_method=linkage_method)
        
        # 导出 CSV
        csv_data = analyzer.export_to_csv()
        
        return send_file(
            BytesIO(csv_data),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'聚类结果_{algorithm}_k{n_clusters}.csv'
        )
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'导出失败: {str(e)}'}), 500


@app.route('/api/get_cluster_subsets', methods=['GET'])
def get_cluster_subsets():
    """获取可用的聚类子集列表"""
    data_id = request.args.get('data_id')
    
    if not data_id or data_id not in cluster_store:
        return jsonify({
            'available': False,
            'subsets': [{'value': 'all', 'label': '全部数据', 'count': 0}]
        })
    
    cluster_info = cluster_store[data_id]
    labels = cluster_info['labels']
    n_clusters = cluster_info['n_clusters']
    
    subsets = [{'value': 'all', 'label': '全部数据', 'count': len(labels)}]
    for i in range(n_clusters):
        count = sum(1 for l in labels if l == i)
        subsets.append({
            'value': str(i),
            'label': f'聚类 {i+1}',
            'count': count
        })
    
    return jsonify({
        'available': True,
        'subsets': subsets
    })


@app.route('/api/analyze_heatmap', methods=['POST'])
def analyze_heatmap():
    """生成热图预览"""
    if not HAS_HEATMAP_MODULE:
        return jsonify({'error': '热图模块未安装'}), 500

    data = request.json
    data_id = data.get('data_id')
    x_vars = data.get('x_vars', [])
    y_vars = data.get('y_vars', [])

    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400

    if not x_vars or not y_vars:
        return jsonify({'error': '请选择行变量(X轴)和列变量(Y轴)'}), 400

    try:
        df = data_store[data_id]

        # 生成图片 (Base64)
        # 预览模式使用较低 DPI
        img_bytes_io = generate_heatmap_image(df, x_vars, y_vars, format='png', dpi=100)
        img_data = img_bytes_io.getvalue()
        img_base64 = base64.b64encode(img_data).decode('utf-8')

        return jsonify({
            'success': True,
            'image': img_base64
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'热图生成失败: {str(e)}'}), 500


@app.route('/api/export_heatmap_image', methods=['POST'])
def export_heatmap_image():
    """导出热图图片"""
    if not HAS_HEATMAP_MODULE:
        return jsonify({'error': '热图模块未安装'}), 500

    data = request.json
    data_id = data.get('data_id')
    x_vars = data.get('x_vars', [])
    y_vars = data.get('y_vars', [])
    fmt = data.get('format', 'png')
    dpi = int(data.get('dpi', 600))

    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400

    if not x_vars or not y_vars:
        return jsonify({'error': '请选择行变量(X轴)和列变量(Y轴)'}), 400

    try:
        df = data_store[data_id]

        # 生成图片 (BytesIO)
        img_bytes = generate_heatmap_image(df, x_vars, y_vars, format=fmt, dpi=dpi)

        # 确定 MIME 类型
        mimetype_map = {
            'png': 'image/png',
            'pdf': 'application/pdf',
            'svg': 'image/svg+xml',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg'
        }
        mimetype = mimetype_map.get(fmt, 'application/octet-stream')

        filename = f'heatmap_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.{fmt}'

        return send_file(
            img_bytes,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'热图导出失败: {str(e)}'}), 500


@app.route('/api/nature_plot', methods=['POST'])
def nature_plot():
    """生成 Nature 风格 Python 论文图。"""
    if not HAS_NATURE_PLOT_MODULE:
        return jsonify({'error': 'Nature 绘图模块未安装'}), 500

    data = request.json or {}
    data_id = data.get('data_id')
    chart_type = data.get('chart_type', '')
    config = data.get('config', {})

    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400

    try:
        plot = generate_nature_plot(data_store[data_id], chart_type, config)
        return jsonify({
            'success': True,
            'chart_type': chart_type,
            'plot': plot
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Nature 绘图失败: {str(e)}'}), 500


@app.route('/api/data_columns', methods=['POST'])
def data_columns():
    """按 data_id 返回当前数据集列名与列类型，供前端面板兜底恢复。"""
    data = request.json or {}
    data_id = data.get('data_id')

    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400

    df = data_store[data_id]
    type_analysis = analyze_column_types(df)
    return jsonify({
        'success': True,
        'columns': list(df.columns),
        'rows': len(df),
        **type_analysis
    })


# =====================================================
# 数据整形 (Reshape) API
# =====================================================

# 存储整形结果
reshape_store = {}  # {data_id: DataFrame}


@app.route('/api/reshape_preview', methods=['POST'])
def reshape_preview():
    """预览原始数据（前20行）"""
    data = request.json
    data_id = data.get('data_id')

    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400

    try:
        df = data_store[data_id]
        preview_rows = min(20, len(df))
        preview_df = sanitize_dataframe(df.head(preview_rows))

        return jsonify({
            'columns': list(df.columns),
            'rows': len(df),
            'preview': preview_df.to_dict(orient='records'),
            'preview_rows': preview_rows
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'预览失败: {str(e)}'}), 500


@app.route('/api/reshape', methods=['POST'])
def reshape():
    """执行数据整形操作"""
    data = request.json
    data_id = data.get('data_id')
    action = data.get('action')  # 'melt' or 'pivot'

    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400

    if action not in ('melt', 'pivot'):
        return jsonify({'error': '不支持的操作类型'}), 400

    try:
        df = data_store[data_id].copy()
        result_df = None

        if action == 'melt':
            # 宽表转长表
            id_vars = data.get('id_vars', [])       # 保持不变的列
            value_vars = data.get('value_vars', [])  # 要融化的列
            var_name = data.get('var_name', '变量')   # 融化后的变量名列名
            value_name = data.get('value_name', '值') # 融化后的值列名

            if not id_vars:
                return jsonify({'error': '请选择至少一个 ID 列（保持不变的列）'}), 400
            if not value_vars:
                return jsonify({'error': '请选择至少一个要融化的值列'}), 400

            # 验证列存在
            missing_cols = [c for c in id_vars + value_vars if c not in df.columns]
            if missing_cols:
                return jsonify({'error': f'列不存在: {", ".join(missing_cols)}'}), 400

            result_df = pd.melt(
                df,
                id_vars=id_vars,
                value_vars=value_vars,
                var_name=var_name,
                value_name=value_name
            )

            # 保持原始 id_vars 的出现顺序
            for col in id_vars:
                clean_col = result_df[col].astype(str).str.strip()
                original_order = pd.unique(clean_col)
                result_df[col] = pd.Categorical(clean_col, categories=original_order, ordered=True)
            
            # 保持 value_vars 的选择顺序
            var_order = pd.unique([str(v) for v in value_vars])
            result_df[var_name] = pd.Categorical(
                result_df[var_name].astype(str),
                categories=var_order,
                ordered=True
            )
            result_df = result_df.sort_values(by=id_vars + [var_name]).reset_index(drop=True)
            # 转回 object 类型以便序列化
            for col in result_df.select_dtypes(include='category').columns:
                result_df[col] = result_df[col].astype(str)

        elif action == 'pivot':
            # 长表转宽表
            index_cols = data.get('index_cols', [])   # 行索引列
            columns_col = data.get('columns_col', '')  # 用于展开的列
            values_col = data.get('values_col', '')    # 值列
            agg_func = data.get('agg_func', 'first')   # 聚合函数

            if not index_cols:
                return jsonify({'error': '请选择至少一个索引列'}), 400
            if not columns_col:
                return jsonify({'error': '请选择列名列（用于展开）'}), 400
            if not values_col:
                return jsonify({'error': '请选择值列'}), 400

            # 验证列存在
            all_cols = index_cols + [columns_col, values_col]
            missing_cols = [c for c in all_cols if c not in df.columns]
            if missing_cols:
                return jsonify({'error': f'列不存在: {", ".join(missing_cols)}'}), 400

            # 聚合函数映射
            agg_map = {
                'first': 'first',
                'mean': 'mean',
                'sum': 'sum',
                'count': 'count',
                'max': 'max',
                'min': 'min'
            }
            agg = agg_map.get(agg_func, 'first')

            # 保持 columns_col 的出现顺序
            col_order = list(pd.unique(df[columns_col].astype(str).str.strip()))

            # 执行 pivot
            try:
                result_df = df.pivot_table(
                    index=index_cols,
                    columns=columns_col,
                    values=values_col,
                    aggfunc=agg
                )
            except Exception as pivot_err:
                return jsonify({'error': f'Pivot 失败: {str(pivot_err)}. 可能存在重复值，请选择适当的聚合函数。'}), 400

            # 按原始顺序排列列
            existing_cols = [c for c in col_order if c in result_df.columns]
            result_df = result_df.reindex(columns=existing_cols)

            result_df.columns.name = None  # 清除列名
            result_df = result_df.reset_index()

        # 存储结果
        reshape_store[data_id] = result_df

        # 返回预览
        preview_rows = min(50, len(result_df))
        preview_df = sanitize_dataframe(result_df.head(preview_rows))

        return jsonify({
            'success': True,
            'action': action,
            'columns': list(result_df.columns),
            'total_rows': len(result_df),
            'preview_rows': preview_rows,
            'preview': preview_df.to_dict(orient='records')
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'整形操作失败: {str(e)}'}), 500


@app.route('/api/export_reshape', methods=['POST'])
def export_reshape():
    """导出整形结果到 Excel"""
    data = request.json
    data_id = data.get('data_id')
    save_dir = data.get('save_dir', '')

    if not data_id or data_id not in reshape_store:
        return jsonify({'error': '没有可导出的整形结果，请先执行转换操作'}), 400

    try:
        result_df = reshape_store[data_id]
        clean_df = sanitize_dataframe(result_df)

        # 确定保存路径
        if save_dir and os.path.isdir(save_dir):
            out_dir = save_dir
        else:
            out_dir = EXPORT_DIR

        filename = f"reshape_result_{data_id[:8]}.xlsx"
        filepath = os.path.join(out_dir, filename)

        # 写入 Excel
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            clean_df.to_excel(writer, sheet_name='整形结果', index=False)

            # 自动调整列宽
            ws = writer.sheets['整形结果']
            for col_idx, col_name in enumerate(clean_df.columns, 1):
                max_len = max(
                    len(str(col_name)),
                    clean_df[col_name].astype(str).str.len().max() if len(clean_df) > 0 else 0
                )
                ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max_len + 4, 40)

        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(filepath) and out_dir == EXPORT_DIR:
                    threading.Timer(60, lambda: os.remove(filepath) if os.path.exists(filepath) else None).start()
            except:
                pass
            return response

        return send_file(filepath, as_attachment=True, download_name=filename)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'导出失败: {str(e)}'}), 500


@app.route('/api/reshape_load_result', methods=['POST'])
def reshape_load_result():
    """将整形结果加载为新的数据源，可以用于后续分析"""
    data = request.json
    data_id = data.get('data_id')

    if not data_id or data_id not in reshape_store:
        return jsonify({'error': '没有可用的整形结果'}), 400

    try:
        result_df = reshape_store[data_id].copy()

        # 使用新的 data_id 存储
        new_data_id = str(uuid.uuid4())
        data_store[new_data_id] = result_df
        data_timestamps[new_data_id] = time.time()

        # 分析列类型
        type_analysis = analyze_column_types(result_df)

        response_data = {
            'data_id': new_data_id,
            'columns': list(result_df.columns),
            'rows': len(result_df)
        }
        response_data.update(type_analysis)

        return jsonify(response_data)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'加载失败: {str(e)}'}), 500


# =====================================================
# 智能数据整理 (Smart Tidy) API
# =====================================================

# 存储扫描结果（含内部数据矩阵）
smart_tidy_store = {}  # {data_id: scan_result}


@app.route('/api/smart_tidy_scan', methods=['POST'])
def smart_tidy_scan():
    """扫描 Excel 文件结构，检测合并单元格和多行表头"""
    if not HAS_SMART_TIDY:
        return jsonify({'error': '智能整理模块未安装'}), 500

    data = request.json
    data_id = data.get('data_id')

    if not data_id or data_id not in raw_file_store:
        return jsonify({'error': '该文件不是 Excel 格式或原始数据已过期，请重新上传 Excel 文件'}), 400

    try:
        raw_info = raw_file_store[data_id]
        file_content = raw_info['content']
        sheet_name = raw_info.get('sheet_name')

        # 扫描文件结构
        result = scan_excel_structure(file_content, sheet_name)

        if 'error' in result:
            return jsonify({'error': result['error']}), 400

        # 存储扫描结果（包含内部数据矩阵）
        smart_tidy_store[data_id] = result

        # 返回给前端（排除内部数据）
        response = {k: v for k, v in result.items() if not k.startswith('_')}
        return jsonify(response)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'扫描失败: {str(e)}'}), 500


@app.route('/api/smart_tidy_execute', methods=['POST'])
def smart_tidy_execute():
    """执行智能整理转换"""
    if not HAS_SMART_TIDY:
        return jsonify({'error': '智能整理模块未安装'}), 500

    data = request.json
    data_id = data.get('data_id')

    if not data_id or data_id not in smart_tidy_store:
        return jsonify({'error': '请先执行扫描操作'}), 400

    try:
        scan_result = smart_tidy_store[data_id]

        # 用户选项
        options = {
            'drop_avg': data.get('drop_avg', True),
            'output_format': data.get('output_format', 'semi_long')
        }

        # 执行转换
        result_df = execute_smart_tidy(scan_result, options)

        # 存入 reshape_store（复用导出机制）
        reshape_store[data_id] = result_df

        # 返回预览
        preview_rows = min(50, len(result_df))
        preview_df = sanitize_dataframe(result_df.head(preview_rows))

        return jsonify({
            'success': True,
            'columns': list(result_df.columns),
            'total_rows': len(result_df),
            'preview_rows': preview_rows,
            'preview': preview_df.to_dict(orient='records')
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'转换失败: {str(e)}'}), 500


# =====================================================
# LLM 数据整理 (AI 万能整理) API
# =====================================================

@app.route('/api/llm_tidy', methods=['POST'])
def llm_tidy():
    """双擎整理：优先本地 SmartTidy，失败后回退到 LLM。"""
    data = request.json or {}
    data_id = data.get('data_id')
    drop_avg = data.get('drop_avg', True)
    # API 配置：前端传入优先，否则回退服务器环境变量（如 NVIDIA integrate 配置）
    api_key = (data.get('api_key') or os.environ.get('LLM_API_KEY') or '').strip()
    model = data.get('model') or os.environ.get('LLM_MODEL')
    api_base = data.get('api_base') or os.environ.get('LLM_API_BASE')

    if not data_id or data_id not in raw_file_store:
        return jsonify({'error': '该文件不是 Excel 格式或数据已过期，请重新上传'}), 400

    try:
        raw_info = raw_file_store[data_id]
        file_content = raw_info['content']
        sheet_name = raw_info.get('sheet_name')
        local_error = None

        # 第一引擎：本地 SmartTidy（优先）
        if HAS_SMART_TIDY:
            try:
                scan_result = scan_excel_structure(file_content, sheet_name)
                sub_tables = scan_result.get('sub_tables', []) if isinstance(scan_result, dict) else []

                if isinstance(scan_result, dict) and 'error' not in scan_result and sub_tables:
                    result_df = execute_smart_tidy(
                        scan_result,
                        {
                            'drop_avg': drop_avg,
                            'output_format': 'wide'
                        }
                    )
                    if isinstance(result_df, pd.DataFrame) and not result_df.empty:
                        reshape_store[data_id] = result_df
                        preview_rows = min(50, len(result_df))
                        preview_df = sanitize_dataframe(result_df.head(preview_rows))
                        tables_found = [
                            {
                                'name': item.get('title', ''),
                                'rows': item.get('rows', 0),
                                'row_range': item.get('row_range'),
                                'location': item.get('column_range'),
                            }
                            for item in sub_tables
                        ]

                        return jsonify({
                            'success': True,
                            'engine': 'smart_tidy',
                            'description': '已使用本地稳健解析器完成多子表解析与宽表融合',
                            'tables_found': tables_found,
                            'columns': list(result_df.columns),
                            'total_rows': len(result_df),
                            'preview_rows': preview_rows,
                            'preview': preview_df.to_dict(orient='records')
                        })

                    local_error = '本地解析器执行完成，但结果为空'
                else:
                    if isinstance(scan_result, dict):
                        local_error = scan_result.get('error', '本地解析器未检测到有效子表')
                    else:
                        local_error = '本地解析器返回异常结构'

            except Exception as local_exc:
                traceback.print_exc()
                local_error = f'本地解析器异常: {str(local_exc)}'
        else:
            local_error = '智能整理模块未安装'

        # 第二引擎：LLM 兜底
        if not HAS_LLM_TIDY:
            return jsonify({
                'success': False,
                'description': '本地解析失败，且 LLM 兜底模块不可用',
                'tables_found': [],
                'error': local_error or '未启用可用整理引擎'
            }), 500

        if not api_key:
            return jsonify({
                'success': False,
                'description': '本地解析失败，且未提供 API Key，无法启动 LLM 兜底',
                'tables_found': [],
                'error': local_error or '本地解析失败'
            }), 400

        llm_result = analyze_and_transform(
            file_content=file_content,
            api_key=api_key,
            sheet_name=sheet_name,
            model=model,
            api_base=api_base,
            max_retries=3,
        )

        if not llm_result.get('success'):
            return jsonify({
                'success': False,
                'description': llm_result.get('description', 'LLM 兜底执行失败'),
                'tables_found': llm_result.get('tables_found', []),
                'error': f"{local_error or '本地解析失败'}；LLM: {llm_result.get('error', '未知错误')}"
            }), 400

        result_df = llm_result.get('result_df')
        if not isinstance(result_df, pd.DataFrame) or result_df.empty:
            return jsonify({
                'success': False,
                'description': llm_result.get('description', 'LLM 兜底返回空结果'),
                'tables_found': llm_result.get('tables_found', []),
                'error': f"{local_error or '本地解析失败'}；LLM 未生成可用结果"
            }), 400

        reshape_store[data_id] = result_df
        preview_rows = min(50, len(result_df))
        preview_df = sanitize_dataframe(result_df.head(preview_rows))

        return jsonify({
            'success': True,
            'engine': 'llm_fallback',
            'description': llm_result.get('description') or '本地解析失败后，已由 LLM 兜底完成整理',
            'tables_found': llm_result.get('tables_found', []),
            'columns': list(result_df.columns),
            'total_rows': len(result_df),
            'preview_rows': preview_rows,
            'preview': preview_df.to_dict(orient='records')
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'双擎整理失败: {str(e)}'}), 500


# =====================================================
# 柱状图 (Bar Chart) API
# =====================================================

@app.route('/api/analyze_barchart', methods=['POST'])
def analyze_barchart():
    """生成分组柱状图"""
    if not HAS_BARCHART_MODULE:
        return jsonify({'error': '柱状图模块未安装'}), 500

    data = request.json
    data_id = data.get('data_id')
    group_cols = data.get('group_cols', [])  # 分组列
    value_col = data.get('value_col', '')    # 数值列
    bar_colors = data.get('bar_colors', None)
    band_colors = data.get('band_colors', None)
    show_error_bars = data.get('show_error_bars', True)
    show_letters = data.get('show_letters', False)
    letter_col = data.get('letter_col', None)
    y_label = data.get('y_label', '')
    chart_title = data.get('title', '')
    fig_width = data.get('fig_width', None)
    fig_height = data.get('fig_height', 6)
    bar_width = data.get('bar_width', 0.6)
    font_size = data.get('font_size', 10)
    output_format = data.get('output_format', 'png')
    y_min = data.get('y_min', None)
    y_max = data.get('y_max', None)
    y_step = data.get('y_step', None)
    # 转为 float（前端可能传字符串或空）
    if y_min is not None and y_min != '':
        y_min = float(y_min)
    else:
        y_min = None
    if y_max is not None and y_max != '':
        y_max = float(y_max)
    else:
        y_max = None
    if y_step is not None and y_step != '':
        y_step = float(y_step)
    else:
        y_step = None

    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400

    if not group_cols:
        return jsonify({'error': '请至少选择一个分组列'}), 400

    if not value_col:
        return jsonify({'error': '请选择一个数值列'}), 400

    try:
        df = data_store[data_id]

        # 验证列名存在
        for col in group_cols:
            if col not in df.columns:
                return jsonify({'error': f'分组列 "{col}" 不存在'}), 400
        if value_col not in df.columns:
            return jsonify({'error': f'数值列 "{value_col}" 不存在'}), 400

        # 获取最内层分组的唯一值，用于前端颜色选择器
        inner_col = group_cols[-1] if len(group_cols) > 1 else group_cols[0]
        work_df = df.copy()
        for col in group_cols:
            work_df[col] = work_df[col].astype(str).replace('nan', pd.NA)
            work_df[col] = work_df[col].ffill()
        inner_vals = list(pd.unique(work_df[inner_col].dropna().astype(str)))

        result = generate_bar_chart(
            df=df,
            group_cols=group_cols,
            value_col=value_col,
            bar_colors=bar_colors,
            band_colors=band_colors,
            show_error_bars=show_error_bars,
            show_letters=show_letters,
            letter_col=letter_col,
            y_label=y_label or value_col,
            title=chart_title,
            fig_width=fig_width,
            fig_height=fig_height,
            bar_width=bar_width,
            font_size=font_size,
            output_format=output_format,
            y_min=y_min,
            y_max=y_max,
            y_step=y_step
        )

        return jsonify({
            'success': True,
            'plot': result,
            'inner_col': inner_col,
            'inner_vals': inner_vals
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'柱状图生成失败: {str(e)}'}), 500


@app.route('/api/barchart_preview_groups', methods=['POST'])
def barchart_preview_groups():
    """预览分组信息（用于前端配置颜色）"""
    data = request.json
    data_id = data.get('data_id')
    group_cols = data.get('group_cols', [])

    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期'}), 400

    if not group_cols:
        return jsonify({'error': '请选择分组列'}), 400

    try:
        df = data_store[data_id]
        work_df = df.copy()

        for col in group_cols:
            if col not in df.columns:
                return jsonify({'error': f'列 "{col}" 不存在'}), 400
            work_df[col] = work_df[col].astype(str).replace('nan', pd.NA)
            work_df[col] = work_df[col].ffill()

        # 最内层分组的唯一值
        inner_col = group_cols[-1] if len(group_cols) > 1 else group_cols[0]
        inner_vals = list(pd.unique(work_df[inner_col].dropna().astype(str)))

        return jsonify({
            'inner_col': inner_col,
            'inner_vals': inner_vals
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/healthz', methods=['GET'])
def healthz():
    """轻量健康检查，供启动器轮询。"""
    return jsonify({'status': 'ok'}), 200


@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    """接收前端关闭请求，终止后台进程"""
    # 仅在非生产环境或明确允许时启用
    if os.environ.get('ALLOW_SHUTDOWN', '').lower() not in ('1', 'true', 'yes'):
        return jsonify({'error': 'shutdown disabled'}), 403
    print("收到关闭指令，正在终止服务...")

    def kill_server():
        time.sleep(0.5)  # 稍微等待以确保响应已发送
        os._exit(0)      # 强制终止进程

    threading.Thread(target=kill_server).start()
    return jsonify({'status': 'shutting_down'})


if __name__ == '__main__':
    # 云端部署配置（适配 ModelScope/Render 等）
    port = int(os.environ.get("PORT", 7860))
    app.run(host='0.0.0.0', port=port)
