"""Request and response schemas for admin API."""

from datetime import datetime
from typing import Optional, Any
from ninja import Schema


class TaskResponseSchema(Schema):
    """Response schema for successful task trigger."""
    success: bool
    message: str
    data: dict[str, Any]
    timestamp: datetime


class ErrorSchema(Schema):
    """Response schema for errors."""
    error: str
    detail: Optional[str] = None


class HealthCheckSchema(Schema):
    """Response schema for health check endpoint."""
    status: str
    timestamp: datetime
    version: str = "1.0"
