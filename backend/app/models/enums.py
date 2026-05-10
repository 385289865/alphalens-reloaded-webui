from enum import Enum


class FileType(str, Enum):
    FACTOR = "factor"
    PRICES = "prices"
    GROUPS = "groups"


class TaskState(str, Enum):
    PENDING = "pending"
    RECEIVED = "received"
    STARTED = "started"
    PROGRESS = "progress"
    SUCCESS = "success"
    FAILURE = "failure"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
