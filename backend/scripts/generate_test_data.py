"""Generate synthetic test data for Alphalens WebUI.

Produces a CSV dataset using stock price as a cross-sectional factor.
The factor value at each date is the stock's closing price — we test
whether price level predicts forward returns across assets.

Dataset: 5 assets × 252 trading days = 1,260 rows
Output:
  - factor.csv  (long format: date, asset, factor_value)
  - prices.csv  (wide format: date, ticker1, ticker2, ...)
"""

import os
from pathlib import Path
from typing import Tuple
import numpy as np
import pandas as pd


# ── Asset configuration ─────────────────────────────────────────────

ASSETS = {
    "AAPL": {"init_price": 185.0, "vol": 0.25},
    "MSFT": {"init_price": 370.0, "vol": 0.22},
    "GOOGL": {"init_price": 140.0, "vol": 0.23},
    "AMZN": {"init_price": 155.0, "vol": 0.30},
    "JPM": {"init_price": 170.0, "vol": 0.20},
}

ANNUAL_DRIFT = 0.10  # 10% annualised drift for all assets
TRADING_DAYS = 252


def generate_price_factor_dataset(
    seed: int = 42,
    n_assets: int = 5,
    n_days: int = 252,
    output_dir: str = "db/test_data",
) -> Tuple[Path, Path]:
    """Generate a price-as-factor test dataset.

    Creates two CSV files:
      - factor.csv  (long format, n_assets × n_days rows)
      - prices.csv  (wide format, n_days rows)

    Parameters
    ----------
    seed : int
        Random seed for reproducibility (default 42).
    n_assets : int
        Number of assets to include (default 5).
    n_days : int
        Number of trading days (default 252).
    output_dir : str
        Directory for output CSV files (default 'db/test_data').

    Returns
    -------
    tuple[Path, Path]
        Paths to (factor.csv, prices.csv).
    """
    rng = np.random.default_rng(seed)

    # Use only the first n_assets from the configuration
    tickers = list(ASSETS.keys())[:n_assets]

    # Generate trading calendar (US business days 2024)
    dates = pd.bdate_range(start="2024-01-01", end="2024-12-31", freq="B")
    # Trim to exactly n_days
    if len(dates) > n_days:
        dates = dates[:n_days]
    elif len(dates) < n_days:
        # Pad forward if needed
        extra = pd.bdate_range(start=dates[-1] + pd.Timedelta(days=1), periods=n_days - len(dates), freq="B")
        dates = dates.append(extra)
    n_days_actual = len(dates)

    # Generate prices via geometric Brownian motion
    mu = ANNUAL_DRIFT / TRADING_DAYS         # daily drift
    price_array = np.zeros((n_days_actual, n_assets))

    for i, ticker in enumerate(tickers):
        cfg = ASSETS[ticker]
        sigma = cfg["vol"] / np.sqrt(TRADING_DAYS)  # daily volatility
        p = cfg["init_price"]

        for t in range(n_days_actual):
            price_array[t, i] = round(p, 2)
            # GBM step: p_{t+1} = p_t * exp(μ + σ * ε)
            eps = float(rng.normal(0, 1))
            p = p * np.exp(mu + sigma * eps)

    # Build DataFrames
    # --- Prices (wide format) ---
    prices_df = pd.DataFrame(price_array, columns=tickers)
    prices_df.insert(0, "date", dates.date)
    # Ensure date is string YYYY-MM-DD
    prices_df["date"] = prices_df["date"].astype(str)

    # --- Factor (long format: melt prices) ---
    factor_df = prices_df.melt(
        id_vars=["date"],
        var_name="asset",
        value_name="factor_value",
    )
    factor_df = factor_df[["date", "asset", "factor_value"]]

    # Ensure output directory exists
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    factor_csv = out_path / "factor.csv"
    prices_csv = out_path / "prices.csv"

    factor_df.to_csv(factor_csv, index=False)
    prices_df.to_csv(prices_csv, index=False)

    print(f"Generated factor CSV:  {factor_csv}  ({len(factor_df):,} rows, {list(factor_df.columns)})")
    print(f"Generated prices CSV:  {prices_csv}  ({len(prices_df):,} rows, {list(prices_df.columns)})")
    print(f"Assets: {', '.join(tickers)}")
    print(f"Date range: {dates[0].date()} to {dates[-1].date()}")

    return factor_csv, prices_csv


def load_csv_to_dataframes(output_dir: str = "db/test_data") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load generated CSV files back into DataFrames.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        (factor_df, prices_df)
    """
    out_path = Path(output_dir)
    factor_df = pd.read_csv(out_path / "factor.csv")
    prices_df = pd.read_csv(out_path / "prices.csv")
    # Parse dates
    factor_df["date"] = pd.to_datetime(factor_df["date"])
    prices_df["date"] = pd.to_datetime(prices_df["date"])
    return factor_df, prices_df


if __name__ == "__main__":
    generate_price_factor_dataset()
