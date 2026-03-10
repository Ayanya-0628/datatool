import sys
import os
import pandas as pd
import numpy as np

# Add project root to path to import its modules
SlyLab_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(SlyLab_path)

# Change working directory to SlyLab so it can find its dependencies/env if needed
os.chdir(SlyLab_path)

try:
    from app import run_analysis, sanitize_dataframe
except ImportError as e:
    print(f"Error importing SlyLab: {e}")
    sys.exit(1)

# Path to the data file
file_path = r'C:\Users\16342\Desktop\BaiduSyncdisk\博士\2023-2024苏涛再生稻试验\产量文章\合并图\2024芽长芽重数据分析7D.xlsx'

print(f"Reading file: {file_path}")
df = pd.read_excel(file_path)

# Identify Factors and Targets
# Based on the file structure:
# Column 0: Variety (Factor 1)
# Column 1: Treatment (Factor 2)
# Column 2: Replication (Block) -> Usually excluded from factors in simple 2-way ANOVA unless specifically requested as Block
# Columns 3+: Targets (Response Variables)

factors = df.columns[:2].tolist() # First 2 columns as factors
targets = df.columns[3:].tolist() # From 4th column onwards are targets

print(f"Factors: {factors}")
print(f"Targets: {targets}")

# Run Analysis
print("Running analysis using SlyLab core logic...")
results, valid_targets = run_analysis(df, factors, targets)

# Save results to Sheet2
# Since SlyLab produces multiple tables (ANOVA, Main Effects, Interaction),
# we will write them to Sheet2 stacked vertically or to separate sheets.
# The user asked for "Sheet2". We will stack them for convenience or use multiple sheets if too large.
# Let's try to put the main ANOVA table in Sheet2, and others in Sheet2_Details if needed.
# Or better: Write everything to Sheet2 with some spacing.

output_buffer = []

def df_to_rows(title, dataframe):
    rows = [[title]]
    rows.append(dataframe.columns.tolist())
    rows.extend(dataframe.values.tolist())
    rows.append([]) # Empty row
    return rows

final_rows = []

# 1. ANOVA Table
if 'anova' in results and isinstance(results['anova'], pd.DataFrame):
    final_rows.extend(df_to_rows("=== 方差分析表 (ANOVA) ===", sanitize_dataframe(results['anova'])))

# 2. Main Effects (Mean + LSD)
if 'main' in results and isinstance(results['main'], pd.DataFrame):
    final_rows.extend(df_to_rows("=== 主效应 (Main Effects) ===", sanitize_dataframe(results['main'])))

# 3. Simple Effects / Interaction (Sliced)
if 'sliced_sep' in results and isinstance(results['sliced_sep'], pd.DataFrame):
    final_rows.extend(df_to_rows("=== 交互作用/组内分析 (Simple Effects) ===", sanitize_dataframe(results['sliced_sep'])))

# Create DataFrame for export
export_df = pd.DataFrame(final_rows)

print("Writing results to Excel...")
with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    # Write Combined Report to Sheet2
    export_df.to_excel(writer, sheet_name='Sheet2', index=False, header=False)

    # Also write separate sheets for cleaner look (Optional, but good for SlyLab style)
    # sanitize_dataframe(results.get('anova')).to_excel(writer, sheet_name='Anti_ANOVA', index=False)
    # sanitize_dataframe(results.get('main')).to_excel(writer, sheet_name='Anti_Main', index=False)
    # sanitize_dataframe(results.get('sliced_sep')).to_excel(writer, sheet_name='Anti_Interaction', index=False)

print("Success! Analysis finished.")



