"""Test fixtures and configuration for backend API contract tests."""

import io
import os
import tempfile
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def db_path():
    """Create a temporary DuckDB file path (fresh per test to avoid cross-test pollution)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(scope="session")
def raw_data_dir():
    """Create a temporary raw data directory."""
    path = tempfile.mkdtemp()
    yield path
    import shutil
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="function")
def app(db_path, raw_data_dir):
    """Create FastAPI app with test database and Celery overrides."""
    with patch("backend.app.config.settings.DB_PATH", db_path), \
         patch("backend.app.config.settings.RAW_DATA_DIR", raw_data_dir), \
         patch("backend.app.config.settings.CELERY_BROKER_URL", "memory://"), \
         patch("backend.app.config.settings.CELERY_RESULT_BACKEND", "cache+memory://"):

        from backend.app.main import create_app
        from backend.app.services.data_service import DataService
        from backend.app.dependencies import get_data_service

        test_app = create_app()
        ds = DataService(db_path)
        test_app.dependency_overrides[get_data_service] = lambda: ds

        yield test_app

        ds.close()
        test_app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """FastAPI TestClient bound to the test app (context-managed for lifespan)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def data_service(app):
    """Return the DataService instance used by the test app."""
    from backend.app.dependencies import get_data_service
    return app.dependency_overrides[get_data_service]()


# ── Sample CSV fixtures ──────────────────────────────────────────────

@pytest.fixture
def factor_csv():
    """Sample factor CSV data (long format: date, asset, factor_value)."""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=30, freq="D")
    rows = []
    for d in dates:
        for asset in ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]:
            rows.append({
                "date": d.strftime("%Y-%m-%d"),
                "asset": asset,
                "factor_value": round(np.random.normal(0, 1), 4),
            })
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf


@pytest.fixture
def prices_csv():
    """Sample prices CSV data (wide format: date + asset columns)."""
    np.random.seed(99)
    dates = pd.date_range("2023-01-01", periods=30, freq="D")
    base = {"AAPL": 150, "MSFT": 350, "GOOGL": 140, "AMZN": 130, "META": 200}
    data = {"date": [d.strftime("%Y-%m-%d") for d in dates]}
    for asset, b in base.items():
        prices = [b]
        for _ in range(len(dates) - 1):
            prices.append(round(prices[-1] * (1 + np.random.normal(0, 0.015)), 2))
        data[asset] = prices
    df = pd.DataFrame(data)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf


@pytest.fixture
def empty_csv():
    """Empty CSV file (header only)."""
    df = pd.DataFrame(columns=["date", "asset", "value"])
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf


# ── Session / Analysis fixtures ──────────────────────────────────────

@pytest.fixture
def session_id(client, factor_csv, prices_csv):
    """Upload factor + prices and return the session_id."""
    # Upload factor
    factor_csv.seek(0)
    resp = client.post(
        "/api/v1/upload/csv",
        files={"file": ("factor.csv", factor_csv, "text/csv")},
        data={"file_type": "factor"},
    )
    assert resp.status_code == 201
    sid = resp.json()["session_id"]

    # Upload prices to same session
    prices_csv.seek(0)
    resp = client.post(
        "/api/v1/upload/csv",
        files={"file": ("prices.csv", prices_csv, "text/csv")},
        data={"file_type": "prices", "session_id": sid},
    )
    assert resp.status_code == 201

    return sid


@pytest.fixture
def analysis_data(data_service, session_id):
    """Seed a completed analysis run with sample results data."""
    # Create analysis run
    analysis_id = data_service.create_analysis_run(session_id)
    data_service.save_analysis_config(analysis_id, {
        "periods": [1, 5, 10],
        "quantiles": 5,
        "filter_zscore": 20,
        "max_loss": 0.35,
        "zero_aware": False,
        "cumulative_returns": True,
        "long_short": True,
        "group_neutral": False,
        "by_group": False,
    })
    data_service.link_task(analysis_id, "mocked-task-id-001")

    # IC data
    dates = pd.date_range("2023-01-05", periods=5, freq="D")
    ic_records = []
    for d in dates:
        for p in ["1D", "5D", "10D"]:
            ic_records.append({
                "analysis_id": analysis_id,
                "date": d,
                "period": p,
                "ic_value": round(np.random.uniform(-0.05, 0.05), 4),
            })
    ic_df = pd.DataFrame(ic_records)

    # Save IC data (needs pivot with date index, period columns)
    ic_pivot = ic_df.pivot_table(index="date", columns="period",
                                  values="ic_value", aggfunc="first")
    data_service.save_ic_results(analysis_id, ic_pivot)

    # Factor returns
    ret_dates = pd.date_range("2023-01-05", periods=5, freq="D")
    ret_records = []
    for d in ret_dates:
        for p in ["1D", "5D", "10D"]:
            ret_records.append({
                "analysis_id": analysis_id,
                "date": d,
                "period": p,
                "return_value": round(np.random.uniform(-0.02, 0.02), 4),
            })
    ret_df = pd.DataFrame(ret_records)
    ret_pivot = ret_df.pivot_table(index="date", columns="period",
                                    values="return_value", aggfunc="first")
    data_service.save_factor_returns(analysis_id, ret_pivot)

    # Alpha / Beta
    ab_data = pd.DataFrame({
        "metric": ["Alpha", "Beta"],
        "1D": [0.0001, 0.95],
        "5D": [0.0005, 0.96],
        "10D": [0.001, 0.97],
    }).set_index("metric")
    data_service.save_alpha_beta(analysis_id, ab_data)

    # Mean return by quantile
    np.random.seed(42)
    mr_records = []
    for q in range(1, 6):
        for p in ["1D", "5D", "10D"]:
            mr_records.append({
                "factor_quantile": q,
                "group_name": None,
                "period": p,
                "mean_return": round(np.random.uniform(-0.01, 0.01), 4),
            })
    mr_df = pd.DataFrame(mr_records)
    mr_pivot = mr_df.pivot_table(
        index="factor_quantile", columns="period",
        values="mean_return", aggfunc="first"
    )
    data_service.save_mean_return_by_quantile(analysis_id, mr_pivot)

    # Cumulative returns
    cum_dates = pd.date_range("2023-01-05", periods=10, freq="D")
    cum_vals = np.cumsum(np.random.uniform(-0.005, 0.005, 10)) + 1
    cum_series = pd.Series(cum_vals, index=pd.date_range("2023-01-05", periods=10, freq="D"))
    data_service.save_cumulative_returns(analysis_id, cum_series)

    # Mean return spread
    spread_dates = pd.date_range("2023-01-05", periods=5, freq="D")
    spread_data = pd.DataFrame({
        "1D": np.random.uniform(-0.01, 0.01, 5),
        "5D": np.random.uniform(-0.01, 0.01, 5),
        "10D": np.random.uniform(-0.01, 0.01, 5),
    }, index=spread_dates)
    data_service.save_mean_return_spread(analysis_id, spread_data)

    # Quantile turnover
    turn_dates = pd.date_range("2023-01-06", periods=4, freq="D")
    turn_dict = {}
    for q in range(1, 6):
        turn_dict[q] = pd.Series(
            np.random.uniform(0.1, 0.5, 4), index=turn_dates
        )
    data_service.save_quantile_turnover(analysis_id, turn_dict)

    # Autocorrelation
    acf_dates = pd.date_range("2023-01-06", periods=4, freq="D")
    acf_series = pd.Series(np.random.uniform(0.5, 0.95, 4), index=acf_dates)
    data_service.save_autocorrelation(analysis_id, acf_series)

    # Mark analysis as completed
    data_service.update_analysis_status(analysis_id, "completed")

    # Save a chart
    data_service.save_chart(analysis_id, "ic_time_series",
                            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")

    return {"analysis_id": analysis_id, "session_id": session_id}


@pytest.fixture
def celery_mock():
    """Mock Celery task dispatch (run_analysis is lazily imported in the endpoint)."""
    with patch("backend.tasks.analysis_tasks.run_analysis.delay") as mock_delay:
        mock_delay.return_value = MagicMock(id="mocked-celery-task-id")
        yield mock_delay
