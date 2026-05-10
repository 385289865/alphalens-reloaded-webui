"""Upload router - CSV file upload endpoints."""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException

from backend.app.models.schemas import UploadResponse, UploadFileInfo, SessionFilesResponse
from backend.app.models.enums import FileType
from backend.app.services.data_service import DataService
from backend.app.dependencies import get_data_service

router = APIRouter()


@router.post("/csv", response_model=UploadResponse, status_code=201)
async def upload_csv(
    file: UploadFile = File(...),
    file_type: str = Form(...),
    session_id: Optional[str] = Form(None),
    data_service: DataService = Depends(get_data_service),
):
    """Upload a CSV file for analysis.

    Supports factor, prices, and groups file types.
    Creates a new session if session_id is not provided.
    """
    if file_type not in (ft.value for ft in FileType):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file_type. Must be one of: {[ft.value for ft in FileType]}",
        )

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    # Create session if new
    if not session_id:
        session_id = data_service.create_session(
            name=f"Upload - {file.filename}",
        )

    # Read file content
    content = await file.read()

    # Parse CSV with pandas
    import pandas as pd
    import io
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    # Save raw file to disk
    raw_dir = os.path.join(
        data_service._get_raw_data_dir(),
        session_id,
    )
    os.makedirs(raw_dir, exist_ok=True)
    storage_path = os.path.join(raw_dir, f"{file_type}.csv")
    with open(storage_path, "wb") as f:
        f.write(content)

    # Ingest data into DuckDB
    try:
        if file_type == "factor":
            rows = data_service.ingest_factor_csv(session_id, df)
        elif file_type == "prices":
            rows, asset_count = data_service.ingest_prices_csv(session_id, df)
            data_service.update_session_stats(
                session_id=session_id,
                row_count_factor=0,
                row_count_prices=rows,
                date_range_start=df.iloc[:, 0].min() if hasattr(df.iloc[:, 0], 'min') else None,
                date_range_end=df.iloc[:, 0].max() if hasattr(df.iloc[:, 0], 'max') else None,
                asset_count=asset_count,
            )
        elif file_type == "groups":
            data_service.ingest_groups_csv(session_id, df)
            rows = len(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to ingest data: {e}")

    # Record raw file metadata
    file_id = data_service.save_raw_file(
        session_id=session_id,
        file_type=file_type,
        original_filename=file.filename,
        storage_path=storage_path,
        file_size_bytes=len(content),
        row_count=len(df),
        column_count=len(df.columns),
    )

    return UploadResponse(
        session_id=session_id,
        file_id=file_id,
        file_type=file_type,
        rows_ingested=rows,
        columns=list(df.columns),
    )


@router.get("/{session_id}/files", response_model=SessionFilesResponse)
async def list_session_files(
    session_id: str,
    data_service: DataService = Depends(get_data_service),
):
    """List all files uploaded in a session."""
    session = data_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    files = data_service.get_session_files(session_id)
    return SessionFilesResponse(
        session_id=session_id,
        files=[UploadFileInfo(**f) for f in files],
    )


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    data_service: DataService = Depends(get_data_service),
):
    """Delete a session and all its data."""
    session = data_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    data_service.delete_session(session_id)

    # Clean up raw files on disk
    import shutil
    raw_dir = os.path.join(data_service._get_raw_data_dir(), session_id)
    if os.path.exists(raw_dir):
        shutil.rmtree(raw_dir)
