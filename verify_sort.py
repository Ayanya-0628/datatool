import pandas as pd
import numpy as np
import sys
import os

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

try:
    from app import run_analysis
except ImportError:
    print("Error: Could not import run_analysis from app.py. Make sure verification script is in the same directory.")
    exit(1)

def verify_sorting():
    print("=== Verifying Sorting Logic ===")
    
    # 1. Create Mock Data with specific appearance order
    # Factors: Variety (V2 appears first, then V1), Treatment (T2, T1)
    data = {
        'Variety': ['V2', 'V2', 'V2', 'V1', 'V1', 'V1', 'V3', 'V3', 'V3', 'V1', 'V1'], # Mixed appearance
        'Treatment': ['T1']*3 + ['T1']*3 + ['T1']*3 + ['T2']*2,
        'Y': np.random.rand(11) * 10
    }
    df = pd.DataFrame(data)
    
    # Force appearance order: V2, V1, V3
    # Note: line 9 puts V1 again at end, but first appearance is index 3.
    # Order should be V2 (index 0), V1 (index 3), V3 (index 6).
    
    print("Input Data Head:")
    print(df.head())
    
    factors = ['Variety', 'Treatment']
    targets = ['Y']
    
    print("\nRunning Analysis...")
    results, _ = run_analysis(df, factors, targets)
    
    # Check sliced_sep
    if 'sliced_sep' not in results:
        print("[FAIL] sliced_sep not in results")
        return

    sliced_sep = results['sliced_sep'] 
    # Usually sliced_sep is a DataFrame, but if serialized it might be list of dicts.
    # The run_analysis returns dataframe inside the dict before jsonify.
    
    print("\n--- Result Analysis (sliced_sep) ---")
    cols = sliced_sep.columns.tolist()
    print("Columns:", cols)
    
    # Check 1: Metric Order (Mean, Letter, SD)
    y_cols = [c for c in cols if 'Y |' in c]
    print("Metric Columns Found:", y_cols)
    
    expected_suffix_order = ['Mean', 'Letter', 'SD']
    actual_suffixes = [c.split(' | ')[1] for c in y_cols if ' | ' in c]
    
    if actual_suffixes == expected_suffix_order:
        print("[PASS] Metric column order is correct: Mean -> Letter -> SD")
    else:
        print(f"[FAIL] Metric column order is INCORRECT. Expected {expected_suffix_order}, got {actual_suffixes}")

    # Check 2: Row Order
    # We expect Variety to be ordered V2, V1, V3 based on appearance
    varieties = sliced_sep['Variety'].unique().tolist()
    print("Result Variety Order:", varieties)
    
    if varieties == ['V2', 'V1', 'V3']:
        print("[PASS] Row order preserves input appearance (V2, V1, V3).")
    else:
        print(f"[FAIL] Row order is INCORRECT. Expected ['V2', 'V1', 'V3'], got {varieties}")

    # Check 3: Factor Column Position
    if cols[0] == 'Variety' and cols[1] == 'Treatment':
        print("[PASS] Factor columns are at the start.")
    else:
        print("[FAIL] Factor columns are NOT at the start.")

if __name__ == "__main__":
    verify_sorting()
