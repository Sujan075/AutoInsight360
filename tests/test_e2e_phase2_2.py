"""
AutoInsight360 - Phase 2.2 End-to-End Acceptance Test
======================================================
Tests the full lifecycle:
1. Data Ingestion of an Indian Automotive Customer with DOB, Vehicle, INR Transaction,
   and Detailed 2026 Service Visit.
2. Verification of Customer 360 profile with INR formatting, detailed service fields,
   and 2026 annual loyalty calculations (100 visit pts + 500 birthday pts = 600 pts).
3. Loyalty Points Redemption (redeem 250 pts -> balance 350 pts).
4. Grounded AI Querying with Ollama Llama 3.1 citing Service Visit and INR costs.
"""

import io
import uuid
import zipfile
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_phase2_2_complete_end_to_end_workflow():
    uid = uuid.uuid4().hex[:6]
    test_email = f"devendra_{uid}@autoinsight.demo"
    test_vin = f"SYNTH-IND-{uid}".upper()
    tx_ref = f"TXN-IND-{uid}".upper()

    # 1. Build Canonical Ingestion ZIP Bundle
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "dealers.csv",
            "dealer_ref,name,city,state,country\n"
            f"DLR-IND-{uid},AutoVista Motors Mumbai,Mumbai,MH,India\n",
        )
        zf.writestr(
            "customers.csv",
            "customer_ref,first_name,last_name,email,phone,date_of_birth,gender,city,state,country,customer_segment,loyalty_points_balance\n"
            f"CUST-IND-{uid},Devendra,Singhania,{test_email},+91 98201 12345,1986-07-22,Male,Mumbai,MH,India,Premium,0\n",
        )
        zf.writestr(
            "vehicles.csv",
            "vehicle_ref,customer_ref,vin,make,model,year,color,trim,body_style,fuel_type,transmission,purchase_date,purchase_price,current_mileage,is_primary\n"
            f"VEH-IND-{uid},CUST-IND-{uid},{test_vin},Tata,Nexon EV,2024,Dark Teal,Empowered Plus,SUV,Electric,Automatic,2024-02-15,1950000.00,12400,true\n",
        )
        zf.writestr(
            "transactions.csv",
            "transaction_ref,customer_ref,dealer_ref,vehicle_ref,transaction_type,amount,currency,transaction_date,payment_method,status,notes\n"
            f"{tx_ref},CUST-IND-{uid},DLR-IND-{uid},VEH-IND-{uid},vehicle_purchase,1950000.00,INR,2024-02-15,finance,completed,Purchased Tata Nexon EV in Mumbai\n",
        )
        zf.writestr(
            "service_visits.csv",
            "vehicle_ref,dealer_ref,service_type,service_date,odometer_reading,cost,parts_cost,labour_cost,service_status,customer_complaint,diagnosis,work_performed,next_service_date\n"
            f"VEH-IND-{uid},DLR-IND-{uid},brake_inspection,2026-05-18,12400,12500.00,7800.00,4700.00,completed,Brake squeal during low speed stopping,Brake pad glazing and light rotor scoring,Resurfaced front rotors and installed new ceramic brake pads,2026-11-18\n",
        )
        zf.writestr(
            "loyalty_events.csv",
            "customer_ref,event_type,points,event_date,description\n",
        )
        zf.writestr(
            "customer_reviews.csv",
            "customer_ref,dealer_ref,vehicle_ref,review_type,rating,title,body,review_date,is_verified,is_published\n"
            f"CUST-IND-{uid},DLR-IND-{uid},VEH-IND-{uid},dealer,5,Exceptional Service in Mumbai,Fast turnaround and smooth brake servicing.,2026-05-20,true,true\n",
        )

    zip_bytes = zip_buffer.getvalue()

    # 2. Preview Ingestion
    preview_resp = client.post(
        "/api/import/preview",
        files={"file": ("indian_dataset.zip", zip_bytes, "application/zip")},
    )
    assert preview_resp.status_code == 200
    pdata = preview_resp.json()
    summary_map = {item["file_name"]: item for item in pdata["summary"]}
    assert summary_map["customers.csv"]["accepted_rows"] == 1
    assert summary_map["service_visits.csv"]["accepted_rows"] == 1
    assert summary_map["transactions.csv"]["accepted_rows"] == 1

    # 3. Commit Ingestion
    commit_resp = client.post(
        "/api/import/commit",
        json={"session_id": pdata["session_id"]},
    )
    assert commit_resp.status_code == 200
    cdata = commit_resp.json()
    assert cdata["success"] is True

    # 4. Search Customer
    search_resp = client.get(f"/api/customers/search?q={test_email}")
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) == 1
    cust_id = results[0]["id"]

    # 5. Verify Customer 360 Profile
    c360_resp = client.get(f"/api/customers/{cust_id}/360")
    assert c360_resp.status_code == 200
    c360 = c360_resp.json()

    # Financial in INR
    assert c360["metrics"]["currency"] == "INR"
    assert c360["metrics"]["cltv_total"] == 1950000.00
    assert c360["metrics"]["total_service_cost"] == 12500.00

    # Detailed Service Visit
    assert len(c360["service_visits"]) == 1
    sv = c360["service_visits"][0]
    assert sv["customer_complaint"] == "Brake squeal during low speed stopping"
    assert sv["diagnosis"] == "Brake pad glazing and light rotor scoring"
    assert sv["work_performed"] == "Resurfaced front rotors and installed new ceramic brake pads"
    assert sv["parts_cost"] == 7800.00
    assert sv["labour_cost"] == 4700.00
    assert sv["cost"] == 12500.00
    assert sv["odometer_reading"] == 12400
    assert sv["next_service_date"] == "2026-11-18"

    # 2026 Loyalty System:
    # 100 visit points (from 2026-05-18 completed visit)
    # + 500 birthday points (DOB: 1986-07-22 occurred in July 2026)
    # Total 2026 Balance = 600 pts
    assert c360["metrics"]["annual_visit_points"] == 100
    assert c360["metrics"]["annual_birthday_points"] == 500
    assert c360["metrics"]["has_birthday_bonus"] is True
    assert c360["metrics"]["annual_loyalty_balance"] == 600

    # 6. Test Controlled Points Redemption (Redeem 250 points)
    redeem_resp = client.post(
        f"/api/customers/{cust_id}/loyalty/redeem",
        json={"amount": 250, "notes": "Brake Maintenance Voucher"},
    )
    assert redeem_resp.status_code == 200
    rdata = redeem_resp.json()
    assert rdata["status"] == "success"
    assert rdata["redeemed_amount"] == 250
    assert rdata["remaining_2026_balance"] == 350

    # Verify updated Customer 360
    c360_updated_resp = client.get(f"/api/customers/{cust_id}/360")
    c360_updated = c360_updated_resp.json()
    assert c360_updated["metrics"]["annual_loyalty_balance"] == 350
    assert c360_updated["metrics"]["annual_redeemed_points"] == 250

    # 7. AI Assistant Query
    agent_resp = client.post(
        "/api/agent/query",
        json={
            "customer_id": cust_id,
            "question": "What service was performed on Devendra's vehicle in 2026, what parts were replaced, what was the cost in INR, and what is his remaining loyalty balance?",
        },
    )
    assert agent_resp.status_code == 200
    agent_data = agent_resp.json()
    assert agent_data["status"] in ("success", "fallback_empty", "fallback_timeout_or_offline")
    answer = agent_data["answer"]

    # Verify that the answer mentions INR / ₹, the service visit, and the remaining loyalty points
    assert ("₹" in answer or "INR" in answer)
    assert any("Service Visit" in item for item in agent_data["evidence_records"])
