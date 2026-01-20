import pandas as pd
xl = pd.ExcelFile(r'c:\Users\16342\Desktop\Analysis_Result.xlsx')
with open('excel_structure.txt', 'w', encoding='utf-8') as f:
    for s in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=s)
        f.write(f"\n--- Sheet: {s} ---\n")
        f.write(f"Cols: {list(df.columns)}\n")
        f.write(f"Data:\n{df.head(20).to_string()}\n")
