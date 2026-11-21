"""
AutoInsight360 - Tests for Dynamic Data Import & Ingestion
============================================================
Tests canonical templates, ZIP validation, multi-stage schema checking,
foreign key resolution, preview generation, and transactional database commit.
"""

import io
import zipfile
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


# ===========================================================================
# 1. Template Catalog & Download Tests
# ===========================================================================

def test_get_template_catalog():
    """GET /api/import/templates returns all 7 canonical template definitions."""
    resp = client.get("/api/import/templates")
    assert resp.status_code == 200
    catalog = resp.json()
    assert isinstance(catalog, list)
    assert len(catalog) == 7
    filenames = [t["filename"] for t in catalog]
    assert "customers.csv" in filenames
    assert "vehicles.csv" in filenames
    assert "dealers.csv" in filenames
    assert "transactions.csv" in filenames
    assert "service_visits.csv" in filenames
    assert "loyalty_events.csv" in filenames
    assert "customer_reviews.csv" in filenames


def test_download_all_templates_zip():
    """GET /api/import/templates/download returns valid ZIP containing 7 CSVs."""
    resp = client.get("/api/import/templates/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] in ("application/zip", "application/x-zip-compressed")
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    files = zf.namelist()
    assert len(files) == 7
    assert "customers.csv" in files
    assert "vehicles.csv" in files


def test_download_single_template_csv():
    """GET /api/import/templates/customers.csv returns CSV content."""
    resp = client.get("/api/import/templates/customers.csv")
    assert resp.status_code == 200
    assert "customer_ref" in resp.text
    assert "email" in resp.text


def test_download_nonexistent_template():
    """GET /api/import/templates/unknown.csv returns 404."""
    resp = client.get("/api/import/templates/unknown.csv")
    assert resp.status_code == 404


# ===========================================================================
# 2. Upload & Preview Validation Tests
# ===========================================================================

def test_preview_rejects_non_zip_file():
    """POST /api/import/preview with a .txt file returns 400."""
    files = {"file": ("test.txt", b"plain text", "text/plain")}
    resp = client.post("/api/import/preview", files=files)
    assert resp.status_code == 400
    assert "must be a .zip" in resp.json()["detail"].lower()


def test_preview_rejects_corrupted_zip():
    """POST /api/import/preview with corrupted zip bytes returns 400."""
    files = {"file": ("corrupt.zip", b"not a real zip file", "application/zip")}
    resp = client.post("/api/import/preview", files=files)
    assert resp.status_code == 400
    assert "not a valid zip archive" in resp.json()["detail"].lower()


def test_preview_empty_zip_returns_no_canonical_found():
    """POST /api/import/preview with an empty zip returns preview with errors."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("notes.txt", "hello")
    zip_buffer.seek(0)

    files = {"file": ("empty.zip", zip_buffer.getvalue(), "application/zip")}
    resp = client.post("/api/import/preview", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_commit"] is False
    assert data["total_accepted_rows"] == 0
    assert any("no recognized canonical csv" in iss["message"].lower() for iss in data["issues"])


def test_preview_missing_required_column_fails():
    """POST /api/import/preview with missing required columns flags error."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        # customers.csv missing 'email'
        zf.writestr("customers.csv", "first_name,last_name\nJohn,Doe\n")
    zip_buffer.seek(0)

    files = {"file": ("dataset.zip", zip_buffer.getvalue(), "application/zip")}
    resp = client.post("/api/import/preview", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_commit"] is False
    assert any("missing required columns: email" in iss["message"].lower() for iss in data["issues"])


def test_preview_unresolved_foreign_key_fails():
    """POST /api/import/preview where vehicles reference missing customer fails."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr(
            "vehicles.csv",
            "vehicle_ref,customer_ref,vin,make,model,year\n"
            "V1,MISSING_CUST_999,SYNTH-TEST-VIN01,Ford,F-150,2022\n"
        )
    zip_buffer.seek(0)

    files = {"file": ("dataset.zip", zip_buffer.getvalue(), "application/zip")}
    resp = client.post("/api/import/preview", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_commit"] is False
    assert any("referenced customer 'missing_cust_999' was not found" in iss["message"].lower() for iss in data["issues"])


def test_preview_and_commit_valid_dataset():
    """Full workflow: upload valid zip bundle, preview, and commit to database."""
    import uuid
    uid = uuid.uuid4().hex[:6]
    test_email = f"jordan.taylor.{uid}@autoinsight.demo"
    test_vin = f"SYNTH-TEST-{uid.upper()}"
    test_tx_ref = f"TXN-TEST-{uid.upper()}"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr(
            "dealers.csv",
            "dealer_ref,name,city,state\n"
            f"DLR-TEST-{uid},Test Dealer Chicago {uid},Chicago,IL\n"
        )
        zf.writestr(
            "customers.csv",
            "customer_ref,first_name,last_name,email,customer_segment,city,state\n"
            f"CUST-TEST-1,Jordan,Taylor,{test_email},Premium,Chicago,IL\n"
        )
        zf.writestr(
            "vehicles.csv",
            "vehicle_ref,customer_ref,vin,make,model,year,current_mileage\n"
            f"VEH-TEST-1,CUST-TEST-1,{test_vin},Tesla,Model Y,2023,12400\n"
        )
        zf.writestr(
            "transactions.csv",
            "transaction_ref,customer_ref,dealer_ref,vehicle_ref,transaction_type,amount,transaction_date\n"
            f"{test_tx_ref},CUST-TEST-1,DLR-TEST-{uid},VEH-TEST-1,vehicle_purchase,52000.00,2023-05-10\n"
        )
        zf.writestr(
            "service_visits.csv",
            "vehicle_ref,dealer_ref,service_type,service_date,cost,description\n"
            f"VEH-TEST-1,DLR-TEST-{uid},tyre_rotation,2023-11-20,75.00,Tire rotation\n"
        )
        zf.writestr(
            "loyalty_events.csv",
            "customer_ref,event_type,points,event_date,transaction_ref\n"
            f"CUST-TEST-1,earn,120,2023-05-10,{test_tx_ref}\n"
        )
        zf.writestr(
            "customer_reviews.csv",
            "customer_ref,dealer_ref,vehicle_ref,review_type,rating,review_date,title,body\n"
            f"CUST-TEST-1,DLR-TEST-{uid},VEH-TEST-1,vehicle,5,2023-06-01,Love the Tesla,Smooth drive\n"
        )
    zip_buffer.seek(0)

    # 1. Preview
    files = {"file": ("new_dataset.zip", zip_buffer.getvalue(), "application/zip")}
    prev_resp = client.post("/api/import/preview", files=files)
    assert prev_resp.status_code == 200
    prev_data = prev_resp.json()
    assert prev_data["can_commit"] is True
    assert prev_data["total_accepted_rows"] == 7
    assert prev_data["total_rejected_rows"] == 0
    session_id = prev_data["session_id"]

    # 2. Commit
    commit_resp = client.post("/api/import/commit", json={"session_id": session_id})
    assert commit_resp.status_code == 200
    commit_data = commit_resp.json()
    assert commit_data["success"] is True
    assert commit_data["imported_counts"]["customers"] == 1
    assert commit_data["imported_counts"]["vehicles"] == 1
    assert commit_data["imported_counts"]["dealers"] == 1
    assert commit_data["imported_counts"]["transactions"] == 1
    assert commit_data["imported_counts"]["service_visits"] == 1
    assert commit_data["imported_counts"]["loyalty_events"] == 1
    assert commit_data["imported_counts"]["customer_reviews"] == 1

    # 3. Verify customer can be searched immediately
    search_resp = client.get("/api/customers/search?q=Jordan")
    assert search_resp.status_code == 200
    results = search_resp.json()
    matching = [c for c in results if c["email"] == test_email]
    assert len(matching) == 1
    new_cid = matching[0]["id"]

    # 4. Verify Customer 360 profile
    c360_resp = client.get(f"/api/customers/{new_cid}/360")
    assert c360_resp.status_code == 200
    c360 = c360_resp.json()
    assert c360["customer"]["first_name"] == "Jordan"
    assert c360["customer"]["last_name"] == "Taylor"
    assert c360["metrics"]["cltv_total"] == 52000.00
    assert c360["metrics"]["loyalty_points_balance"] == 120
    assert len(c360["vehicles"]) == 1
    assert c360["vehicles"][0]["vin"] == test_vin
    assert len(c360["service_visits"]) == 1
    assert len(c360["transactions"]) == 1
    assert len(c360["reviews"]) == 1
