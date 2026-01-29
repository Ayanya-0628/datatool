import sys
import os
import pandas as pd
import time

# Add AntiAPP to path
antiapp_path = r"E:\AntiAPP"
sys.path.append(antiapp_path)
os.chdir(antiapp_path)

try:
    from app import run_analysis, sanitize_dataframe
except ImportError as e:
    print(f"Error importing AntiAPP: {e}")
    sys.exit(1)

file_path = r'C:\Users\16342\Desktop\BaiduSyncdisk\博士\2023-2024苏涛再生稻试验\产量文章\合并图\2024芽长芽重数据分析7D.xlsx'

print(f"Reading file: {file_path}")
try:
    df = pd.read_excel(file_path)
except Exception as e:
    print(f"Error reading file (is it open?): {e}")
    sys.exit(1)

# Define factors and targets
factors = df.columns[:2].tolist()
targets = df.columns[3:].tolist()

print(f"Running analysis on targets: {targets}")
results, valid_targets = run_analysis(df, factors, targets)

if 'anova' not in results:
    print("Error: No ANOVA results generated.")
    sys.exit(1)

anova_df = sanitize_dataframe(results['anova'])
print("ANOVA results extracted.")

# Retry logic for permission error
max_retries = 3
for i in range(max_retries):
    try:
        print(f"Attempting to write to Sheet2 (Try {i+1}/{max_retries})...")
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            anova_df.to_excel(writer, sheet_name='Sheet2', index=False)
        print("Success! ANOVA results written to Sheet2.")
        break
    except PermissionError:
        print("Permission denied. File might be open.")
        if i < max_retries - 1:
            print("Waiting 5 seconds before retrying... Please close the Excel file.")
            time.sleep(5)
        else:
            print("Failed to write to file after retries. Please close the file and try again.")
            sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
