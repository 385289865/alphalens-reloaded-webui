"""LiteFS-aware database routing middleware.

Routes read queries to the LiteFS replica and write queries to the primary.
Used as a FastAPI dependency — depends on request method.
"""

from fastapi import Request
from backend.app.perfact.metadata_db import MetadataDB
from backend.app.config import settings

# Singleton instances
_primary_db: MetadataDB = None
_replica_db: MetadataDB = None


def get_metadata_db(request: Request = None) -> MetadataDB:
    """Return MetadataDB instance — primary for writes, replica for reads.

    LiteFS provides a FUSE filesystem where the replica is at
    METADATA_REPLICA_DB_PATH. Reads go to the replica, writes to the primary.
    If no replica is configured, falls back to primary for all operations.
    """
    global _primary_db, _replica_db

    if _primary_db is None:
        _primary_db = MetadataDB(settings.METADATA_DB_PATH, read_only=False)

    if request and request.method in ("GET", "OPTIONS", "HEAD"):
        # Check if replica is available
        replica_path = settings.METADATA_REPLICA_DB_PATH
        if replica_path and replica_path != settings.METADATA_DB_PATH:
            import os
            if os.path.exists(replica_path):
                if _replica_db is None:
                    _replica_db = MetadataDB(replica_path, read_only=True)
                return _replica_db

    return _primary_db
