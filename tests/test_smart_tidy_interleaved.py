import os
import sys
import uuid

import pandas as pd

# Add project root to import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as app_module
from smart_tidy import execute_smart_tidy, scan_excel_structure
from app import app, raw_file_store, reshape_store


FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__),
    "fixtures",
    "data_tidy_test.xlsx",
)


def _read_fixture_bytes():
    with open(FIXTURE_PATH, "rb") as handle:
        return handle.read()


def test_interleaved_multitable_extracts_wide_clean_dataframe():
    content = _read_fixture_bytes()
    scan_result = scan_excel_structure(content)

    assert "error" not in scan_result
    assert scan_result["sub_table_count"] == 7

    result_df = execute_smart_tidy(scan_result, {"drop_avg": True})

    assert isinstance(result_df, pd.DataFrame)
    assert not result_df.empty
    assert result_df.shape == (21, 19)
    assert set(["处理", "重复"]).issubset(result_df.columns)

    metric_columns = [col for col in result_df.columns if col not in {"处理", "重复"}]
    assert len(metric_columns) >= 17
    assert all("_" in col for col in metric_columns)
    assert not any(any(k in col for k in ("平均", "均值", "平均值")) for col in metric_columns)

    repeats = set(result_df["重复"].astype(str))
    assert repeats == {"重复1", "重复2", "重复3"}

    null_ratio = result_df.isna().sum().sum() / (result_df.shape[0] * result_df.shape[1])
    assert null_ratio < 0.05


def test_llm_tidy_endpoint_uses_local_parser_without_api_key():
    test_id = str(uuid.uuid4())
    raw_file_store[test_id] = {
        "content": _read_fixture_bytes(),
        "filename": "data_tidy_test.xlsx",
        "sheet_name": None,
    }

    try:
        client = app.test_client()
        response = client.post("/api/llm_tidy", json={"data_id": test_id})
        payload = response.get_json()

        assert response.status_code == 200
        assert payload["success"] is True
        assert payload["total_rows"] == 21
        assert len(payload["columns"]) >= 19
        assert payload["description"]
        assert len(payload["tables_found"]) == 7
        assert payload["engine"] == "smart_tidy"
        assert test_id in reshape_store
    finally:
        raw_file_store.pop(test_id, None)
        reshape_store.pop(test_id, None)


def test_llm_tidy_endpoint_fallbacks_to_llm_when_local_scan_fails(monkeypatch):
    test_id = str(uuid.uuid4())
    raw_file_store[test_id] = {
        "content": _read_fixture_bytes(),
        "filename": "data_tidy_test.xlsx",
        "sheet_name": None,
    }

    mocked_df = pd.DataFrame(
        [
            {"处理": "T1", "重复": "重复1", "指标A": 1.0},
            {"处理": "T1", "重复": "重复2", "指标A": 2.0},
        ]
    )

    monkeypatch.setattr(app_module, "scan_excel_structure", lambda *_args, **_kwargs: {"error": "scan failed"})
    monkeypatch.setattr(
        app_module,
        "analyze_and_transform",
        lambda **_kwargs: {
            "success": True,
            "description": "llm fallback ok",
            "tables_found": [{"name": "fallback_table"}],
            "result_df": mocked_df,
            "error": None,
            "llm_response": "{}",
        },
    )

    try:
        client = app.test_client()
        response = client.post(
            "/api/llm_tidy",
            json={"data_id": test_id, "api_key": "dummy-key", "model": "dummy-model"},
        )
        payload = response.get_json()

        assert response.status_code == 200
        assert payload["success"] is True
        assert payload["engine"] == "llm_fallback"
        assert payload["total_rows"] == 2
        assert payload["columns"] == ["处理", "重复", "指标A"]
        assert test_id in reshape_store
    finally:
        raw_file_store.pop(test_id, None)
        reshape_store.pop(test_id, None)
