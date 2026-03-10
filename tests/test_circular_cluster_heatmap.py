import os
import sys
import uuid
import base64

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from clustering import ClusterAnalyzer
from app import app, data_store


def _build_cluster_df():
    np.random.seed(7)
    groups = ["A"] * 6 + ["B"] * 6 + ["C"] * 6
    base = np.array(
        [[1.0, 2.0, 3.0, 4.0]] * 6
        + [[4.5, 3.5, 2.0, 1.0]] * 6
        + [[2.5, 4.8, 1.4, 3.2]] * 6
    )
    noise = np.random.normal(0, 0.18, size=base.shape)
    values = base + noise
    return pd.DataFrame(
        {
            "品种": [f"材料{i + 1}" for i in range(len(groups))],
            "分组": groups,
            "产量": values[:, 0],
            "糙米率": values[:, 1],
            "整精米率": values[:, 2],
            "蛋白质含量": values[:, 3],
        }
    )


def test_cluster_analyzer_generates_circular_heatmap_png():
    df = _build_cluster_df()
    analyzer = ClusterAnalyzer(
        df,
        features=["产量", "糙米率", "整精米率", "蛋白质含量"],
        factors=["品种", "分组"],
    )
    analyzer.fit_hierarchical(n_clusters=3)

    plot = analyzer.plot_circular_heatmap()

    assert plot["format"] == "png"
    image_bytes = base64.b64decode(plot["data"])
    assert image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(image_bytes) > 5000


def test_analyze_cluster_returns_circular_heatmap_plot():
    df = _build_cluster_df()
    data_id = str(uuid.uuid4())
    data_store[data_id] = df

    try:
        client = app.test_client()
        response = client.post(
            "/api/analyze_cluster",
            json={
                "data_id": data_id,
                "features": ["产量", "糙米率", "整精米率", "蛋白质含量"],
                "factors": ["品种", "分组"],
                "algorithm": "hierarchical",
                "n_clusters": 3,
            },
        )
        payload = response.get_json()

        assert response.status_code == 200
        assert "circular_heatmap_plot" in payload
        assert payload["circular_heatmap_plot"]["format"] == "png"
        image_bytes = base64.b64decode(payload["circular_heatmap_plot"]["data"])
        assert image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    finally:
        data_store.pop(data_id, None)
