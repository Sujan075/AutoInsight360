"""
AutoInsight360 - Phase 2.2 Detailed Service History Tests
==========================================================
Tests enhanced ServiceVisit schema, optional fields, backward compatibility,
and Customer 360 detailed service retrieval.
"""

import io
import uuid
import zipfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.app.database.connection import engine
from backend.app.database.models import Dealer, ServiceVisit, Vehicle
from backend.app.main import app

client = TestClient(app)


def test_service_visit_table_has_enhanced_columns():
    """Verify that SQLite service_visits table has all Phase 2.2 detailed columns."""
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("service_visits")}

    expected_cols = {
        "customer_complaint",
        "diagnosis",
        "work_performed",
        "service_status",
        "parts_cost",
        "labour_cost",
        "service_description",
        "odometer_reading",
        "next_service_date",
        "cost",
        "service_type",
        "service_date",
    }
    missing = expected_cols - cols
    assert not missing, f"service_visits table is missing required columns: {missing}"


def test_customer_360_service_visits_schema():
    """Verify that Customer 360 returns the enhanced ServiceVisitDetail fields."""
    resp = client.get("/api/customers/1/360")
    assert resp.status_code == 200
    data = resp.json()

    assert "service_visits" in data
    assert isinstance(data["service_visits"], list)

    if data["service_visits"]:
        sv = data["service_visits"][0]
        assert "customer_complaint" in sv
        assert "diagnosis" in sv
        assert "work_performed" in sv
        assert "service_status" in sv
        assert "parts_cost" in sv
        assert "labour_cost" in sv
        assert "odometer_reading" in sv
        assert "next_service_date" in sv


def test_backward_compatibility_old_service_csv_format():
    """Older CSV bundles missing optional columns must import cleanly without error."""
    uid = uuid.uuid4().hex[:6]
    test_email = f"old_format_{uid}@autoinsight.demo"
    test_vin = f"SYNTH-OLD-{uid}".upper()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "dealers.csv",
            "dealer_ref,name,city,state\n"
            f"DLR-OLD-1,Dealer Old {uid},Denver,CO\n",
        )
        zf.writestr(
            "customers.csv",
            "customer_ref,first_name,last_name,email\n"
            f"CUST-OLD-1,OldFormat,Customer,{test_email}\n",
        )
        zf.writestr(
            "vehicles.csv",
            "vehicle_ref,customer_ref,vin,make,model,year\n"
            f"VEH-OLD-1,CUST-OLD-1,{test_vin},Subaru,Outback,2022\n",
        )
        # Old service format with only original minimal fields
        zf.writestr(
            "service_visits.csv",
            "vehicle_ref,dealer_ref,service_type,service_date,cost,description\n"
            "VEH-OLD-1,DLR-OLD-1,oil_change,2024-03-15,3500.00,Basic oil change\n",
        )

    zip_bytes = zip_buffer.getvalue()

    # Preview
    preview_resp = client.post(
        "/api/import/preview",
        files={"file": ("old_dataset.zip", zip_bytes, "application/zip")},
    )
    assert preview_resp.status_code == 200
    pdata = preview_resp.json()
    summary_map = {item["file_name"]: item for item in pdata["summary"]}
    assert summary_map["service_visits.csv"]["accepted_rows"] == 1
    assert summary_map["service_visits.csv"]["rejected_rows"] == 0

    # Commit
    commit_resp = client.post(
        "/api/import/commit",
        json={"session_id": pdata["session_id"]},
    )
    assert commit_resp.status_code == 200
    cdata = commit_resp.json()
    assert cdata["imported_counts"]["service_visits"] == 1


def test_expanded_service_csv_format_import():
    """Expanded CSV bundles with all detailed service fields populate correctly."""
    uid = uuid.uuid4().hex[:6]
    test_email = f"detailed_{uid}@autoinsight.demo"
    test_vin = f"SYNTH-DET-{uid}".upper()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "dealers.csv",
            "dealer_ref,name,city,state\n"
            f"DLR-DET-1,Dealer Detail {uid},Phoenix,AZ\n",
        )
        zf.writestr(
            "customers.csv",
            "customer_ref,first_name,last_name,email,date_of_birth\n"
            f"CUST-DET-1,Aarav,Patel,{test_email},1990-05-15\n",
        )
        zf.writestr(
            "vehicles.csv",
            "vehicle_ref,customer_ref,vin,make,model,year\n"
            f"VEH-DET-1,CUST-DET-1,{test_vin},BMW,M340i,2023\n",
        )
        # Full Phase 2.2 expanded service format
        zf.writestr(
            "service_visits.csv",
            "vehicle_ref,dealer_ref,service_type,service_date,odometer_reading,cost,parts_cost,labour_cost,service_status,customer_complaint,diagnosis,work_performed,next_service_date\n"
            "VEH-DET-1,DLR-DET-1,brake_inspection,2026-04-10,18500,16500.00,10500.00,6000.00,completed,Vibration in pedal,Rotor thickness variation,Resurfaced rotors and installed new pads,2026-10-10\n",
        )

    zip_bytes = zip_buffer.getvalue()

    # Preview & commit
    preview_resp = client.post(
        "/api/import/preview",
        files={"file": ("detailed_dataset.zip", zip_bytes, "application/zip")},
    )
    assert preview_resp.status_code == 200
    pdata = preview_resp.json()
    summary_map = {item["file_name"]: item for item in pdata["summary"]}
    assert summary_map["service_visits.csv"]["accepted_rows"] == 1

    commit_resp = client.post(
        "/api/import/commit",
        json={"session_id": pdata["session_id"]},
    )
    assert commit_resp.status_code == 200

    # Retrieve newly imported customer
    search_resp = client.get(f"/api/customers/search?q={test_email}")
    assert search_resp.status_code == 200
    cust_id = search_resp.json()[0]["id"]

    c360_resp = client.get(f"/api/customers/{cust_id}/360")
    assert c360_resp.status_code == 200
    c360 = c360_resp.json()

    assert len(c360["service_visits"]) == 1
    sv = c360["service_visits"][0]
    assert sv["customer_complaint"] == "Vibration in pedal"
    assert sv["diagnosis"] == "Rotor thickness variation"
    assert sv["work_performed"] == "Resurfaced rotors and installed new pads"
    assert sv["parts_cost"] == 10500.00
    assert sv["labour_cost"] == 6000.00
    assert sv["cost"] == 16500.00
    assert sv["odometer_reading"] == 18500
    assert sv["service_status"] == "completed"
    assert sv["next_service_date"] == "2026-10-10"
