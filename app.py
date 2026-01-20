"""
数据分析 Web 应用 - Flask 后端
功能：多因子方差分析、LSD多重比较、组内分析、主效应分析、相关性分析
支持在线部署与分享
修改重点：
1. 强制所有 GroupBy 不排序 (sort=False) 以保持文件原始顺序
2. 强制结果表因子列在最左侧
"""

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
from io import BytesIO

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
# 禁止 jsonify 自动排序键 (关键修复: 保持 DataFrame 列顺序)
app.config['JSON_SORT_KEYS'] = False
app.json.sort_keys = False

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

# 存储上传的数据 (带时间戳用于清理)
data_store = {}
data_timestamps = {}
DATA_EXPIRE_SECONDS = 3600  # 数据1小时后过期

# 暂存未确认的文件 (用于多Sheet选择)
temp_file_store = {}

# 导出文件存放目录
EXPORT_DIR = os.path.join(os.getcwd(), 'exports')
if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR)


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
        with open("last_error.txt", "w", encoding="utf-8") as f:
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
        results['anova'] = df_anova.pivot(index='Source', columns='指标', values='Value').reset_index()

    # (B) Main Effects (Main Table)
    if raw_results['main_rows']:
        df_raw = pd.DataFrame(raw_results['main_rows'])
        # Filter for Mean/Letter/SD
        df_std = df_raw[df_raw['Type'].isin(['Mean', 'Letter', 'SD'])].copy()
        
        # Pivot: Index=[Factor, Level], Columns=[指标, Type]
        # We temporarily set Factor/Level as categorical to sort the pivot index automatically
        for f in ['Factor', 'Level']: # 'Factor' col contains factor names, 'Level' col contains level names
             pass # Logic for main effects is slightly different as 'Factor' is a column itself
        
        # Manually constructing pivot to avoid multi-index complexity issues
        df_pivot = df_std.pivot_table(
            index=['Factor', 'Level'], 
            columns=['指标', 'Type'], 
            values='Value', 
            aggfunc='first'
        )
        
        # Flatten Columns
        new_cols = [f"{t} | {m}" for t, m in df_pivot.columns]
        df_pivot.columns = new_cols
        df_pivot = df_pivot.reset_index()
        
        # Re-sort Rows: 
        # Main Effects table has mixed factors in the 'Factor' column.
        # We enable a SortKey.
        sort_map = {}
        idx = 0
        for f in factors:
            if f in file_orders:
                for val in file_orders[f]:
                    sort_map[(f, val)] = idx
                    idx += 1
        
        df_pivot['SortKey'] = df_pivot.apply(lambda r: sort_map.get((r['Factor'], r['Level']), 99999), axis=1)
        df_pivot = df_pivot.sort_values('SortKey').drop(columns=['SortKey'])
        
        # Re-sort Columns
        # For Main input, 'factors' list isn't columns, but rows. 
        # Columns are Factor, Level, + Metrics.
        base_cols = ['Factor', 'Level']
        final_main_cols = base_cols + [c for c in df_pivot.columns if c not in base_cols]
        # Re-order metric columns strictly
        strict_metric_cols = []
        for t in valid_targets:
            for m in ['Mean', 'Letter', 'SD']:
                cname = f"{t} | {m}"
                if cname in df_pivot.columns:
                    strict_metric_cols.append(cname)
        
        results['main'] = df_pivot[base_cols + strict_metric_cols]

        # (B-2) Main Effects (Combined)
        df_comb_raw = df_raw[df_raw['Type'] == 'Combined'].copy()
        df_comb_pivot = df_comb_raw.pivot_table(index=['Factor', 'Level'], columns='指标', values='Value', aggfunc='first').reset_index()
        # Sort rows same way
        df_comb_pivot['SortKey'] = df_comb_pivot.apply(lambda r: sort_map.get((r['Factor'], r['Level']), 99999), axis=1)
        results['main_combined'] = df_comb_pivot.sort_values('SortKey').drop(columns=['SortKey'])

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
        # Sort factors by user user selection
        facs_sorted = [f for f in factors if f in facs]
        results['sliced_comb'] = df_pivot[facs_sorted + others]

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

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload():
    """上传文件并解析列信息"""
    if 'file' not in request.files:
        return jsonify({'error': '未找到上传文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    try:
        filename = file.filename.lower()
        
        # 读取文件
        if filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif filename.endswith(('.xls', '.xlsx')):
            # 先检查是否有多个 Sheet
            xls = pd.ExcelFile(file)
            if len(xls.sheet_names) > 1:
                # 暂存文件内容
                file.seek(0)
                temp_id = str(uuid.uuid4())
                temp_file_store[temp_id] = {
                    'content': file.read(),
                    'filename': file.filename,
                    'timestamp': time.time()
                }
                return jsonify({
                    'status': 'select_sheet',
                    'sheets': xls.sheet_names,
                    'temp_id': temp_id
                })
            else:
                df = pd.read_excel(xls, sheet_name=0)
        else:
            return jsonify({'error': '不支持的文件格式，请上传 .csv, .xls 或 .xlsx 文件'}), 400
        
        # 保存数据
        data_id = str(uuid.uuid4())
        data_store[data_id] = df
        data_timestamps[data_id] = time.time()
        
        return jsonify({
            'data_id': data_id,
            'columns': list(df.columns),
            'rows': len(df)
        })
    
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
        
        return jsonify({
            'data_id': data_id,
            'columns': list(df.columns),
            'rows': len(df)
        })
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'加载失败: {str(e)}'}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """执行分析"""
    data = request.json
    data_id = data.get('data_id')
    factors = data.get('factors', [])
    targets = data.get('targets', [])
    
    if not data_id or data_id not in data_store:
        return jsonify({'error': '数据已过期，请重新上传文件'}), 400
    
    if not factors or not targets:
        return jsonify({'error': '请选择因子和性状'}), 400
    
    try:
        df = data_store[data_id]
        
        # 运行分析
        results, valid_targets = run_analysis(df, factors, targets)
        
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
        
        return jsonify(response)
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'分析失败: {str(e)}'}), 500


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


if __name__ == '__main__':
    app.run(debug=True, port=5000)