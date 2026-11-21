# AutoInsight360

**Automotive Customer 360 Intelligence Agent**

An AI-powered customer intelligence system that retrieves automotive customer data and generates evidence-backed insights using a locally running LLM.

---

## Project Status

**Phase 2.2 — Judge Feedback Implementation: INR, Service History & Annual Loyalty** ✅ Complete

| Phase | Description | Status |
|---|---|---|
| Phase 0 | Project Setup & Specification | ✅ Complete |
| Phase 1 | Database Foundation (SQLite + SQLAlchemy 2.0) | ✅ Complete |
| Phase 1.1 | Seed Data Idempotency Audit | ✅ Complete |
| Phase 2 | Full-Stack Application (FastAPI + Vanilla JS + Llama 3.1) | ✅ Complete |
| Phase 2.1 | Dynamic Data Ingestion, UI Corrections & E2E Validation | ✅ Complete |
| Phase 2.2 | Judge Feedback Implementation (INR, Service History, 2026 Loyalty) | ✅ Complete |
| Phase 3 | Advanced Multi-Agent Intelligence Workflows | 🔜 Planned |

---

## Core Features

- **Indian Rupee (INR ₹) Standardisation**: Standardised all financial presentations to Indian Rupees across CLTV, transactions, service/labour/parts costs, import previews, and AI responses using authentic Indian numbering grouping (`₹1,45,000.00`). Supported by an explicit currency policy with RBI benchmark conversion (1 USD = ₹84.00) and unsupported foreign currency rejection.
- **Detailed Service History**: Granular automotive service records with optional customer complaint, technical diagnosis, work performed, service completion status, parts cost, labour cost, odometer reading, and next service date, backed by backward-compatible CSV ingestion and interactive expandable UI accordions.
- **2026 Annual Loyalty Points Program & Birthday Bonus**: Year-isolated loyalty accounting featuring 100 points per completed 2026 service visit, 500 birthday bonus points awarded for birthdays occurring in 2026, dynamic annual balance calculation (`2026 Visits + 2026 Birthday - 2026 Redeemed`), and controlled point redemption via API and modal UI.
- **Dynamic Automotive Data Ingestion**: Upload, validate, preview, and transactionally commit external automotive datasets via canonical CSV ZIP archives.
- **Downloadable CSV Templates**: Pre-packaged CSV templates for all 7 entities (`customers`, `vehicles`, `dealers`, `transactions`, `service_visits`, `loyalty_events`, `customer_reviews`).
- **Source-ID-to-Database-ID Mapping**: Relational mapping preserves cross-entity foreign keys regardless of internal database primary key auto-increments.
- **Multi-Stage Validation & Safe Transactions**: Atomic rollbacks prevent partial writes on failure; row-by-row error and warning diagnostics.
- **Genuine System Status Badges**: Primary header dynamically reports `Database: Connected`, `Currency: INR (₹)`, and `Llama 3.1: Ready`.
- **Unified Customer 360 Profile**: Demographics, contact preferences, customer segment, account status.
- **Historical Customer Lifetime Value (CLTV)**: Calculated from actual completed vehicle purchases, service payments, parts, and accessories in INR.
- **Vehicle Ownership Records**: Complete specifications (VIN, year, make, model, trim, fuel type, mileage, primary vehicle designation).
- **Customer Reviews & Feedback**: Star ratings (1–5★), feedback text, dealer/vehicle links, and verified customer badges.
- **Local AI Customer Insights Assistant**: Natural-language intelligence assistant powered by local Ollama (Llama 3.1).
- **Evidence-Grounded AI Responses**: Cites specific database record identifiers (`[Vehicle VIN: ...]`, `[Transaction Ref: ...]`, `[Service Visit #...]`, `[Review #...]`).
- **Security & Guardrails**: Read-only database access via approved Python services; no arbitrary SQL execution; input validation and query length constraints.
- **Audit Logging**: Structured query responses with cited evidence records and model metadata.

---

## Technology Stack

| Layer | Component | Technology | Version / Details |
|---|---|---|---|
| Backend | Runtime & Language | Python | 3.13 |
| Backend | Web Framework | FastAPI | 0.115.11 |
| Backend | ASGI Server | Uvicorn | 0.34.0 |
| Backend | Data Validation | Pydantic v2 | 2.10.6 |
| Backend | Multipart Forms | python-multipart | 0.0.34 |
| Database | Storage | SQLite (MVP) | `data/autoinsight360.db` |
| Database | ORM | SQLAlchemy | 2.0.40 |
| Database | Safe Additive Migrations | Native Python Engine | `backend/app/database/migrations.py` |
| AI / LLM | Local Inference | Ollama | 0.40.16 |
| AI / LLM | Foundation Model | Llama 3.1 | `llama3.1:latest` (8B) |
| Frontend | UI Architecture | Single-Page Application (SPA) | HTML5, CSS3, Vanilla JavaScript |
| Testing | Test Runner | pytest | 8.3.4 (98 tests passed - 100%) |

---

## API Specification

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check: SQLite connection status, row counts, and Ollama model status. |
| `GET` | `/api/customers/search` | Search customers by name, customer ID, email, phone, or VIN. Supports `q` and `limit`. |
| `GET` | `/api/customers/{customer_id}/360` | Full Customer 360 profile: demographics, metrics, vehicles, transactions, services, loyalty, and reviews. |
| `POST` | `/api/agent/query` | Evidence-grounded natural-language query about a customer via Ollama (Llama 3.1). |
| `POST` | `/api/customers/{customer_id}/loyalty/redeem` | Controlled redemption of 2026 annual loyalty points with balance validation. |
| `POST` | `/api/loyalty/reconcile` | Reconcile visit rewards and birthday bonuses across all eligible customers. |
| `GET` | `/api/import/templates` | Catalog of supported canonical CSV templates with required and optional columns. |
| `GET` | `/api/import/templates/download` | Download pre-packaged ZIP bundle containing all 7 canonical CSV templates. |
| `GET` | `/api/import/templates/{filename}` | Download an individual canonical CSV template file. |
| `POST` | `/api/import/preview` | Upload and preview a dataset ZIP archive. Generates validation issues, row stats, and staging session ID. |
| `POST` | `/api/import/commit` | Confirm and transactionally commit a validated import session into SQLite. |
| `GET` | `/` | Serves the single-page frontend application. |
| `GET` | `/static/*` | Serves static assets (CSS, JavaScript). |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Browser Client                        │
│          (HTML5 / Modern Automotive CSS / Vanilla JS)       │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON fetch()
┌──────────────────────────────▼──────────────────────────────┐
│                  FastAPI Backend Server                      │
│                  (http://127.0.0.1:8000)                    │
│                                                             │
│   GET /api/health                                           │
│   GET /api/customers/search                                 │
│   GET /api/customers/{id}/360                               │
│   POST /api/agent/query                                     │
├──────────────────────────────┬──────────────────────────────┤
│       Service Layer          │        AI Agent Layer        │
│   (Customer 360 & CLTV)      │   (Prompt Builder & Citations│
└──────────────┬───────────────┴──────────────┬───────────────┘
               │ SQLAlchemy ORM               │ HTTP REST
┌──────────────▼───────────────┐ ┌────────────▼───────────────┐
│     SQLite Database          │ │      Local Ollama Engine    │
│  (data/autoinsight360.db)    │ │      (llama3.1:latest)     │
└──────────────────────────────┘ └─────────────────────────────┘
```

---

## Security & Guardrails

1. **Parameterised ORM Queries**: All database queries use SQLAlchemy ORM constructs. Raw SQL string interpolation is strictly prohibited.
2. **Read-Only AI Tools**: The AI Agent cannot perform database write or schema mutation operations.
3. **No Arbitrary SQL**: The AI Assistant receives structured context data and cannot execute SQL queries.
4. **Input Constraints**: Customer IDs are validated as positive integers; question inputs are restricted to 3–500 characters.
5. **Synthetic Data Policy**: All personal names, email addresses (`@autoinsight.demo`), VINs (`SYNTH-...`), and phone numbers (`555-...`) are entirely synthetic and fictitious.

---

## Demo Workflow

1. Start Ollama: `ollama run llama3.1` (or background service).
2. Start the application:
   ```powershell
   .\.venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000
   ```
3. Open `http://localhost:8000` in your web browser.
4. Search for a customer (e.g. `Katherine` or ID `1`) or select one from the quick dropdown.
5. Review the Customer 360 profile:
   - Historical CLTV and spending breakdown
   - Loyalty points balance and history
   - Vehicles owned and primary vehicle designation
   - Service visit records and maintenance expenditure
   - Customer feedback reviews
6. Use the **Customer Insights AI** panel to ask questions or click 1-click insight prompts.
