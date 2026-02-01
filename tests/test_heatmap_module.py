import sys
import os
import pandas as pd
import numpy as np
import logging

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.heatmap import generate_heatmap_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_generate_heatmap():
    logger.info("Starting heatmap generation test...")

    # Create dummy data
    np.random.seed(42)
    data = {
        'Trait1': np.random.rand(20),
        'Trait2': np.random.rand(20),
        'Trait3': np.random.rand(20),
        'Factor1': np.random.rand(20) * 0.5 + np.random.rand(20), # Correlation
        'Factor2': np.random.rand(20)
    }
    df = pd.DataFrame(data)

    x_cols = ['Trait1', 'Trait2', 'Trait3']
    y_cols = ['Factor1', 'Factor2']

    logger.info("Generating heatmap...")
    try:
        img_buffer = generate_heatmap_image(df, x_cols, y_cols)

        output_path = os.path.join(os.path.dirname(__file__), 'test_heatmap.png')
        with open(output_path, 'wb') as f:
            f.write(img_buffer.getvalue())

        logger.info(f"Heatmap saved successfully to {output_path}")
        print("TEST PASSED: Image generated.")
    except Exception as e:
        logger.error(f"Failed to generate heatmap: {e}")
        print(f"TEST FAILED: {e}")
        raise

if __name__ == "__main__":
    test_generate_heatmap()
