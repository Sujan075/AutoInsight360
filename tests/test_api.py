"""
AutoInsight360 - Phase 2 API & Full-Stack Integration Tests
=============================================================
Tests FastAPI endpoints, database integration, CLTV calculation,
Customer 360 retrieval, error handling, static serving, and AI agent query.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


# ===========================================================================
# 1. System & Health Check Tests
# ===========================================================================

def test_health_check_endpoint():
    """GET /api/health returns 200 with database status and metrics."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["total_customers"] > 0
    assert data["total_vehicles"] > 0
    assert data["total_dealers"] > 0
    assert data["total_transactions"] > 0
    assert data["total_services"] > 0
    assert "model_name" in data


# ===========================================================================
# 2. Customer Search Tests
# ===========================================================================

def test_search_customers_default():
    """GET /api/customers/search without query returns top customers."""
    resp = client.get("/api/customers/search?limit=10")
    assert resp.status_code == 200
    customers = resp.json()
    assert isinstance(customers, list)
    assert len(customers) > 0
    first = customers[0]
    assert "id" in first
    assert "full_name" in first
    assert "email" in first
    assert "customer_segment" in first
    assert "loyalty_points" in first
    assert "vehicles_count" in first


def test_search_customers_by_numeric_id():
    """GET /api/customers/search with an exact ID query returns that customer."""
    resp = client.get("/api/customers/search?q=1")
    assert resp.status_code == 200
    customers = resp.json()
    assert any(c["id"] == 1 for c in customers)


def test_search_customers_by_name():
    """GET /api/customers/search with a name substring returns matching customers."""
    # Find a name from the database first
    sample_resp = client.get("/api/customers/search?limit=1")
    sample_name = sample_resp.json()[0]["first_name"]

    resp = client.get(f"/api/customers/search?q={sample_name}")
    assert resp.status_code == 200
    customers = resp.json()
    assert len(customers) > 0
    assert any(sample_name.lower() in c["full_name"].lower() for c in customers)


def test_search_customers_no_match():
    """GET /api/customers/search with nonexistent term returns empty list."""
    resp = client.get("/api/customers/search?q=XYZNONEXISTENT99999")
    assert resp.status_code == 200
    customers = resp.json()
    assert isinstance(customers, list)
    assert len(customers) == 0


# ===========================================================================
# 3. Customer 360 Full Profile Tests
# ===========================================================================

def test_get_customer_360_success():
    """GET /api/customers/{id}/360 returns comprehensive profile with verified metrics."""
    resp = client.get("/api/customers/1/360")
    assert resp.status_code == 200
    data = resp.json()

    # Customer object
    customer = data["customer"]
    assert customer["id"] == 1
    assert "full_name" in customer
    assert "email" in customer
    assert customer["email"].endswith("@autoinsight.demo")

    # Metrics
    metrics = data["metrics"]
    assert "cltv_total" in metrics
    assert "cltv_vehicle_spend" in metrics
    assert "cltv_service_spend" in metrics
    assert "loyalty_points_balance" in metrics
    assert "total_vehicles_count" in metrics
    assert "total_services_count" in metrics
    assert "total_transactions_count" in metrics
    assert metrics["cltv_total"] >= 0

    # Vehicles
    assert "vehicles" in data
    assert isinstance(data["vehicles"], list)
    if data["vehicles"]:
        v = data["vehicles"][0]
        assert "vin" in v
        assert "make" in v
        assert "model" in v
        assert "year" in v
        assert v["vin"].startswith("SYNTH-")

    # Transactions
    assert "transactions" in data
    assert isinstance(data["transactions"], list)
    if data["transactions"]:
        tx = data["transactions"][0]
        assert "reference_number" in tx
        assert "amount" in tx
        assert "status" in tx
        assert "dealer_name" in tx

    # Service Visits
    assert "service_visits" in data
    assert isinstance(data["service_visits"], list)

    # Loyalty Events
    assert "loyalty_events" in data
    assert isinstance(data["loyalty_events"], list)

    # Customer Reviews
    assert "reviews" in data
    assert isinstance(data["reviews"], list)


def test_get_customer_360_cltv_calculation():
    """Verify that CLTV equals the sum of completed transaction amounts."""
    resp = client.get("/api/customers/1/360")
    assert resp.status_code == 200
    data = resp.json()

    completed_txs = [t for t in data["transactions"] if t["status"] == "completed"]
    expected_cltv = round(sum(t["amount"] for t in completed_txs), 2)
    actual_cltv = data["metrics"]["cltv_total"]

    assert actual_cltv == expected_cltv, (
        f"CLTV calculation mismatch: actual {actual_cltv} vs expected {expected_cltv}"
    )


def test_get_customer_360_not_found():
    """GET /api/customers/{id}/360 with nonexistent ID returns 404."""
    resp = client.get("/api/customers/999999/360")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_get_customer_360_invalid_id():
    """GET /api/customers/{id}/360 with zero or negative ID returns 400."""
    resp = client.get("/api/customers/0/360")
    assert resp.status_code == 400

    resp_neg = client.get("/api/customers/-5/360")
    assert resp_neg.status_code == 400


# ===========================================================================
# 4. AI Agent Query Tests
# ===========================================================================

def test_agent_query_success():
    """POST /api/agent/query returns structured, evidence-grounded response."""
    payload = {
        "customer_id": 1,
        "question": "What vehicles does this customer own and what is their mileage?",
    }
    resp = client.post("/api/agent/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["customer_id"] == 1
    assert "customer_name" in data
    assert "answer" in data
    assert len(data["answer"]) > 10
    assert "evidence_records" in data
    assert isinstance(data["evidence_records"], list)
    assert len(data["evidence_records"]) > 0
    assert "model" in data
    assert "status" in data


def test_agent_query_invalid_customer():
    """POST /api/agent/query with nonexistent customer ID returns error status."""
    payload = {
        "customer_id": 999999,
        "question": "Tell me about this customer.",
    }
    resp = client.post("/api/agent/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error_not_found"
    assert "does not exist" in data["answer"]


def test_agent_query_empty_question():
    """POST /api/agent/query with empty question returns validation error."""
    payload = {
        "customer_id": 1,
        "question": "   ",
    }
    resp = client.post("/api/agent/query", json=payload)
    assert resp.status_code in (400, 422)


def test_agent_query_question_too_long():
    """POST /api/agent/query with question exceeding 500 characters returns 422."""
    payload = {
        "customer_id": 1,
        "question": "a" * 501,
    }
    resp = client.post("/api/agent/query", json=payload)
    assert resp.status_code == 422


# ===========================================================================
# 5. Static Files & Frontend Serving Tests
# ===========================================================================

def test_serve_frontend_index():
    """GET / returns the single-page HTML application."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "AutoInsight360" in resp.text
    assert "Customer 360" in resp.text


def test_serve_static_css():
    """GET /static/css/styles.css returns CSS stylesheet."""
    resp = client.get("/static/css/styles.css")
    assert resp.status_code == 200
    assert "text/css" in resp.headers.get("content-type", "")


def test_serve_static_js():
    """GET /static/js/app.js returns client application script."""
    resp = client.get("/static/js/app.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers.get("content-type", "")
    assert "loadCustomer360" in resp.text
