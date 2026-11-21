"""
AutoInsight360 - Phase 2.1 End-to-End Acceptance Tests
========================================================
Validates the complete workflow:
1. Ingest new automotive customer dataset via validated ZIP bundle.
2. Preview & confirm import into SQLite.
3. Search for newly imported customer.
4. Retrieve dynamic Customer 360 profile, CLTV, and vehicle history.
5. Query local Ollama AI regarding imported service history.
6. Verify evidence citation record IDs for audit grounding.
"""

import io
import uuid
import zipfile
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_e2e_new_customer_import_and_ai_query():
    """
    TASK 7 Acceptance Test:
    Imports a brand-new automotive customer (Dominic Torres) with a 2023 Porsche Taycan 4S,
    linked transaction ($118,500), brake inspection service visit ($480), and loyalty reward.
    Verifies full-stack pipeline from ingestion to AI query citations.
    """
    run_id = uuid.uuid4().hex[:6]
    cust_email = f"dominic.torres.{run_id}@autoinsight.demo"
    cust_vin = f"SYNTH-PORSCHE-{run_id.upper()}"
    tx_ref = f"TXN-DT-{run_id.upper()}"
    dealer_name = f"Apex Porsche Center {run_id}"

    # Step A: Build canonical CSV ZIP bundle
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr(
            "dealers.csv",
            "dealer_ref,name,city,state,country\n"
            f"DLR-PORSCHE-1,{dealer_name},Denver,CO,USA\n"
        )
        zf.writestr(
            "customers.csv",
            "customer_ref,first_name,last_name,email,customer_segment,city,state\n"
            f"CUST-DT-01,Dominic,Torres,{cust_email},Premium,Denver,CO\n"
        )
        zf.writestr(
            "vehicles.csv",
            "vehicle_ref,customer_ref,vin,make,model,year,body_style,fuel_type,current_mileage\n"
            f"VEH-DT-01,CUST-DT-01,{cust_vin},Porsche,Taycan 4S,2023,Sedan,Electric,8450\n"
        )
        zf.writestr(
            "transactions.csv",
            "transaction_ref,customer_ref,dealer_ref,vehicle_ref,transaction_type,amount,transaction_date,status\n"
            f"{tx_ref},CUST-DT-01,DLR-PORSCHE-1,VEH-DT-01,vehicle_purchase,118500.00,2023-07-20,completed\n"
        )
        zf.writestr(
            "service_visits.csv",
            "vehicle_ref,dealer_ref,service_type,service_date,cost,description,technician_notes\n"
            f"VEH-DT-01,DLR-PORSCHE-1,brake_inspection,2024-02-14,480.00,Annual PCCB ceramic brake inspection,Ceramic brake pads at 9.5mm front and rear. Nominal condition.\n"
        )
        zf.writestr(
            "loyalty_events.csv",
            "customer_ref,event_type,points,event_date,transaction_ref,description\n"
            f"CUST-DT-01,earn,350,2023-07-20,{tx_ref},Porsche Taycan vehicle acquisition bonus\n"
        )
        zf.writestr(
            "customer_reviews.csv",
            "customer_ref,dealer_ref,vehicle_ref,review_type,rating,review_date,title,body\n"
            f"CUST-DT-01,DLR-PORSCHE-1,VEH-DT-01,vehicle,5,2023-08-01,Exceptional Electric GT,Incredible acceleration and handling in Denver winter.\n"
        )
    zip_buf.seek(0)

    # Step B: Upload and Preview
    files = {"file": ("porsche_customer_dataset.zip", zip_buf.getvalue(), "application/zip")}
    preview_res = client.post("/api/import/preview", files=files)
    assert preview_res.status_code == 200, f"Preview failed: {preview_res.text}"
    preview_data = preview_res.json()
    assert preview_data["can_commit"] is True
    assert preview_data["total_accepted_rows"] == 7
    assert preview_data["total_rejected_rows"] == 0
    session_id = preview_data["session_id"]

    # Step C: Confirm & Commit Import
    commit_res = client.post("/api/import/commit", json={"session_id": session_id})
    assert commit_res.status_code == 200, f"Commit failed: {commit_res.text}"
    commit_data = commit_res.json()
    assert commit_data["success"] is True
    assert commit_data["imported_counts"]["customers"] == 1
    assert commit_data["imported_counts"]["vehicles"] == 1
    assert commit_data["imported_counts"]["service_visits"] == 1

    # Step D & E: Search for Newly Imported Customer
    search_res = client.get("/api/customers/search?q=Dominic")
    assert search_res.status_code == 200
    search_results = search_res.json()
    matching_custs = [c for c in search_results if c["email"] == cust_email]
    assert len(matching_custs) == 1, "Newly imported customer Dominic Torres not found in search results."
    new_cust_id = matching_custs[0]["id"]
    assert matching_custs[0]["full_name"] == "Dominic Torres"
    assert "Porsche" in matching_custs[0]["primary_vehicle"]

    # Step F: Open Customer 360 Profile & Validate Metrics
    c360_res = client.get(f"/api/customers/{new_cust_id}/360")
    assert c360_res.status_code == 200
    profile = c360_res.json()
    assert profile["customer"]["email"] == cust_email
    assert profile["metrics"]["cltv_total"] == 118500.00
    assert profile["metrics"]["cltv_vehicle_spend"] == 118500.00
    assert profile["metrics"]["loyalty_points_balance"] == 350
    assert profile["metrics"]["total_services_count"] == 1
    assert profile["metrics"]["total_service_cost"] == 480.00
    assert len(profile["vehicles"]) == 1
    assert profile["vehicles"][0]["vin"] == cust_vin
    assert len(profile["service_visits"]) == 1
    service_record = profile["service_visits"][0]
    assert service_record["service_type"] == "brake_inspection"
    assert "9.5mm" in service_record["technician_notes"]

    # Step G: Query AI Agent about Newly Imported Customer's Service History
    agent_payload = {
        "customer_id": new_cust_id,
        "question": "What service was performed on Dominic's vehicle, how much did it cost, and what were the technician notes?",
    }
    agent_res = client.post("/api/agent/query", json=agent_payload)
    assert agent_res.status_code == 200
    agent_data = agent_res.json()
    assert agent_data["customer_id"] == new_cust_id
    assert agent_data["status"] == "success"
    answer_lower = agent_data["answer"].lower()

    # Step H: Verify Evidence Grounding & Record ID Citations
    assert "brake" in answer_lower or "480" in answer_lower or "porsche" in answer_lower or "taycan" in answer_lower
    # Must cite real database records
    evidence_tags = agent_data["evidence_records"]
    assert len(evidence_tags) > 0
    assert any(
        f"Service Visit #{service_record['id']}" in tag
        or cust_vin in tag
        or f"Customer #{new_cust_id}" in tag
        for tag in evidence_tags
    )
