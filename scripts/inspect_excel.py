import pandas as pd

file_path = "相关分析图.xlsx"

try:
    # Load the Excel file to get sheet names
    xls = pd.ExcelFile(file_path)
    print("Sheet names:", xls.sheet_names)

    # Read and print the first few rows of the first sheet
    if len(xls.sheet_names) > 0:
        sheet1_name = xls.sheet_names[0]
        print(f"\n--- First Sheet: {sheet1_name} ---")
        df1 = pd.read_excel(file_path, sheet_name=sheet1_name, nrows=5)
        print("Columns:", df1.columns.tolist())
        print(df1)

    # Read and print the first few rows of the second sheet
    if len(xls.sheet_names) > 1:
        sheet2_name = xls.sheet_names[1]
        print(f"\n--- Second Sheet: {sheet2_name} ---")
        df2 = pd.read_excel(file_path, sheet_name=sheet2_name, nrows=5)
        print("Columns:", df2.columns.tolist())
        print(df2)
    else:
        print("\nSecond sheet does not exist.")

except Exception as e:
    print(f"Error reading Excel file: {e}")
