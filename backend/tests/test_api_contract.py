"""API Contract Tests.

Verify that all backend endpoint response shapes match the Pydantic
schemas expected by the frontend. These tests ensure the contract
between frontend and backend stays consistent.

Run:  pytest backend/tests/test_api_contract.py -v
"""

import pytest


class TestOpenAPISchema:
    """All expected endpoints must be present in the OpenAPI schema."""

    EXPECTED_PATHS = [
        "/api/v1/health",
        "/api/v1/upload/csv",
        "/api/v1/upload/{session_id}/files",
        "/api/v1/upload/{session_id}",
        "/api/v1/data/sessions",
        "/api/v1/data/sessions/{session_id}",
        "/api/v1/data/sessions/{session_id}/factor",
        "/api/v1/data/sessions/{session_id}/prices",
        "/api/v1/data/preview",
        "/api/v1/analysis/run",
        "/api/v1/analysis/{analysis_id}/status",
        "/api/v1/analysis/{analysis_id}/results",
        "/api/v1/analysis/{analysis_id}/results/ic",
        "/api/v1/analysis/{analysis_id}/results/returns",
        "/api/v1/analysis/{analysis_id}/results/alpha-beta",
        "/api/v1/analysis/{analysis_id}/results/turnover",
        "/api/v1/analysis/{analysis_id}/results/summary-tables",
        "/api/v1/analysis/{analysis_id}/results/charts/{chart_type}",
        "/api/v1/tasks/{task_id}",
        "/api/v1/tasks/",
        "/api/v1/tasks/{task_id}/revoke",
    ]

    def test_all_endpoints_in_openapi(self, client):
        schema = client.get("/openapi.json").json()
        paths = schema["paths"]
        for path in self.EXPECTED_PATHS:
            assert path in paths, f"Missing endpoint: {path}"

    def test_health_endpoint_returns_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "version" in data


class TestUploadContract:
    """Upload endpoint response shapes must match UploadResponse schema."""

    def test_upload_response_shape(self, client, factor_csv):
        factor_csv.seek(0)
        resp = client.post(
            "/api/v1/upload/csv",
            files={"file": ("factor.csv", factor_csv, "text/csv")},
            data={"file_type": "factor"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        assert "file_id" in data
        assert isinstance(data["file_id"], str)
        assert "file_type" in data
        assert data["file_type"] == "factor"
        assert "rows_ingested" in data
        assert isinstance(data["rows_ingested"], int)
        assert data["rows_ingested"] > 0
        assert "columns" in data
        assert isinstance(data["columns"], list)
        assert len(data["columns"]) > 0

    def test_upload_prices_shape(self, client, session_id, prices_csv):
        prices_csv.seek(0)
        resp = client.post(
            "/api/v1/upload/csv",
            files={"file": ("prices.csv", prices_csv, "text/csv")},
            data={"file_type": "prices", "session_id": session_id},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_type"] == "prices"
        assert data["rows_ingested"] > 0
        assert isinstance(data["columns"], list)

    def test_upload_invalid_file_type_returns_400(self, client, factor_csv):
        factor_csv.seek(0)
        resp = client.post(
            "/api/v1/upload/csv",
            files={"file": ("factor.csv", factor_csv, "text/csv")},
            data={"file_type": "invalid_type"},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data

    def test_upload_empty_csv_returns_400(self, client, empty_csv):
        empty_csv.seek(0)
        resp = client.post(
            "/api/v1/upload/csv",
            files={"file": ("empty.csv", empty_csv, "text/csv")},
            data={"file_type": "factor"},
        )
        assert resp.status_code == 400

    def test_list_session_files_shape(self, client, session_id):
        resp = client.get(f"/api/v1/upload/{session_id}/files")
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["session_id"] == session_id
        assert "files" in data
        assert isinstance(data["files"], list)
        if data["files"]:
            f = data["files"][0]
            assert "file_id" in f
            assert "file_type" in f
            assert "original_filename" in f
            assert "file_size_bytes" in f
            assert "row_count" in f
            assert "uploaded_at" in f

    def test_list_files_nonexistent_session_returns_404(self, client):
        resp = client.get("/api/v1/upload/nonexistent-id/files")
        assert resp.status_code == 404
        assert "detail" in resp.json()

    def test_delete_session_returns_204(self, client, session_id):
        resp = client.delete(f"/api/v1/upload/{session_id}")
        assert resp.status_code == 204

    def test_delete_nonexistent_session_returns_404(self, client):
        resp = client.delete("/api/v1/upload/nonexistent-id")
        assert resp.status_code == 404


class TestDataContract:
    """Data browsing endpoints must match PaginatedData / SessionSummary / etc."""

    def test_list_sessions_shape(self, client, session_id):
        resp = client.get("/api/v1/data/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            s = data[0]
            assert "session_id" in s
            assert "created_at" in s
            assert "status" in s
            assert "asset_count" in s
            assert "analysis_count" in s

    def test_get_session_detail_shape(self, client, session_id):
        resp = client.get(f"/api/v1/data/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert "name" in data
        assert "description" in data
        assert "created_at" in data
        assert "status" in data
        assert "files" in data
        assert isinstance(data["files"], list)
        assert "asset_count" in data
        assert isinstance(data["asset_count"], int)

    def test_get_session_nonexistent_returns_404(self, client):
        resp = client.get("/api/v1/data/sessions/nonexistent-id")
        assert resp.status_code == 404

    def test_factor_data_paginated_shape(self, client, session_id):
        resp = client.get(f"/api/v1/data/sessions/{session_id}/factor")
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["session_id"] == session_id
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "page" in data
        assert data["page"] == 1
        assert "page_size" in data
        assert data["page_size"] == 100
        assert "total_rows" in data
        assert isinstance(data["total_rows"], int)

    def test_factor_data_pagination_params(self, client, session_id):
        resp = client.get(
            f"/api/v1/data/sessions/{session_id}/factor",
            params={"page": 1, "page_size": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["data"]) <= 10

    def test_price_data_paginated_shape(self, client, session_id):
        resp = client.get(f"/api/v1/data/sessions/{session_id}/prices")
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "page" in data
        assert "page_size" in data
        assert "total_rows" in data

    def test_preview_csv_shape(self, client, factor_csv):
        factor_csv.seek(0)
        resp = client.post(
            "/api/v1/data/preview",
            files={"file": ("factor.csv", factor_csv, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "columns" in data
        assert isinstance(data["columns"], list)
        assert "dtypes" in data
        assert isinstance(data["dtypes"], dict)
        assert "rows" in data
        assert isinstance(data["rows"], list)
        # Factor CSV has 30 days x 5 assets = 150 rows, but preview limits to 10
        assert len(data["rows"]) <= 10


class TestAnalysisContract:
    """Analysis endpoints must match AnalysisRunResponse / AnalysisStatusResponse / etc."""

    def test_analysis_run_response_shape(self, client, session_id, celery_mock):
        resp = client.post("/api/v1/analysis/run", json={
            "session_id": session_id,
            "config": {
                "periods": [1, 5, 10],
                "quantiles": 5,
                "filter_zscore": 20,
                "max_loss": 0.35,
                "long_short": True,
                "group_neutral": False,
            },
        })
        assert resp.status_code == 202
        data = resp.json()
        assert "analysis_id" in data
        assert isinstance(data["analysis_id"], str)
        assert "task_id" in data
        assert isinstance(data["task_id"], str)
        assert "status" in data
        assert data["status"] == "pending"

    def test_analysis_run_nonexistent_session_returns_404(self, client, celery_mock):
        resp = client.post("/api/v1/analysis/run", json={
            "session_id": "nonexistent-session-id",
            "config": {"periods": [1, 5, 10]},
        })
        assert resp.status_code == 404

    def test_analysis_status_shape(self, client, analysis_data):
        aid = analysis_data["analysis_id"]
        resp = client.get(f"/api/v1/analysis/{aid}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_id" in data
        assert data["analysis_id"] == aid
        assert "task_id" in data
        assert "status" in data
        assert "current_stage" in data
        assert "progress_pct" in data
        assert isinstance(data["progress_pct"], int)
        assert 0 <= data["progress_pct"] <= 100
        assert "message" in data
        assert "started_at" in data
        assert "completed_at" in data
        assert "error_message" in data

    def test_analysis_status_completed(self, client, analysis_data):
        aid = analysis_data["analysis_id"]
        resp = client.get(f"/api/v1/analysis/{aid}/status")
        data = resp.json()
        assert data["status"] == "completed"

    def test_analysis_nonexistent_returns_404(self, client):
        resp = client.get("/api/v1/analysis/nonexistent/status")
        assert resp.status_code == 404

    def test_analysis_results_shape(self, client, analysis_data):
        aid = analysis_data["analysis_id"]
        resp = client.get(f"/api/v1/analysis/{aid}/results")
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_id" in data
        assert data["analysis_id"] == aid
        assert "status" in data
        assert "config" in data
        assert "ic" in data
        assert "charts" in data

    def test_ic_results_shape(self, client, analysis_data):
        aid = analysis_data["analysis_id"]
        resp = client.get(f"/api/v1/analysis/{aid}/results/ic")
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_id" in data
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_returns_results_shape(self, client, analysis_data):
        aid = analysis_data["analysis_id"]
        resp = client.get(f"/api/v1/analysis/{aid}/results/returns")
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_id" in data
        assert "factor_returns" in data
        assert isinstance(data["factor_returns"], list)
        assert "returns_by_quantile" in data
        assert isinstance(data["returns_by_quantile"], list)
        assert "cumulative_returns" in data
        assert isinstance(data["cumulative_returns"], list)

    def test_alpha_beta_shape(self, client, analysis_data):
        aid = analysis_data["analysis_id"]
        resp = client.get(f"/api/v1/analysis/{aid}/results/alpha-beta")
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_id" in data
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_turnover_shape(self, client, analysis_data):
        aid = analysis_data["analysis_id"]
        resp = client.get(f"/api/v1/analysis/{aid}/results/turnover")
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_id" in data
        assert "turnover" in data
        assert isinstance(data["turnover"], list)
        assert "autocorrelation" in data
        assert isinstance(data["autocorrelation"], list)

    def test_summary_tables_shape(self, client, analysis_data):
        aid = analysis_data["analysis_id"]
        resp = client.get(f"/api/v1/analysis/{aid}/results/summary-tables")
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_id" in data
        assert "alpha_beta" in data
        assert "returns_by_quantile" in data
        assert "ic" in data


class TestChartContract:
    """Chart endpoint must return proper base64-encoded PNG responses."""

    CHART_TYPES = [
        "ic_time_series",
        "ic_histogram",
        "ic_qq_plot",
        "quantile_returns_bar",
        "cumulative_returns",
        "mean_quantile_spread",
        "quantile_turnover",
        "rank_autocorrelation",
    ]

    def test_chart_response_shape(self, client, analysis_data):
        aid = analysis_data["analysis_id"]
        resp = client.get(f"/api/v1/analysis/{aid}/results/charts/ic_time_series")
        assert resp.status_code == 200
        data = resp.json()
        assert "chart_type" in data
        assert data["chart_type"] == "ic_time_series"
        assert "image" in data
        assert isinstance(data["image"], str)
        assert data["image"].startswith("data:image/png;base64,")
        assert "format" in data
        assert data["format"] == "png"

    def test_all_chart_types_return_valid(self, client, analysis_data):
        aid = analysis_data["analysis_id"]
        for chart_type in self.CHART_TYPES:
            resp = client.get(
                f"/api/v1/analysis/{aid}/results/charts/{chart_type}"
            )
            # Chart may be 200 (cached/generated) or 404 (insufficient test data)
            # Both are valid contract responses
            if resp.status_code == 200:
                data = resp.json()
                assert data["chart_type"] == chart_type
                assert data["image"].startswith("data:image/png;base64,")
            elif resp.status_code == 404:
                data = resp.json()
                assert "detail" in data

    def test_unknown_chart_type_returns_400(self, client, analysis_data):
        aid = analysis_data["analysis_id"]
        resp = client.get(
            f"/api/v1/analysis/{aid}/results/charts/nonexistent_chart"
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data


class TestTaskContract:
    """Task endpoints must match TaskStatusResponse / TaskSummary."""

    def test_task_status_shape(self, client):
        # Use a fake task_id -- since broker is memory://,
        # it should still return a valid response shape
        resp = client.get("/api/v1/tasks/fake-task-id-123")
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert data["task_id"] == "fake-task-id-123"
        assert "status" in data
        assert isinstance(data["status"], str)

    def test_revoke_task_shape(self, client):
        resp = client.post("/api/v1/tasks/fake-task-id-123/revoke")
        assert resp.status_code == 202
        data = resp.json()
        assert "status" in data
        assert "task_id" in data

    def test_list_tasks_shape(self, client):
        resp = client.get("/api/v1/tasks/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestErrorContract:
    """All error responses must follow FastAPI's standard error shape."""

    def test_error_response_has_detail(self, client):
        endpoints = [
            "/api/v1/data/sessions/nonexistent",
            "/api/v1/upload/nonexistent/files",
            "/api/v1/analysis/nonexistent/status",
        ]
        for ep in endpoints:
            resp = client.get(ep)
            assert resp.status_code == 404
            body = resp.json()
            assert "detail" in body, f"Missing 'detail' in 404 response for {ep}"

    def test_400_error_has_detail(self, client, empty_csv):
        empty_csv.seek(0)
        resp = client.post(
            "/api/v1/upload/csv",
            files={"file": ("empty.csv", empty_csv, "text/csv")},
            data={"file_type": "factor"},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert "detail" in body
