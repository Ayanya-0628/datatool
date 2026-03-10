import sys
import os
import pandas as pd
import numpy as np

# Add project root to path to import its modules
SlyLab_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(SlyLab_path)

# Change working directory to SlyLab
os.chdir(SlyLab_path)

try:
    from app import run_analysis, sanitize_dataframe
except ImportError as e:
    print(f"Error importing SlyLab: {e}")
    sys.exit(1)

# Path to the data file
file_path = r'C:\Users\16342\Desktop\BaiduSyncdisk\博士\2023-2024苏涛再生稻试验\产量文章\合并图\2024芽长芽重数据分析7D.xlsx'
output_path = r'C:\Users\16342\Desktop\BaiduSyncdisk\博士\2023-2024苏涛再生稻试验\产量文章\合并图\2024芽长芽重数据分析7D_SlyLab分析结果.xlsx'

print(f"Reading file: {file_path}")
try:
    df = pd.read_excel(file_path)
except Exception as e:
    print(f"Error reading file: {e}")
    sys.exit(1)

# Identify Factors and Targets
# Based on the file structure:
# Column 0: Variety (Factor 1)
# Column 1: Treatment (Factor 2)
# Column 2: Replication -> Exclude
# Columns 3+: Targets
factors = df.columns[:2].tolist()
targets = df.columns[3:].tolist()

print(f"Factors: {factors}")
print(f"Targets: {targets}")

# Run Analysis
print("Running analysis using SlyLab core logic...")
results, valid_targets = run_analysis(df, factors, targets)

# Save results to Excel
output_buffer = []

def df_to_rows(title, dataframe):
    if dataframe is None or dataframe.empty:
        return []
    rows = [[title]]
    rows.append(dataframe.columns.tolist())
    rows.extend(dataframe.values.tolist())
    rows.append([]) # Empty row
    return rows

final_rows = []

# 1. ANOVA Table
if 'anova' in results:
    final_rows.extend(df_to_rows("=== 方差分析表 (ANOVA) ===", sanitize_dataframe(results['anova'])))

# 2. Main Effects
if 'main' in results:
    final_rows.extend(df_to_rows("=== 主效应 (Main Effects) ===", sanitize_dataframe(results['main'])))

# 3. Simple Effects
if 'sliced_sep' in results:
    final_rows.extend(df_to_rows("=== 交互作用/组内分析 (Simple Effects) ===", sanitize_dataframe(results['sliced_sep'])))

export_df = pd.DataFrame(final_rows)

print(f"Writing results to: {output_path}")
try:
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        export_df.to_excel(writer, sheet_name='Sheet2', index=False, header=False)
    print("Success! Analysis finished.")
except Exception as e:
    print(f"Error writing file: {e}")
    sys.exit(1)



