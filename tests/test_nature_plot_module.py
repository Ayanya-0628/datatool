import base64
import os
import sys
import uuid

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app, data_store
from modules.nature_plot import generate_nature_plot


def _df():
    return pd.DataFrame(
        {
            "group": ["T1", "T2", "T3"],
            "control": [0.72, 0.76, 0.81],
            "treatment": [0.78, 0.83, 0.88],
            "err_control": [0.03, 0.02, 0.02],
            "err_treatment": [0.02, 0.03, 0.02],
            "estimate": [0.18, -0.06, 0.24],
            "ci_low": [0.05, -0.19, 0.10],
            "ci_high": [0.31, 0.08, 0.38],
        }
    )


def test_generate_nature_grouped_bar_png():
    plot = generate_nature_plot(
        _df(),
        "grouped_bar",
        {
            "category_col": "group",
            "value_cols": ["control", "treatment"],
            "error_cols": ["err_control", "err_treatment"],
            "format": "png",
        },
    )

    assert plot["format"] == "png"
    raw = base64.b64decode(plot["data"])
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(raw) > 5000


def test_generate_nature_heatmap_svg_preserves_text():
    plot = generate_nature_plot(
        _df(),
        "heatmap",
        {
            "row_label_col": "group",
            "value_cols": ["control", "treatment"],
            "format": "svg",
            "annotate": True,
        },
    )

    assert plot["format"] == "svg"
    assert plot["editable_text"] is True
    assert "<svg" in base64.b64decode(plot["data"]).decode("utf-8", errors="ignore")


def test_nature_plot_api_returns_plot():
    data_id = str(uuid.uuid4())
    data_store[data_id] = _df()
    try:
        client = app.test_client()
        response = client.post(
            "/api/nature_plot",
            json={
                "data_id": data_id,
                "chart_type": "forest",
                "config": {
                    "label_col": "group",
                    "estimate_col": "estimate",
                    "ci_low_col": "ci_low",
                    "ci_high_col": "ci_high",
                    "format": "png",
                },
            },
        )
        payload = response.get_json()

        assert response.status_code == 200
        assert payload["success"] is True
        assert payload["plot"]["format"] == "png"
    finally:
        data_store.pop(data_id, None)


def test_data_columns_api_returns_current_dataset_columns():
    data_id = str(uuid.uuid4())
    data_store[data_id] = _df()
    try:
        response = app.test_client().post("/api/data_columns", json={"data_id": data_id})
        payload = response.get_json()

        assert response.status_code == 200
        assert payload["success"] is True
        assert payload["columns"] == list(_df().columns)
        assert payload["column_types"]["control"] == "numeric"
    finally:
        data_store.pop(data_id, None)
