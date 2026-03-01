import pandas as pd
import os
import numpy as np

# -------------------------- 1. 读取 Excel 数据 --------------------------
# 请把你的 Excel 文件路径替换到这里（如 r"C:\Users\你的用户名\Desktop\data.xlsx"）
file_path = r"C:\Users\张银\Desktop\3333.xlsx"
df = pd.read_excel(file_path)

# -------------------------- 2. 定义指标类型 --------------------------
# 极大型（效益型）
max_type = [
    "糙米率", "精米率", "整精米率", "长宽比", "热浆粘度", "最终粘度", "崩解值", "峰值粘度", "清蛋白", "球蛋白", "醇溶蛋白", "谷蛋白", "产量"
]
# 极小型（成本型）
min_type = [
    "垩白粒率", "垩白度", "稻米蛋白质含量", "糊化温度", "消减值", "峰值时间"
]
# 区间型（直链淀粉含量，最优区间 [13.0, 22.0]）
interval_type = ["直链淀粉含量"]
a, b = 13.0, 22.0  # 最优区间

# -------------------------- 3. 极差变换正向化函数 --------------------------
def normalize_max(series):
    """极大型正向化：(x - min)/(max - min)"""
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series(np.ones_like(series), index=series.index)
    return (series - min_val) / (max_val - min_val)

def normalize_min(series):
    """极小型正向化：(max - x)/(max - min)"""
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series(np.ones_like(series), index=series.index)
    return (max_val - series) / (max_val - min_val)

def normalize_interval(series, a, b):
    """区间型正向化：按你给的公式"""
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

# -------------------------- 4. 自动识别列并正向化 --------------------------
df_norm = df.copy()

# 极大型
for col in max_type:
    if col in df.columns:
        df_norm[col + "_正向化"] = normalize_max(df[col])

# 极小型
for col in min_type:
    if col in df.columns:
        df_norm[col + "_正向化"] = normalize_min(df[col])

# 区间型
for col in interval_type:
    if col in df.columns:
        df_norm[col + "_正向化"] = normalize_interval(df[col], a, b)

# -------------------------- 5. 保存到桌面 --------------------------
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
save_path = os.path.join(desktop_path, "数据正向化.xlsx")
df_norm.to_excel(save_path, index=False)

print(f"✅ 正向化完成！文件已保存到：\n{save_path}")