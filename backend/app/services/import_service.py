"""
AutoInsight360 - Import Service
=================================
Core business logic for dynamic CSV/ZIP dataset ingestion,
schema validation, relationship mapping, preview generation,
and transactional database commits.
"""

from __future__ import annotations

import csv
import datetime
import io
import logging
import os
import re
import time
import uuid
import zipfile
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from backend.app.database.models import (
    Customer,
    CustomerReview,
    Dealer,
    LoyaltyEvent,
    ServiceVisit,
    Transaction,
    Vehicle,
)
from backend.app.schemas.import_schemas import (
    EntityImportSummary,
    ImportCommitResponse,
    ImportPreviewResponse,
    TemplateFileInfo,
    ValidationIssue,
)

logger = logging.getLogger(__name__)

# Security & Quota Constants
MAX_ZIP_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MAX_ROWS_PER_ENTITY = 5000
SESSION_EXPIRY_SECONDS = 1800  # 30 minutes

# Email validation pattern
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Valid Enum Values
VALID_TRANSACTION_TYPES = {"vehicle_purchase", "service_payment", "parts", "accessories", "financing"}
VALID_TRANSACTION_STATUSES = {"completed", "refunded", "pending", "cancelled"}
VALID_SERVICE_TYPES = {"oil_change", "tyre_rotation", "brake_inspection", "major_service", "recall", "warranty", "repair"}
VALID_LOYALTY_EVENT_TYPES = {"earn", "redeem", "adjustment", "expiry", "bonus"}
VALID_REVIEW_TYPES = {"dealer", "vehicle", "service"}

# Canonical Schema Definitions
CANONICAL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "dealers.csv": {
        "entity": "dealers",
        "model": Dealer,
        "required": ["name", "city", "state"],
        "optional": ["dealer_ref", "country", "phone", "email", "is_active"],
        "ref_col": "dealer_ref",
        "description": "Automotive dealerships providing sales and services.",
    },
    "customers.csv": {
        "entity": "customers",
        "model": Customer,
        "required": ["first_name", "last_name", "email"],
        "optional": [
            "customer_ref", "phone", "date_of_birth", "gender", "city", "state",
            "country", "postal_code", "customer_segment", "preferred_contact",
            "is_active", "loyalty_points_balance", "registered_at",
        ],
        "ref_col": "customer_ref",
        "description": "Customer demographics, contact info, and profile metadata.",
    },
    "vehicles.csv": {
        "entity": "vehicles",
        "model": Vehicle,
        "required": ["customer_ref", "vin", "make", "model", "year"],
        "optional": [
            "vehicle_ref", "color", "trim", "body_style", "fuel_type",
            "transmission", "engine", "purchase_date", "purchase_price",
            "mileage_at_purchase", "current_mileage", "is_primary", "is_active",
        ],
        "ref_col": "vehicle_ref",
        "description": "Customer-owned vehicle registrations and technical specifications.",
    },
    "transactions.csv": {
        "entity": "transactions",
        "model": Transaction,
        "required": ["customer_ref", "dealer_ref", "transaction_type", "amount", "transaction_date"],
        "optional": [
            "transaction_ref", "vehicle_ref", "currency", "payment_method",
            "status", "notes",
        ],
        "ref_col": "transaction_ref",
        "description": "Vehicle sales, parts, accessories, and maintenance financial records.",
    },
    "service_visits.csv": {
        "entity": "service_visits",
        "model": ServiceVisit,
        "required": ["vehicle_ref", "dealer_ref", "service_type", "service_date"],
        "optional": [
            "mileage_at_service", "cost", "description", "technician_notes",
            "is_warranty", "next_service_date",
        ],
        "ref_col": None,
        "description": "Chronological vehicle maintenance, recall, and repair visits.",
    },
    "loyalty_events.csv": {
        "entity": "loyalty_events",
        "model": LoyaltyEvent,
        "required": ["customer_ref", "event_type", "points", "event_date"],
        "optional": ["description", "transaction_ref", "balance_after"],
        "ref_col": None,
        "description": "Points earned or redeemed towards customer rewards.",
    },
    "customer_reviews.csv": {
        "entity": "customer_reviews",
        "model": CustomerReview,
        "required": ["customer_ref", "review_type", "rating", "review_date"],
        "optional": [
            "dealer_ref", "vehicle_ref", "title", "body", "is_verified", "is_published",
        ],
        "ref_col": None,
        "description": "Customer satisfaction ratings and feedback comments.",
    },
}

# In-Memory Cache for Pending Import Sessions
# Session Data: { session_id: { "created_at": float, "parsed_data": dict, "summary": list, "issues": list } }
_IMPORT_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _clean_expired_sessions() -> None:
    """Remove import sessions older than SESSION_EXPIRY_SECONDS."""
    now = time.time()
    expired = [
        sid for sid, data in _IMPORT_SESSIONS.items()
        if now - data.get("created_at", 0) > SESSION_EXPIRY_SECONDS
    ]
    for sid in expired:
        _IMPORT_SESSIONS.pop(sid, None)


# ---------------------------------------------------------------------------
# Template Retrieval Helpers
# ---------------------------------------------------------------------------

def get_template_catalog() -> List[TemplateFileInfo]:
    """Return catalog metadata for all supported canonical templates."""
    catalog = []
    for filename, spec in CANONICAL_SCHEMAS.items():
        catalog.append(
            TemplateFileInfo(
                filename=filename,
                entity=spec["entity"],
                description=spec["description"],
                required_columns=spec["required"],
                optional_columns=spec["optional"],
            )
        )
    return catalog


# ---------------------------------------------------------------------------
# Parsing & Conversion Helpers
# ---------------------------------------------------------------------------

def _parse_bool(val: Any, default: bool = True) -> bool:
    if val is None or val == "":
        return default
    s = str(val).strip().lower()
    return s in ("true", "1", "t", "yes", "y")


def _parse_date(val: Any) -> Optional[datetime.date]:
    if not val or not str(val).strip():
        return None
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Invalid date format '{s}'. Expected YYYY-MM-DD.")


def _parse_datetime(val: Any) -> datetime.datetime:
    if not val or not str(val).strip():
        return datetime.datetime.now(datetime.UTC)
    s = str(val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(s, fmt)
            return dt.replace(tzinfo=datetime.UTC)
        except ValueError:
            pass
    return datetime.datetime.now(datetime.UTC)


def _parse_int(val: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> Optional[int]:
    if val is None or str(val).strip() == "":
        return None
    try:
        iv = int(float(str(val).strip()))
        if min_val is not None and iv < min_val:
            raise ValueError(f"Value {iv} must be >= {min_val}")
        if max_val is not None and iv > max_val:
            raise ValueError(f"Value {iv} must be <= {max_val}")
        return iv
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid integer '{val}': {e}")


def _parse_float(val: Any, min_val: Optional[float] = None) -> Optional[float]:
    if val is None or str(val).strip() == "":
        return None
    try:
        fv = round(float(str(val).strip().replace("$", "").replace(",", "")), 2)
        if min_val is not None and fv < min_val:
            raise ValueError(f"Value {fv} must be >= {min_val}")
        return fv
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid decimal/number '{val}': {e}")


# ---------------------------------------------------------------------------
# ZIP Validation & CSV Extraction
# ---------------------------------------------------------------------------

def process_upload_and_preview(
    zip_bytes: bytes,
    db: Session,
) -> ImportPreviewResponse:
    """
    Validate and inspect an uploaded ZIP bundle containing CSV datasets.
    Extracts files, checks canonical formats, validates rows and foreign keys,
    builds sample previews, and creates a staging session for confirmation.
    """
    _clean_expired_sessions()

    if len(zip_bytes) > MAX_ZIP_SIZE_BYTES:
        raise ValueError(f"Uploaded ZIP file exceeds maximum allowed size of {MAX_ZIP_SIZE_BYTES // (1024 * 1024)} MB.")

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        raise ValueError("The uploaded file is not a valid ZIP archive.")

    # Safe extraction & canonical filename matching
    extracted_csvs: Dict[str, str] = {}
    issues: List[ValidationIssue] = []

    for item in zf.infolist():
        # Prevent Zip Slip directory traversal
        norm_name = os.path.normpath(item.filename)
        if norm_name.startswith("..") or os.path.isabs(norm_name):
            issues.append(ValidationIssue(
                file=item.filename,
                severity="error",
                message="Zip Slip security violation: archive contains illegal file paths."
            ))
            continue

        base_name = os.path.basename(item.filename).lower()
        if not base_name.endswith(".csv") or base_name.startswith(".") or "__macosx" in item.filename.lower():
            continue

        # Match with canonical schema
        matched_canonical = None
        for canonical_name in CANONICAL_SCHEMAS.keys():
            if base_name == canonical_name.lower():
                matched_canonical = canonical_name
                break

        if matched_canonical:
            try:
                content = zf.read(item).decode("utf-8-sig")
                extracted_csvs[matched_canonical] = content
            except UnicodeDecodeError:
                issues.append(ValidationIssue(
                    file=item.filename,
                    severity="error",
                    message="File encoding is not valid UTF-8."
                ))
        else:
            issues.append(ValidationIssue(
                file=item.filename,
                severity="warning",
                message=f"Ignored non-canonical or unsupported CSV '{item.filename}'. Please use approved template names."
            ))

    if not extracted_csvs:
        return ImportPreviewResponse(
            session_id=str(uuid.uuid4()),
            can_commit=False,
            total_files_found=0,
            files_processed=[],
            summary=[],
            issues=issues + [ValidationIssue(
                file="archive.zip",
                severity="error",
                message="No recognized canonical CSV files found in the ZIP archive. (e.g. customers.csv, vehicles.csv, etc.)"
            )],
            total_accepted_rows=0,
            total_rejected_rows=0,
            message="No canonical CSV templates found in archive.",
        )

    # -----------------------------------------------------------------------
    # Multi-Stage Validation with Cross-Entity Foreign Key Tracking
    # -----------------------------------------------------------------------

    # Pre-populate known entities from existing SQLite database
    existing_dealers = db.query(Dealer).all()
    existing_dealer_names = {d.name.lower(): d.id for d in existing_dealers}
    existing_dealer_ids = {str(d.id): d.id for d in existing_dealers}

    existing_customers = db.query(Customer).all()
    existing_customer_emails = {c.email.lower(): c.id for c in existing_customers}
    existing_customer_ids = {str(c.id): c.id for c in existing_customers}

    existing_vehicles = db.query(Vehicle).all()
    existing_vehicle_vins = {v.vin.upper(): v.id for v in existing_vehicles}
    existing_vehicle_ids = {str(v.id): v.id for v in existing_vehicles}

    existing_transactions = db.query(Transaction).all()
    existing_tx_refs = {t.reference_number: t.id for t in existing_transactions if t.reference_number}

    # Tracking sets for batch scope
    batch_dealer_refs: Set[str] = set()
    batch_customer_refs: Set[str] = set()
    batch_vehicle_refs: Set[str] = set()
    batch_vehicle_vins: Set[str] = set()
    batch_tx_refs: Set[str] = set()

    parsed_data: Dict[str, List[Dict[str, Any]]] = {k: [] for k in CANONICAL_SCHEMAS.keys()}
    summaries: List[EntityImportSummary] = []

    # Process in strict topological order
    evaluation_order = [
        "dealers.csv",
        "customers.csv",
        "vehicles.csv",
        "transactions.csv",
        "service_visits.csv",
        "loyalty_events.csv",
        "customer_reviews.csv",
    ]

    for fname in evaluation_order:
        if fname not in extracted_csvs:
            continue

        raw_csv = extracted_csvs[fname]
        spec = CANONICAL_SCHEMAS[fname]
        reader = csv.DictReader(io.StringIO(raw_csv))

        # Check required columns
        header_fields = [h.strip().lower() for h in (reader.fieldnames or [])]
        reader.fieldnames = header_fields

        missing_required = [c for c in spec["required"] if c not in header_fields]
        if missing_required:
            issues.append(ValidationIssue(
                file=fname,
                severity="error",
                message=f"Missing required columns: {', '.join(missing_required)}"
            ))
            summaries.append(EntityImportSummary(
                entity=spec["entity"],
                file_name=fname,
                total_rows=0,
                accepted_rows=0,
                rejected_rows=0,
                warning_rows=1,
                sample_preview=[],
            ))
            continue

        # Check unexpected / unsupported columns
        allowed_cols = set(spec["required"] + spec["optional"])
        unsupported_cols = [c for c in header_fields if c not in allowed_cols]
        if unsupported_cols:
            issues.append(ValidationIssue(
                file=fname,
                severity="warning",
                message=f"Ignored unsupported columns: {', '.join(unsupported_cols)}"
            ))

        total_rows = 0
        accepted_rows = 0
        rejected_rows = 0
        warning_rows = 0
        sample_preview: List[Dict[str, Any]] = []

        for row_idx, row in enumerate(reader, start=2):
            total_rows += 1
            if total_rows > MAX_ROWS_PER_ENTITY:
                issues.append(ValidationIssue(
                    file=fname,
                    row=row_idx,
                    severity="error",
                    message=f"Row quota exceeded! Maximum allowed is {MAX_ROWS_PER_ENTITY} rows per file."
                ))
                rejected_rows += 1
                break

            row_errors: List[str] = []
            cleaned_record: Dict[str, Any] = {}

            # --- Specific Entity Validation ---
            if fname == "dealers.csv":
                name = row.get("name", "").strip()
                city = row.get("city", "").strip()
                state = row.get("state", "").strip()
                dealer_ref = row.get("dealer_ref", "").strip() or name

                if not name:
                    row_errors.append("Dealer 'name' is required.")
                if not city or not state:
                    row_errors.append("Dealer 'city' and 'state' are required.")

                if name.lower() in existing_dealer_names:
                    issues.append(ValidationIssue(
                        file=fname,
                        row=row_idx,
                        field="name",
                        severity="warning",
                        message=f"Dealer '{name}' already exists in database. Existing record will be reused for linked references."
                    ))
                    warning_rows += 1

                if not row_errors:
                    cleaned_record = {
                        "dealer_ref": dealer_ref,
                        "name": name,
                        "city": city,
                        "state": state,
                        "country": row.get("country", "").strip() or "USA",
                        "phone": row.get("phone", "").strip() or None,
                        "email": row.get("email", "").strip() or None,
                        "is_active": _parse_bool(row.get("is_active"), True),
                    }
                    batch_dealer_refs.add(dealer_ref.lower())
                    batch_dealer_refs.add(name.lower())

            elif fname == "customers.csv":
                first_name = row.get("first_name", "").strip()
                last_name = row.get("last_name", "").strip()
                email = row.get("email", "").strip().lower()
                customer_ref = row.get("customer_ref", "").strip() or email

                if not first_name or not last_name:
                    row_errors.append("Customer 'first_name' and 'last_name' are required.")
                if not email or not EMAIL_REGEX.match(email):
                    row_errors.append(f"Invalid or missing customer email '{email}'.")
                elif email in existing_customer_emails or email in [c["email"] for c in parsed_data["customers.csv"]]:
                    row_errors.append(f"Customer email '{email}' already exists in database or current batch.")

                dob = None
                try:
                    dob = _parse_date(row.get("date_of_birth"))
                except ValueError as e:
                    row_errors.append(str(e))

                points = 0
                try:
                    points = _parse_int(row.get("loyalty_points_balance"), min_val=0) or 0
                except ValueError as e:
                    row_errors.append(str(e))

                if not row_errors:
                    cleaned_record = {
                        "customer_ref": customer_ref,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "phone": row.get("phone", "").strip() or None,
                        "date_of_birth": dob,
                        "gender": row.get("gender", "").strip() or None,
                        "city": row.get("city", "").strip() or None,
                        "state": row.get("state", "").strip() or None,
                        "country": row.get("country", "").strip() or "USA",
                        "postal_code": row.get("postal_code", "").strip() or None,
                        "customer_segment": row.get("customer_segment", "").strip() or "Standard",
                        "preferred_contact": row.get("preferred_contact", "").strip() or "email",
                        "is_active": _parse_bool(row.get("is_active"), True),
                        "loyalty_points_balance": points,
                        "registered_at": _parse_datetime(row.get("registered_at")),
                    }
                    batch_customer_refs.add(customer_ref.lower())

            elif fname == "vehicles.csv":
                customer_ref = row.get("customer_ref", "").strip()
                vin = row.get("vin", "").strip().upper()
                make = row.get("make", "").strip()
                model = row.get("model", "").strip()
                vehicle_ref = row.get("vehicle_ref", "").strip() or vin

                if not customer_ref:
                    row_errors.append("Vehicle 'customer_ref' is required.")
                elif (customer_ref.lower() not in batch_customer_refs and
                      customer_ref not in existing_customer_ids and
                      customer_ref.lower() not in existing_customer_emails):
                    row_errors.append(f"Referenced customer '{customer_ref}' was not found in customers.csv or database.")

                if not vin:
                    row_errors.append("Vehicle 'vin' is required.")
                elif vin in existing_vehicle_vins or vin in batch_vehicle_vins:
                    row_errors.append(f"Vehicle VIN '{vin}' already exists in database or current import.")

                if not make or not model:
                    row_errors.append("Vehicle 'make' and 'model' are required.")

                year = None
                try:
                    year = _parse_int(row.get("year"), min_val=1900, max_val=2100)
                    if not year:
                        row_errors.append("Vehicle 'year' is required.")
                except ValueError as e:
                    row_errors.append(str(e))

                price = None
                try:
                    price = _parse_float(row.get("purchase_price"), min_val=0.0)
                except ValueError as e:
                    row_errors.append(str(e))

                pdate = None
                try:
                    pdate = _parse_date(row.get("purchase_date"))
                except ValueError as e:
                    row_errors.append(str(e))

                mileage = None
                try:
                    mileage = _parse_int(row.get("current_mileage"), min_val=0)
                except ValueError as e:
                    row_errors.append(str(e))

                if not row_errors:
                    cleaned_record = {
                        "vehicle_ref": vehicle_ref,
                        "customer_ref": customer_ref,
                        "vin": vin,
                        "make": make,
                        "model": model,
                        "year": year,
                        "color": row.get("color", "").strip() or None,
                        "trim": row.get("trim", "").strip() or None,
                        "body_style": row.get("body_style", "").strip() or None,
                        "fuel_type": row.get("fuel_type", "").strip() or None,
                        "transmission": row.get("transmission", "").strip() or None,
                        "engine": row.get("engine", "").strip() or None,
                        "purchase_date": pdate,
                        "purchase_price": price,
                        "mileage_at_purchase": _parse_int(row.get("mileage_at_purchase"), min_val=0),
                        "current_mileage": mileage,
                        "is_primary": _parse_bool(row.get("is_primary"), False),
                        "is_active": _parse_bool(row.get("is_active"), True),
                    }
                    batch_vehicle_refs.add(vehicle_ref.lower())
                    batch_vehicle_refs.add(vin.lower())
                    batch_vehicle_vins.add(vin)

            elif fname == "transactions.csv":
                customer_ref = row.get("customer_ref", "").strip()
                dealer_ref = row.get("dealer_ref", "").strip()
                vehicle_ref = row.get("vehicle_ref", "").strip() or None
                tx_ref = row.get("transaction_ref", "").strip() or f"TXN-IMP-{uuid.uuid4().hex[:8].upper()}"

                if not customer_ref:
                    row_errors.append("Transaction 'customer_ref' is required.")
                elif (customer_ref.lower() not in batch_customer_refs and
                      customer_ref not in existing_customer_ids and
                      customer_ref.lower() not in existing_customer_emails):
                    row_errors.append(f"Referenced customer '{customer_ref}' was not found in customers.csv or database.")

                if not dealer_ref:
                    row_errors.append("Transaction 'dealer_ref' is required.")
                elif (dealer_ref.lower() not in batch_dealer_refs and
                      dealer_ref not in existing_dealer_ids and
                      dealer_ref.lower() not in existing_dealer_names):
                    row_errors.append(f"Referenced dealer '{dealer_ref}' was not found in dealers.csv or database.")

                if vehicle_ref and (vehicle_ref.lower() not in batch_vehicle_refs and
                                    vehicle_ref not in existing_vehicle_ids and
                                    vehicle_ref.upper() not in existing_vehicle_vins):
                    row_errors.append(f"Referenced vehicle '{vehicle_ref}' was not found in vehicles.csv or database.")

                ttype = row.get("transaction_type", "").strip().lower()
                if not ttype or ttype not in VALID_TRANSACTION_TYPES:
                    row_errors.append(f"Invalid transaction_type '{ttype}'. Allowed: {', '.join(VALID_TRANSACTION_TYPES)}")

                amount = None
                try:
                    amount = _parse_float(row.get("amount"), min_val=0.0)
                    if amount is None:
                        row_errors.append("Transaction 'amount' is required.")
                except ValueError as e:
                    row_errors.append(str(e))

                tx_date = None
                try:
                    tx_date = _parse_date(row.get("transaction_date"))
                    if not tx_date:
                        row_errors.append("Transaction 'transaction_date' is required.")
                except ValueError as e:
                    row_errors.append(str(e))

                if tx_ref in existing_tx_refs or tx_ref in batch_tx_refs:
                    row_errors.append(f"Transaction reference '{tx_ref}' already exists.")

                status = row.get("status", "").strip().lower() or "completed"
                if status not in VALID_TRANSACTION_STATUSES:
                    row_errors.append(f"Invalid status '{status}'. Allowed: {', '.join(VALID_TRANSACTION_STATUSES)}")

                if not row_errors:
                    cleaned_record = {
                        "transaction_ref": tx_ref,
                        "customer_ref": customer_ref,
                        "dealer_ref": dealer_ref,
                        "vehicle_ref": vehicle_ref,
                        "transaction_type": ttype,
                        "amount": amount,
                        "currency": row.get("currency", "").strip() or "USD",
                        "transaction_date": tx_date,
                        "payment_method": row.get("payment_method", "").strip() or None,
                        "status": status,
                        "notes": row.get("notes", "").strip() or None,
                    }
                    batch_tx_refs.add(tx_ref)

            elif fname == "service_visits.csv":
                vehicle_ref = row.get("vehicle_ref", "").strip()
                dealer_ref = row.get("dealer_ref", "").strip()

                if not vehicle_ref:
                    row_errors.append("Service visit 'vehicle_ref' is required.")
                elif (vehicle_ref.lower() not in batch_vehicle_refs and
                      vehicle_ref not in existing_vehicle_ids and
                      vehicle_ref.upper() not in existing_vehicle_vins):
                    row_errors.append(f"Referenced vehicle '{vehicle_ref}' was not found.")

                if not dealer_ref:
                    row_errors.append("Service visit 'dealer_ref' is required.")
                elif (dealer_ref.lower() not in batch_dealer_refs and
                      dealer_ref not in existing_dealer_ids and
                      dealer_ref.lower() not in existing_dealer_names):
                    row_errors.append(f"Referenced dealer '{dealer_ref}' was not found.")

                stype = row.get("service_type", "").strip().lower()
                if not stype or stype not in VALID_SERVICE_TYPES:
                    row_errors.append(f"Invalid service_type '{stype}'. Allowed: {', '.join(VALID_SERVICE_TYPES)}")

                sdate = None
                try:
                    sdate = _parse_date(row.get("service_date"))
                    if not sdate:
                        row_errors.append("Service visit 'service_date' is required.")
                except ValueError as e:
                    row_errors.append(str(e))

                cost = None
                try:
                    cost = _parse_float(row.get("cost"), min_val=0.0)
                except ValueError as e:
                    row_errors.append(str(e))

                next_date = None
                try:
                    next_date = _parse_date(row.get("next_service_date"))
                except ValueError as e:
                    row_errors.append(str(e))

                if not row_errors:
                    cleaned_record = {
                        "vehicle_ref": vehicle_ref,
                        "dealer_ref": dealer_ref,
                        "service_type": stype,
                        "service_date": sdate,
                        "mileage_at_service": _parse_int(row.get("mileage_at_service"), min_val=0),
                        "cost": cost,
                        "description": row.get("description", "").strip() or None,
                        "technician_notes": row.get("technician_notes", "").strip() or None,
                        "is_warranty": _parse_bool(row.get("is_warranty"), False),
                        "next_service_date": next_date,
                    }

            elif fname == "loyalty_events.csv":
                customer_ref = row.get("customer_ref", "").strip()
                if not customer_ref:
                    row_errors.append("Loyalty event 'customer_ref' is required.")
                elif (customer_ref.lower() not in batch_customer_refs and
                      customer_ref not in existing_customer_ids and
                      customer_ref.lower() not in existing_customer_emails):
                    row_errors.append(f"Referenced customer '{customer_ref}' was not found.")

                etype = row.get("event_type", "").strip().lower()
                if not etype or etype not in VALID_LOYALTY_EVENT_TYPES:
                    row_errors.append(f"Invalid event_type '{etype}'. Allowed: {', '.join(VALID_LOYALTY_EVENT_TYPES)}")

                points = None
                try:
                    points = _parse_int(row.get("points"))
                    if points is None:
                        row_errors.append("Loyalty event 'points' is required.")
                except ValueError as e:
                    row_errors.append(str(e))

                edate = None
                try:
                    edate = _parse_date(row.get("event_date"))
                    if not edate:
                        row_errors.append("Loyalty event 'event_date' is required.")
                except ValueError as e:
                    row_errors.append(str(e))

                tx_ref = row.get("transaction_ref", "").strip() or None

                if not row_errors:
                    cleaned_record = {
                        "customer_ref": customer_ref,
                        "event_type": etype,
                        "points": points,
                        "event_date": edate,
                        "description": row.get("description", "").strip() or None,
                        "transaction_ref": tx_ref,
                        "balance_after": _parse_int(row.get("balance_after")) or 0,
                    }

            elif fname == "customer_reviews.csv":
                customer_ref = row.get("customer_ref", "").strip()
                dealer_ref = row.get("dealer_ref", "").strip() or None
                vehicle_ref = row.get("vehicle_ref", "").strip() or None

                if not customer_ref:
                    row_errors.append("Customer review 'customer_ref' is required.")
                elif (customer_ref.lower() not in batch_customer_refs and
                      customer_ref not in existing_customer_ids and
                      customer_ref.lower() not in existing_customer_emails):
                    row_errors.append(f"Referenced customer '{customer_ref}' was not found.")

                rtype = row.get("review_type", "").strip().lower()
                if not rtype or rtype not in VALID_REVIEW_TYPES:
                    row_errors.append(f"Invalid review_type '{rtype}'. Allowed: {', '.join(VALID_REVIEW_TYPES)}")

                rating = None
                try:
                    rating = _parse_int(row.get("rating"), min_val=1, max_val=5)
                    if rating is None:
                        row_errors.append("Customer review 'rating' (1-5) is required.")
                except ValueError as e:
                    row_errors.append(str(e))

                rdate = None
                try:
                    rdate = _parse_date(row.get("review_date"))
                    if not rdate:
                        row_errors.append("Customer review 'review_date' is required.")
                except ValueError as e:
                    row_errors.append(str(e))

                if not row_errors:
                    cleaned_record = {
                        "customer_ref": customer_ref,
                        "dealer_ref": dealer_ref,
                        "vehicle_ref": vehicle_ref,
                        "review_type": rtype,
                        "rating": rating,
                        "title": row.get("title", "").strip() or None,
                        "body": row.get("body", "").strip() or None,
                        "review_date": rdate,
                        "is_verified": _parse_bool(row.get("is_verified"), False),
                        "is_published": _parse_bool(row.get("is_published"), True),
                    }

            # Aggregate row verdict
            if row_errors:
                rejected_rows += 1
                for err in row_errors:
                    issues.append(ValidationIssue(
                        file=fname,
                        row=row_idx,
                        severity="error",
                        message=err,
                    ))
            else:
                accepted_rows += 1
                parsed_data[fname].append(cleaned_record)
                if len(sample_preview) < 3:
                    # serialize dates for preview JSON
                    preview_item = {}
                    for k, v in cleaned_record.items():
                        if isinstance(v, (datetime.date, datetime.datetime)):
                            preview_item[k] = v.isoformat()
                        else:
                            preview_item[k] = v
                    sample_preview.append(preview_item)

        summaries.append(EntityImportSummary(
            entity=spec["entity"],
            file_name=fname,
            total_rows=total_rows,
            accepted_rows=accepted_rows,
            rejected_rows=rejected_rows,
            warning_rows=warning_rows,
            sample_preview=sample_preview,
        ))

    total_accepted = sum(s.accepted_rows for s in summaries)
    total_rejected = sum(s.rejected_rows for s in summaries)
    can_commit = total_accepted > 0 and not any(i.severity == "error" for i in issues)

    session_id = str(uuid.uuid4())
    _IMPORT_SESSIONS[session_id] = {
        "created_at": time.time(),
        "parsed_data": parsed_data,
        "summary": summaries,
        "issues": issues,
    }

    status_msg = (
        f"Validation passed: {total_accepted} records ready to import."
        if can_commit
        else f"Validation finished with {total_rejected} rejected rows or blocking errors."
    )

    return ImportPreviewResponse(
        session_id=session_id,
        can_commit=can_commit,
        total_files_found=len(extracted_csvs),
        files_processed=list(extracted_csvs.keys()),
        summary=summaries,
        issues=issues,
        total_accepted_rows=total_accepted,
        total_rejected_rows=total_rejected,
        message=status_msg,
    )


# ---------------------------------------------------------------------------
# Transactional Database Commit
# ---------------------------------------------------------------------------

def commit_import_session(
    session_id: str,
    db: Session,
) -> ImportCommitResponse:
    """
    Commit previously validated records into SQLite within an atomic database transaction.
    Resolves external source references to auto-generated database IDs.
    Rolls back cleanly on any unexpected failure.
    """
    _clean_expired_sessions()

    session_bundle = _IMPORT_SESSIONS.get(session_id)
    if not session_bundle:
        raise ValueError("Import session expired or not found. Please upload the dataset again to preview.")

    parsed_data = session_bundle["parsed_data"]

    imported_counts: Dict[str, int] = {
        "dealers": 0,
        "customers": 0,
        "vehicles": 0,
        "transactions": 0,
        "service_visits": 0,
        "loyalty_events": 0,
        "customer_reviews": 0,
    }

    # Resolution maps from external string references -> SQLite IDs
    dealer_id_map: Dict[str, int] = {}
    customer_id_map: Dict[str, int] = {}
    vehicle_id_map: Dict[str, int] = {}
    transaction_id_map: Dict[str, int] = {}

    # Seed resolution maps with existing DB entities
    for d in db.query(Dealer).all():
        dealer_id_map[str(d.id)] = d.id
        dealer_id_map[d.name.lower()] = d.id

    for c in db.query(Customer).all():
        customer_id_map[str(c.id)] = c.id
        customer_id_map[c.email.lower()] = c.id

    for v in db.query(Vehicle).all():
        vehicle_id_map[str(v.id)] = v.id
        vehicle_id_map[v.vin.upper()] = v.id

    for t in db.query(Transaction).all():
        if t.reference_number:
            transaction_id_map[t.reference_number] = t.id

    try:
        # Atomic Transaction
        # 1. Insert Dealers
        for rec in parsed_data.get("dealers.csv", []):
            d_name = rec["name"].strip()
            existing_id = dealer_id_map.get(d_name.lower())
            if existing_id:
                dealer_id_map[rec["dealer_ref"].lower()] = existing_id
                continue

            new_dealer = Dealer(
                name=d_name,
                city=rec["city"],
                state=rec["state"],
                country=rec["country"],
                phone=rec["phone"],
                email=rec["email"],
                is_active=rec["is_active"],
            )
            db.add(new_dealer)
            db.flush()
            dealer_id_map[rec["dealer_ref"].lower()] = new_dealer.id
            dealer_id_map[new_dealer.name.lower()] = new_dealer.id
            dealer_id_map[str(new_dealer.id)] = new_dealer.id
            imported_counts["dealers"] += 1

        # 2. Insert Customers
        for rec in parsed_data.get("customers.csv", []):
            new_cust = Customer(
                first_name=rec["first_name"],
                last_name=rec["last_name"],
                email=rec["email"],
                phone=rec["phone"],
                date_of_birth=rec["date_of_birth"],
                gender=rec["gender"],
                city=rec["city"],
                state=rec["state"],
                country=rec["country"],
                postal_code=rec["postal_code"],
                customer_segment=rec["customer_segment"],
                preferred_contact=rec["preferred_contact"],
                is_active=rec["is_active"],
                loyalty_points_balance=rec["loyalty_points_balance"],
                registered_at=rec["registered_at"],
            )
            db.add(new_cust)
            db.flush()
            customer_id_map[rec["customer_ref"].lower()] = new_cust.id
            customer_id_map[new_cust.email.lower()] = new_cust.id
            customer_id_map[str(new_cust.id)] = new_cust.id
            imported_counts["customers"] += 1

        # 3. Insert Vehicles
        for rec in parsed_data.get("vehicles.csv", []):
            cid = customer_id_map.get(rec["customer_ref"].lower())
            if not cid:
                raise ValueError(f"Could not map customer reference '{rec['customer_ref']}'.")

            new_veh = Vehicle(
                customer_id=cid,
                vin=rec["vin"],
                make=rec["make"],
                model=rec["model"],
                year=rec["year"],
                color=rec["color"],
                trim=rec["trim"],
                body_style=rec["body_style"],
                fuel_type=rec["fuel_type"],
                transmission=rec["transmission"],
                engine=rec["engine"],
                purchase_date=rec["purchase_date"],
                purchase_price=rec["purchase_price"],
                mileage_at_purchase=rec["mileage_at_purchase"],
                current_mileage=rec["current_mileage"],
                is_primary=rec["is_primary"],
                is_active=rec["is_active"],
            )
            db.add(new_veh)
            db.flush()
            vehicle_id_map[rec["vehicle_ref"].lower()] = new_veh.id
            vehicle_id_map[new_veh.vin.upper()] = new_veh.id
            vehicle_id_map[str(new_veh.id)] = new_veh.id
            imported_counts["vehicles"] += 1

        # 4. Insert Transactions
        for rec in parsed_data.get("transactions.csv", []):
            cid = customer_id_map.get(rec["customer_ref"].lower())
            did = dealer_id_map.get(rec["dealer_ref"].lower())
            vid = vehicle_id_map.get(rec["vehicle_ref"].lower()) if rec.get("vehicle_ref") else None

            new_tx = Transaction(
                customer_id=cid,
                dealer_id=did,
                vehicle_id=vid,
                transaction_type=rec["transaction_type"],
                amount=rec["amount"],
                currency=rec["currency"],
                transaction_date=rec["transaction_date"],
                payment_method=rec["payment_method"],
                status=rec["status"],
                reference_number=rec["transaction_ref"],
                notes=rec["notes"],
            )
            db.add(new_tx)
            db.flush()
            transaction_id_map[rec["transaction_ref"]] = new_tx.id
            imported_counts["transactions"] += 1

        # 5. Insert Service Visits
        for rec in parsed_data.get("service_visits.csv", []):
            vid = vehicle_id_map.get(rec["vehicle_ref"].lower())
            did = dealer_id_map.get(rec["dealer_ref"].lower())

            new_sv = ServiceVisit(
                vehicle_id=vid,
                dealer_id=did,
                service_type=rec["service_type"],
                service_date=rec["service_date"],
                mileage_at_service=rec["mileage_at_service"],
                cost=rec["cost"],
                description=rec["description"],
                technician_notes=rec["technician_notes"],
                is_warranty=rec["is_warranty"],
                next_service_date=rec["next_service_date"],
            )
            db.add(new_sv)
            imported_counts["service_visits"] += 1

        # 6. Insert Loyalty Events
        affected_cust_ids: Set[int] = set()
        for rec in parsed_data.get("loyalty_events.csv", []):
            cid = customer_id_map.get(rec["customer_ref"].lower())
            tx_id = transaction_id_map.get(rec["transaction_ref"]) if rec.get("transaction_ref") else None

            new_le = LoyaltyEvent(
                customer_id=cid,
                event_type=rec["event_type"],
                points=rec["points"],
                event_date=rec["event_date"],
                description=rec["description"],
                related_transaction_id=tx_id,
                balance_after=rec["balance_after"],
            )
            db.add(new_le)
            imported_counts["loyalty_events"] += 1
            if cid:
                affected_cust_ids.add(cid)

        # 7. Insert Customer Reviews
        for rec in parsed_data.get("customer_reviews.csv", []):
            cid = customer_id_map.get(rec["customer_ref"].lower())
            did = dealer_id_map.get(rec["dealer_ref"].lower()) if rec.get("dealer_ref") else None
            vid = vehicle_id_map.get(rec["vehicle_ref"].lower()) if rec.get("vehicle_ref") else None

            new_cr = CustomerReview(
                customer_id=cid,
                dealer_id=did,
                vehicle_id=vid,
                review_type=rec["review_type"],
                rating=rec["rating"],
                title=rec["title"],
                body=rec["body"],
                review_date=rec["review_date"],
                is_verified=rec["is_verified"],
                is_published=rec["is_published"],
            )
            db.add(new_cr)
            imported_counts["customer_reviews"] += 1

        # Flush all pending inserts to SQLite session before calculating balances
        db.flush()

        # 8. Recalculate loyalty balance for affected customers
        for cid in affected_cust_ids:
            events = db.query(LoyaltyEvent).filter(LoyaltyEvent.customer_id == cid).all()
            if events:
                net_pts = sum(e.points for e in events)
                cust = db.query(Customer).filter(Customer.id == cid).first()
                if cust:
                    cust.loyalty_points_balance = max(0, net_pts)

        db.flush()
        # Commit all atomically
        db.commit()

        # Clean session
        _IMPORT_SESSIONS.pop(session_id, None)

        now_iso = datetime.datetime.now(datetime.UTC).isoformat()
        logger.info("Successfully committed import session %s: %s", session_id, imported_counts)

        return ImportCommitResponse(
            success=True,
            message="Dataset imported and committed to database successfully.",
            imported_counts=imported_counts,
            committed_at=now_iso,
        )

    except Exception as e:
        db.rollback()
        logger.exception("Failed to commit import session %s: %s", session_id, e)
        raise RuntimeError(f"Database import failed during commit. Transaction was safely rolled back: {e}")
