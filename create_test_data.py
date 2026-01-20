
import pandas as pd
import numpy as np

# Sheet 1: Data1
df1 = pd.DataFrame({
    'Factor1': ['A']*4 + ['B']*4,
    'Factor2': ['X','X','Y','Y']*2,
    'Trait': np.random.rand(8) * 10
})

# Sheet 2: Data2
df2 = pd.DataFrame({
    'Variety': ['V1']*4 + ['V2']*4,
    'Treatment': ['T1','T1','T2','T2']*2,
    'Yield': np.random.rand(8) * 100
})

with pd.ExcelWriter('multi_sheet_test.xlsx') as writer:
    df1.to_excel(writer, sheet_name='Sheet1_Data', index=False)
    df2.to_excel(writer, sheet_name='Sheet2_Yield', index=False)

print("Created multi_sheet_test.xlsx")
