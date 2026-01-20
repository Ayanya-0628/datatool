import pandas as pd
import json

try:
    xl = pd.ExcelFile(r'c:\Users\16342\Desktop\Analysis_Result.xlsx')
    result = {}
    for s in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=s)
        result[s] = {
            'columns': list(df.columns),
            'head': df.head(10).to_dict(orient='records')
        }
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
