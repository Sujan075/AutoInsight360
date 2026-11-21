"""
AutoInsight360 - Import Schemas
=================================
Pydantic schemas for dynamic CSV/ZIP dataset ingestion, preview,
validation feedback, and transactional commit.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """Represents a specific validation issue (error or warning) during import."""
    file: str
    row: Optional[int] = None
    field: Optional[str] = None
    severity: str = Field(..., description="'error' (blocks row) or 'warning'")
    message: str


class EntityImportSummary(BaseModel):
    """Per-entity counts and sample rows for the import preview."""
    entity: str
    file_name: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    warning_rows: int
    sample_preview: List[Dict[str, Any]] = []


class ImportPreviewResponse(BaseModel):
    """Response returned after parsing and validating an uploaded ZIP bundle."""
    session_id: str
    can_commit: bool
    total_files_found: int
    files_processed: List[str]
    summary: List[EntityImportSummary]
    issues: List[ValidationIssue]
    total_accepted_rows: int
    total_rejected_rows: int
    message: str


class ImportCommitRequest(BaseModel):
    """Request payload to commit a previously validated import session."""
    session_id: str


class ImportCommitResponse(BaseModel):
    """Response returned after successfully committing imported records."""
    success: bool
    message: str
    imported_counts: Dict[str, int]
    committed_at: str


class TemplateFileInfo(BaseModel):
    """Information regarding a downloadable canonical CSV template."""
    filename: str
    entity: str
    description: str
    required_columns: List[str]
    optional_columns: List[str]
