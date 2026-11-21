"""
AutoInsight360 - Main FastAPI Application
===========================================
Entry point for the Automotive Customer 360 Intelligence backend API.

Endpoints:
- GET  /api/health
- GET  /api/customers/search
- GET  /api/customers/{customer_id}/360
- POST /api/agent/query
- Static frontend mounted at / and /static
"""

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.app.agents.customer_agent import check_ollama_status, query_customer_agent
from backend.app.database.connection import get_db
from backend.app.schemas.customer_schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    Customer360Response,
    CustomerSummaryResponse,
    HealthCheckResponse,
)
from backend.app.schemas.import_schemas import (
    ImportCommitRequest,
    ImportCommitResponse,
    ImportPreviewResponse,
    TemplateFileInfo,
)
from backend.app.services.customer_service import (
    get_customer_360,
    get_system_health,
    search_customers,
)
from backend.app.services.import_service import (
    commit_import_session,
    get_template_catalog,
    process_upload_and_preview,
)

logger = logging.getLogger("autoinsight360")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# ---------------------------------------------------------------------------
# FastAPI Application Factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AutoInsight360 — Customer Intelligence API",
    description="Automotive Customer 360 Intelligence Agent API with local Ollama Llama 3.1",
    version="2.0.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve project paths
BASE_DIR = Path(__file__).resolve().parents[2]  # AutoInsight360/
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "data" / "templates"


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthCheckResponse, tags=["System"])
def api_health(db: Session = Depends(get_db)):
    """Health check endpoint: verifies SQLite database and local Ollama model."""
    ollama_info = check_ollama_status()
    health = get_system_health(
        db,
        model_available=ollama_info["model_available"],
        model_name=ollama_info["model"],
    )
    return health


@app.get("/api/customers/search", response_model=List[CustomerSummaryResponse], tags=["Customers"])
def api_search_customers(
    q: Optional[str] = Query(None, description="Search term: ID, name, email, phone, or VIN"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    db: Session = Depends(get_db),
):
    """
    Search customers by name, customer ID, email, phone, or VIN.
    If q is omitted, returns the top customers ordered by ID.
    """
    results = search_customers(db=db, query=q, limit=limit)
    return results


@app.get(
    "/api/customers/{customer_id}/360",
    response_model=Customer360Response,
    tags=["Customers"],
)
def api_get_customer_360(
    customer_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve the comprehensive Customer 360 profile including:
    - Customer demographics and segment
    - Historical CLTV (Customer Lifetime Value) metrics
    - Vehicle ownership records
    - Transaction history
    - Automotive service history
    - Loyalty events and points balance
    - Customer reviews and sentiment
    """
    if customer_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer ID must be a positive integer.",
        )

    profile = get_customer_360(db=db, customer_id=customer_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} was not found.",
        )

    return profile


@app.post(
    "/api/agent/query",
    response_model=AgentQueryResponse,
    tags=["AI Agent"],
)
def api_query_agent(
    payload: AgentQueryRequest,
    db: Session = Depends(get_db),
):
    """
    Ask natural-language questions about a specific customer.
    The AI Agent retrieves verified customer records from SQLite and
    prompts local Ollama (Llama 3.1) with strict evidence-grounding constraints.
    """
    if payload.customer_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer ID must be a positive integer.",
        )

    if not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must not be empty.",
        )

    response = query_customer_agent(
        db=db,
        customer_id=payload.customer_id,
        question=payload.question.strip(),
    )
    return response


# ---------------------------------------------------------------------------
# Dynamic Dataset Ingestion & Template Routes
# ---------------------------------------------------------------------------

@app.get("/api/import/templates", response_model=List[TemplateFileInfo], tags=["Data Ingestion"])
def api_get_templates():
    """Return catalog of canonical CSV templates."""
    return get_template_catalog()


@app.get("/api/import/templates/download", tags=["Data Ingestion"])
def api_download_all_templates():
    """Download bundled ZIP containing all canonical CSV templates."""
    zip_path = TEMPLATES_DIR / "AutoInsight360_CSV_Templates.zip"
    if not zip_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template bundle not found.",
        )
    return FileResponse(
        path=str(zip_path),
        filename="AutoInsight360_CSV_Templates.zip",
        media_type="application/zip",
    )


@app.get("/api/import/templates/{filename}", tags=["Data Ingestion"])
def api_download_template_file(filename: str):
    """Download a single canonical CSV template file."""
    clean_name = Path(filename).name
    target = TEMPLATES_DIR / clean_name
    if not target.exists() or not clean_name.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{filename}' not found.",
        )
    return FileResponse(
        path=str(target),
        filename=clean_name,
        media_type="text/csv",
    )


@app.post("/api/import/preview", response_model=ImportPreviewResponse, tags=["Data Ingestion"])
async def api_preview_import(
    file: UploadFile = File(..., description="ZIP bundle containing canonical CSV files"),
    db: Session = Depends(get_db),
):
    """
    Upload and preview a ZIP bundle containing automotive customer datasets.
    Performs complete schema, type, and cross-entity foreign key validation.
    Returns preview summary, validation issues, and a staging session_id.
    """
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a .zip archive.",
        )

    content = await file.read()
    try:
        preview = process_upload_and_preview(zip_bytes=content, db=db)
        return preview
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Unexpected error during import preview: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating import archive: {e}",
        )


@app.post("/api/import/commit", response_model=ImportCommitResponse, tags=["Data Ingestion"])
def api_commit_import(
    payload: ImportCommitRequest,
    db: Session = Depends(get_db),
):
    """
    Confirm and commit a previously validated import session into SQLite.
    Applies transactional integrity: rolls back completely on any failure.
    """
    if not payload.session_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID is required.",
        )

    try:
        result = commit_import_session(session_id=payload.session_id, db=db)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Unexpected error during import commit: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit import: {e}",
        )


# ---------------------------------------------------------------------------
# Static Frontend Serving
# ---------------------------------------------------------------------------

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend_index():
    """Serve the single-page frontend application."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "AutoInsight360 API is running. Frontend index.html not yet installed."}
