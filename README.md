# AutoInsight360

**Automotive Customer 360 Intelligence Agent**

An AI-powered customer intelligence system that provides unified automotive customer information and evidence-backed insights using a locally running LLM.

---

## Current Status

**Phase 2.1 — Dynamic Data Ingestion, UI Corrections & End-to-End Validation** ✅ Complete

| Phase | Description | Status |
|---|---|---|
| Phase 0 | Project Setup & Specification | ✅ Complete |
| Phase 1 | Database Foundation (SQLite + SQLAlchemy 2.0) | ✅ Complete |
| Phase 1.1 | Seed Data Idempotency Audit | ✅ Complete |
| Phase 2 | Full-Stack Application (FastAPI + Vanilla JS + Llama 3.1) | ✅ Complete |
| Phase 2.1 | Dynamic Data Ingestion, UI Corrections & E2E Validation | ✅ Complete |
| Phase 3 | Advanced Multi-Agent Intelligence Workflows | 🔜 Planned |

---

## Core Features

- **Dynamic Automotive Data Ingestion**: Upload, validate, preview, and transactionally commit external automotive datasets via canonical CSV ZIP archives.
- **Downloadable Canonical CSV Templates**: Pre-configured CSV templates for all 7 entities (`customers.csv`, `vehicles.csv`, `dealers.csv`, `transactions.csv`, `service_visits.csv`, `loyalty_events.csv`, `customer_reviews.csv`).
- **Source-ID-to-Database-ID Mapping**: Relational mapping preserves cross-entity foreign keys regardless of internal database primary key auto-increments.
- **Multi-Stage Validation & Safe Transactions**: Atomic rollbacks prevent partial writes on failure; row-by-row error and warning diagnostics.
- **Genuine System Status Badges**: Primary header dynamically reports `Database: Connected` and `Llama 3.1: Ready`, moving detailed counts to the Import / Admin panel.
- **Unified Customer 360 Lookup**: Demographics, contact preferences, segment, status.
- **Historical Customer Value (CLTV)**: Calculated from completed vehicle purchases, service payments, parts, and accessories.
- **Vehicle Ownership**: Full specifications, VIN, fuel type, mileage, primary vehicle designation.
- **Automotive Service History**: Maintenance records, service types, costs, dealer associations, warranty coverage, and technician notes.
- **Loyalty Points & History**: Real-time points balance, points earned, points redeemed, and chronological audit log.
- **Customer Reviews & Feedback**: Star ratings (1–5★), feedback text, dealer/vehicle links, and verified customer badges.
- **Local AI Customer Insights Assistant**: Natural-language intelligence assistant powered by local Ollama (Llama 3.1).
- **Evidence-Grounded AI Responses**: Cites specific database record identifiers (`[Vehicle VIN: ...]`, `[Transaction Ref: ...]`, `[Service Visit #...]`, `[Review #...]`).
- **Security Guardrails**: Read-only database access via approved Python services; no arbitrary SQL execution; input validation and query length constraints.
- **Audit Logging**: Structured query responses with cited evidence records and model metadata.

---

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.13 |
| Web Framework | FastAPI | 0.115.11 |
| ASGI Server | Uvicorn | 0.34.0 |
| Data Validation | Pydantic v2 | 2.10.6 |
| Multipart Uploads | python-multipart | 0.0.34 |
| Database | SQLite (MVP) | `data/autoinsight360.db` |
| ORM | SQLAlchemy | 2.0.40 |
| AI / LLM | Ollama (Local) | 0.40.16 |
| Foundation Model | Llama 3.1 | `llama3.1:latest` (8B) |
| Frontend | HTML5, Modern CSS3, Vanilla JavaScript | Responsive SPA |
| Testing | pytest | 8.3.4 (77 tests passed) |

---

## Project Structure

```text
AutoInsight360/
├── backend/
│   └── app/
│       ├── main.py                # FastAPI app, API routes, static file serving
│       ├── database/
│       │   ├── __init__.py        # Database package exports
│       │   ├── base.py            # SQLAlchemy DeclarativeBase
│       │   ├── connection.py      # Engine, SessionLocal, get_db()
│       │   ├── init_db.py         # Table creation & schema verification
│       │   ├── models.py          # ORM models (7 entities)
│       │   └── seed_data.py       # Reproducible idempotent synthetic data generator
│       ├── schemas/
│       │   ├── __init__.py        # Schemas package exports
│       │   └── customer_schemas.py# Pydantic request & response schemas
│       ├── services/
│       │   ├── __init__.py        # Services package exports
│       │   └── customer_service.py# Customer search, Customer 360 profile & CLTV
│       └── agents/
│           ├── __init__.py        # Agents package exports
│           └── customer_agent.py  # Evidence-grounded Ollama Llama 3.1 agent
├── data/
│   └── autoinsight360.db          # SQLite database (git-ignored)
├── docs/
│   └── ERD.md                     # Entity Relationship Diagram
├── frontend/
│   ├── index.html                 # Single-page dashboard application
│   └── static/
│       ├── css/
│       │   └── styles.css         # Modern automotive stylesheet
│       └── js/
│           └── app.js             # Client state management & fetch() integration
├── scripts/
│   ├── init_db.py                 # Database initialisation & reset script
│   └── verify_db.py               # Database verification script
├── tests/
│   ├── conftest.py                # pytest fixtures (in-memory SQLite)
│   ├── test_database.py           # Database schema, counts & idempotency tests (50 tests)
│   └── test_api.py                # FastAPI endpoints & full-stack tests (16 tests)
├── .gitignore
├── project.md                     # Master specification (source of truth)
└── README.md
```

---

## Setup & Quickstart

### Prerequisites

- Python 3.13
- Git
- Ollama with `llama3.1:latest` (optional for AI assistant, fallback provided if offline)

### 1. Activate Virtual Environment & Install Dependencies

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install fastapi "uvicorn[standard]" pydantic httpx sqlalchemy pytest faker
```

### 2. Database Initialisation (If setting up fresh)

```powershell
# Initialise database and seed data (idempotent, safe to rerun)
python scripts/init_db.py

# Verify database integrity
python scripts/verify_db.py
```

### 3. Launch the Application

```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open your browser to:

👉 **`http://localhost:8000`**

---

## API Endpoints

Interactive Swagger documentation is available at **`http://localhost:8000/docs`**.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check: SQLite connection status, table counts, and Ollama status. |
| `GET` | `/api/customers/search?q={query}&limit={limit}` | Search customers by name, customer ID, email, phone, or VIN. |
| `GET` | `/api/customers/{customer_id}/360` | Comprehensive Customer 360 profile with verified CLTV, vehicles, services, transactions, loyalty, and reviews. |
| `POST` | `/api/agent/query` | Natural-language customer intelligence query powered by Ollama (Llama 3.1) with database evidence grounding. |
| `GET` | `/api/import/templates` | Catalog of canonical CSV template definitions. |
| `GET` | `/api/import/templates/download` | Download bundled ZIP containing all canonical CSV templates. |
| `GET` | `/api/import/templates/{filename}` | Download individual canonical CSV template file. |
| `POST` | `/api/import/preview` | Upload and validate a dataset ZIP bundle. Generates preview statistics and staging session. |
| `POST` | `/api/import/commit` | Confirm and transactionally commit a validated import session into SQLite. |
| `GET` | `/` | Serves the single-page frontend application. |
| `GET` | `/static/*` | Serves CSS stylesheets and JavaScript client files. |

---

## Running Tests

Execute the complete test suite (77 tests covering database models, FK integrity, idempotency, API endpoints, CLTV calculation, dynamic ingestion, and AI agent queries):

```powershell
python -m pytest tests/ -v
```

### Test Suite Breakdown

| File | Tests | Coverage | Result |
|---|---|---|---|
| `tests/test_database.py` | 50 | Schema, record counts, data integrity, foreign keys, ORM traversal, Customer 360 queries, seed idempotency | ✅ 50 Passed |
| `tests/test_api.py` | 16 | `/api/health`, customer search, Customer 360 retrieval, CLTV calculation, error handling (404/400), AI agent queries, static file serving | ✅ 16 Passed |
| `tests/test_import.py` | 10 | Canonical template downloads, ZIP validation, multi-stage schema checking, FK resolution, preview, and transactional commit | ✅ 10 Passed |
| `tests/test_e2e_import.py` | 1 | Complete Task 7 E2E workflow: dataset ZIP ingestion -> DB verify -> search -> Customer 360 -> Ollama AI query with citations | ✅ 1 Passed |
| **Total** | **77** | Complete full-stack database, ingestion, API & AI coverage | **✅ 77 Passed (0 failed)** |

---

## Security & AI Guardrails

- **Read-Only Database Access**: The AI Agent and search APIs use read-only queries.
- **No Arbitrary SQL**: The AI Assistant receives structured data via approved Python services; no raw SQL execution is permitted.
- **Evidence-Grounded Answers**: The AI agent is instructed to cite verified record identifiers (`[Vehicle VIN: ...]`, `[Transaction Ref: ...]`, `[Service Visit #...]`, `[Review #...]`).
- **Input Constraints**: Customer IDs are validated as positive integers; questions are restricted to 3–500 characters.
- **Graceful Fallback**: If the local Ollama LLM is busy or offline, the system automatically provides an evidence-backed structured summary without failing.

---

## Data Policy

> **SYNTHETIC DATA DISCLAIMER**
>
> All customer data, vehicle records, dealer information, transactions, and reviews in this system are **entirely synthetic and fictitious**.
>
> - Customer names, emails, phone numbers, addresses and dates of birth are randomly generated.
> - Synthetic emails use the domain `@autoinsight.demo`.
> - Vehicle VINs are prefixed with `SYNTH-` and are not real vehicle identifiers.
> - Dealer phone numbers use the `555-` prefix.
> - No real personal information has been used or should ever be committed to this repository.
