# AutoInsight360

**Automotive Customer 360 Intelligence Agent**

An AI-powered customer intelligence system that provides unified automotive customer information and evidence-backed insights using a locally running LLM.

---

## Current Status

**Phase 1 — Database Foundation** ✅

The relational database schema, synthetic data generator, and verification suite are complete and tested.

| Phase | Description | Status |
|---|---|---|
| Phase 0 | Project Setup & Specification | ✅ Complete |
| Phase 1 | Database Foundation (SQLite + SQLAlchemy) | ✅ Complete |
| Phase 2 | FastAPI Customer Endpoints | 🔜 Planned |
| Phase 3 | AI Agent Integration (Ollama / Llama 3.1) | 🔜 Planned |
| Phase 4 | Frontend UI | 🔜 Planned |

---

## Core Features

- Customer 360 lookup
- Historical Customer Value
- Vehicle ownership information
- Loyalty points and loyalty history
- Automotive service history
- Customer reviews and feedback
- AI-powered customer insights *(Phase 3)*
- Natural language querying *(Phase 3)*
- Evidence-grounded AI responses *(Phase 3)*
- Security guardrails
- Audit logging

---

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.13 |
| Web Framework | FastAPI *(Phase 2)* |
| ASGI Server | Uvicorn *(Phase 2)* |
| Database | SQLite (MVP) |
| ORM | SQLAlchemy 2.0 |
| AI Model | Ollama / Llama 3.1 *(Phase 3)* |
| Frontend | HTML, CSS, JavaScript *(Phase 4)* |
| Testing | pytest |

---

## Project Structure

```text
AutoInsight360/
├── backend/
│   └── app/
│       ├── database/
│       │   ├── __init__.py        # Package exports
│       │   ├── base.py            # SQLAlchemy declarative base
│       │   ├── connection.py      # Engine, session factory, get_db()
│       │   ├── init_db.py         # Table creation and schema verification
│       │   ├── models.py          # ORM models (all 7 entities)
│       │   └── seed_data.py       # Synthetic data generator
│       ├── agents/                # AI agents (Phase 3)
│       ├── services/              # Business logic (Phase 2)
│       └── schemas/               # Pydantic schemas (Phase 2)
├── data/
│   └── autoinsight360.db          # SQLite database (git-ignored)
├── docs/
│   └── ERD.md                     # Entity Relationship Diagram
├── frontend/                      # UI (Phase 4)
├── scripts/
│   ├── init_db.py                 # Database initialisation script
│   └── verify_db.py               # Database verification script
├── tests/
│   ├── conftest.py                # pytest fixtures (in-memory test DB)
│   └── test_database.py           # Database and ORM tests
├── .gitignore
├── project.md                     # Master specification (source of truth)
└── README.md
```

---

## Database Architecture

The database uses **SQLite** (MVP) managed via **SQLAlchemy 2.0 ORM**.

### Entities

| Table | Description |
|---|---|
| `dealers` | Automotive dealerships (5 in demo) |
| `customers` | Individual customer profiles (100 in demo) |
| `vehicles` | Customer-owned vehicles (100–150 in demo) |
| `transactions` | Financial transactions at a dealer |
| `service_visits` | Vehicle maintenance and repair records |
| `loyalty_events` | Points earned, redeemed or adjusted |
| `customer_reviews` | Customer ratings and feedback |

See [`docs/ERD.md`](docs/ERD.md) for the full Entity Relationship Diagram.

### Database Location

The database is stored at:

```
data/autoinsight360.db
```

This path is relative to the project root and is excluded from Git via `.gitignore`.

The location can be overridden using environment variables:

```
AUTOINSIGHT_DATA_DIR   — directory for the database file
AUTOINSIGHT_DB_NAME    — database filename (default: autoinsight360.db)
```

---

## Setup

### Prerequisites

- Python 3.13
- Git

### Create and activate the virtual environment

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
pip install sqlalchemy pytest faker
```

---

## Database Initialisation

### First-time setup

```powershell
python scripts/init_db.py
```

This will:
1. Create the `data/autoinsight360.db` SQLite database.
2. Create all required tables.
3. Seed synthetic data (~100 customers, ~100–150 vehicles, 5 dealers, etc.).
4. Verify the schema.

### Initialise without seeding

```powershell
python scripts/init_db.py --no-seed
```

### Reset database (DESTRUCTIVE — requires confirmation)

```powershell
python scripts/init_db.py --reset
```

> **Warning:** `--reset` permanently deletes all existing data. The script will prompt for confirmation before proceeding.

---

## Synthetic Data Generation

The synthetic data generator is located at:

```
backend/app/database/seed_data.py
```

It is called automatically by `scripts/init_db.py`.

The generator creates interconnected records with valid foreign-key relationships:

| Entity | Demo Target |
|---|---|
| Dealers | 5 |
| Customers | 100 |
| Vehicles | 100–150 |
| Transactions | ~400 |
| Service Visits | ~300 |
| Loyalty Events | ~400+ |
| Customer Reviews | ~150 |

Data generation uses a fixed random seed (`42`) for reproducibility.

Re-running the seed process is **idempotent**: existing records are not duplicated.

---

## Database Verification

Run the verification script to confirm the database is correctly set up:

```powershell
python scripts/verify_db.py
```

This checks:
- All expected tables exist
- Each table has records
- Foreign key integrity
- ORM relationship traversal
- A complete Customer 360 example query

---

## Running Tests

```powershell
# Run all tests with verbose output
python -m pytest tests/ -v

# Run a specific test class
python -m pytest tests/test_database.py::TestCustomer360Query -v
```

Tests use an **in-memory SQLite database** — they are isolated from the development database and safe to run at any time.

### Test coverage

| Test Class | What is tested |
|---|---|
| `TestSchema` | All 7 tables exist |
| `TestRecordCounts` | Each table has records > 0 |
| `TestDataIntegrity` | Field values, formats, constraints |
| `TestForeignKeys` | Referential integrity across all relationships |
| `TestRelationships` | ORM relationship traversal |
| `TestCustomer360Query` | Full end-to-end Customer 360 retrieval |
| `TestIdempotency` | Re-seeding does not create duplicates |

---

## Data Policy

> **SYNTHETIC DATA DISCLAIMER**
>
> All customer data, vehicle records, dealer information, transactions, and reviews
> in this system are **entirely synthetic and fictitious**.
>
> - Customer names, emails, phone numbers, addresses and dates of birth are randomly generated.
> - Synthetic emails use the domain `@autoinsight.demo`.
> - Vehicle VINs are prefixed with `SYNTH-` and are not real vehicle identifiers.
> - Dealer phone numbers use the `555-` prefix to identify them as synthetic.
> - No real personal information has been used or should ever be committed to this repository.

---

## Documentation

- [`project.md`](project.md) — Master specification (source of truth for all phases)
- [`docs/ERD.md`](docs/ERD.md) — Entity Relationship Diagram

---

## Contributing

1. Never commit real personal data, database files (`*.db`, `*.sqlite`), or secrets.
2. All new features must be consistent with `project.md`.
3. All new database changes must update `docs/ERD.md`.
4. Run the test suite before committing.
