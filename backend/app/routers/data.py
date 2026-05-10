"""Data router - session and data browsing endpoints."""

from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File

from backend.app.models.schemas import (
    SessionSummary, SessionDetail, PreviewResponse, PaginatedData,
)
from backend.app.services.data_service import DataService
from backend.app.dependencies import get_data_service

router = APIRouter()


@router.get("/sessions", response_model=List[SessionSummary])
async def list_sessions(
    data_service: DataService = Depends(get_data_service),
):
    """List all upload sessions."""
    sessions = data_service.list_sessions()
    return [
        SessionSummary(
            session_id=s["session_id"],
            name=s.get("name"),
            created_at=s["created_at"],
            status=s["status"],
            asset_count=s.get("asset_count", 0),
            date_range_start=s.get("date_range_start"),
            date_range_end=s.get("date_range_end"),
            analysis_count=int(s.get("analysis_count", 0)),
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    data_service: DataService = Depends(get_data_service),
):
    """Get full session details."""
    session = data_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    files = data_service.get_session_files(session_id)
    return SessionDetail(
        session_id=session["session_id"],
        name=session.get("name"),
        description=session.get("description"),
        created_at=session["created_at"],
        status=session["status"],
        files=files,
        date_range_start=session.get("date_range_start"),
        date_range_end=session.get("date_range_end"),
        asset_count=int(session.get("asset_count", 0)),
    )


@router.get("/sessions/{session_id}/factor", response_model=PaginatedData)
async def get_factor_data(
    session_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=10000),
    asset: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    data_service: DataService = Depends(get_data_service),
):
    """Get paginated factor data from a session."""
    session = data_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    query = "SELECT * FROM factor_values WHERE session_id = ?"
    params = [session_id]

    if asset:
        query += " AND asset = ?"
        params.append(asset)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    # Get total count
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    total = data_service.conn.execute(count_query, params).fetchone()[0]

    # Paginate
    offset = (page - 1) * page_size
    query += " ORDER BY date, asset LIMIT ? OFFSET ?"
    params.extend([page_size, offset])

    result = data_service.conn.execute(query, params).fetchdf()
    return PaginatedData(
        session_id=session_id,
        data=result.to_dict("records") if not result.empty else [],
        page=page,
        page_size=page_size,
        total_rows=total,
    )


@router.get("/sessions/{session_id}/prices", response_model=PaginatedData)
async def get_price_data(
    session_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=10000),
    asset: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    data_service: DataService = Depends(get_data_service),
):
    """Get paginated price data from a session."""
    session = data_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    query = "SELECT * FROM price_data WHERE session_id = ?"
    params = [session_id]

    if asset:
        query += " AND asset = ?"
        params.append(asset)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    total = data_service.conn.execute(count_query, params).fetchone()[0]

    offset = (page - 1) * page_size
    query += " ORDER BY date, asset LIMIT ? OFFSET ?"
    params.extend([page_size, offset])

    result = data_service.conn.execute(query, params).fetchdf()
    return PaginatedData(
        session_id=session_id,
        data=result.to_dict("records") if not result.empty else [],
        page=page,
        page_size=page_size,
        total_rows=total,
    )


@router.post("/preview", response_model=PreviewResponse)
async def preview_csv(
    file: UploadFile = File(...),
    rows: int = Query(10, le=100),
    data_service: DataService = Depends(get_data_service),
):
    """Preview a CSV file before uploading to a session."""
    import pandas as pd
    import io

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    return PreviewResponse(
        columns=list(df.columns),
        dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
        rows=df.head(rows).fillna("").to_dict("records"),
        total_rows_preview=min(rows, len(df)),
    )
