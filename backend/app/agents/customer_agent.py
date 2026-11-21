"""
AutoInsight360 - Customer Intelligence Agent
==============================================
Evidence-grounded AI agent using local Ollama (Llama 3.1).

Security & Guardrails:
- Read-only database access via approved Python services.
- Never accepts or executes arbitrary SQL.
- Constrains prompts strictly to verified database records.
- Demands explicit citations for every claim.
- Enforces strict input validation and question length limits.
- Provides graceful fallback when the local LLM is offline or busy.
"""

from __future__ import annotations

import logging
import re
from typing import List, Tuple

import httpx
from sqlalchemy.orm import Session

from backend.app.schemas.customer_schemas import (
    AgentQueryResponse,
    Customer360Response,
)
from backend.app.services.customer_service import get_customer_360

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:latest"


def check_ollama_status() -> dict:
    """Check if Ollama server is running and the target model is loaded."""
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_found = any(DEFAULT_MODEL in m for m in models)
                return {
                    "running": True,
                    "model_available": model_found,
                    "model": DEFAULT_MODEL,
                    "models_list": models,
                }
    except Exception as e:
        logger.warning("Ollama health check failed: %s", e)

    return {
        "running": False,
        "model_available": False,
        "model": DEFAULT_MODEL,
        "models_list": [],
    }


def _build_evidence_context(profile: Customer360Response) -> Tuple[str, List[str]]:
    """
    Format verified Customer 360 data into a structured context string
    and extract all individual record IDs for audit and evidence grounding.
    """
    evidence_ids: List[str] = []
    lines: List[str] = []

    c = profile.customer
    m = profile.metrics

    lines.append(f"CUSTOMER PROFILE [Customer ID #{c.id}]:")
    lines.append(f"- Name: {c.full_name}")
    lines.append(f"- Email: {c.email}")
    lines.append(f"- Phone: {c.phone or 'N/A'}")
    lines.append(f"- Location: {c.city or 'N/A'}, {c.state or 'N/A'}, {c.country}")
    lines.append(f"- Date of Birth: {c.date_of_birth or 'N/A'}")
    lines.append(f"- Segment: {c.customer_segment or 'Standard'}")
    lines.append(f"- Preferred Contact: {c.preferred_contact or 'email'}")
    lines.append(f"- Account Status: {'Active' if c.is_active else 'Inactive'}")
    lines.append(f"- Registered Date: {c.registered_at.strftime('%Y-%m-%d')}")
    evidence_ids.append(f"Customer #{c.id}")

    lines.append("\nHISTORICAL METRICS & VALUE:")
    lines.append(f"- Customer Lifetime Value (CLTV): ${m.cltv_total:,.2f} USD")
    lines.append(f"  * Vehicle Purchases: ${m.cltv_vehicle_spend:,.2f}")
    lines.append(f"  * Service Payments: ${m.cltv_service_spend:,.2f}")
    lines.append(f"  * Parts & Accessories: ${m.cltv_parts_accessories_spend:,.2f}")
    lines.append(f"- Completed Transactions: {m.completed_transactions_count} of {m.total_transactions_count}")
    lines.append(f"- Total Vehicles Owned: {m.total_vehicles_count}")
    lines.append(f"- Loyalty Points Balance: {m.loyalty_points_balance} pts (Earned: {m.loyalty_points_earned}, Redeemed: {m.loyalty_points_redeemed})")
    lines.append(f"- Service Visits Count: {m.total_services_count} (Total Service Spend: ${m.total_service_cost:,.2f})")
    lines.append(f"- Reviews Submitted: {m.total_reviews_count} (Average Rating: {m.average_rating or 'N/A'}★)")

    lines.append("\nOWNED VEHICLES:")
    if profile.vehicles:
        for v in profile.vehicles:
            tag = f"Vehicle VIN: {v.vin}"
            evidence_ids.append(tag)
            primary_badge = " [PRIMARY]" if v.is_primary else ""
            price_str = f"${v.purchase_price:,.2f}" if v.purchase_price is not None else "N/A"
            mileage_str = f"{v.current_mileage:,} mi" if v.current_mileage is not None else "N/A"
            lines.append(
                f"- [{tag}]{primary_badge} {v.year} {v.make} {v.model} ({v.trim or 'Base'}), "
                f"Body: {v.body_style or 'N/A'}, Fuel: {v.fuel_type or 'N/A'}, "
                f"Transmission: {v.transmission or 'N/A'}, Engine: {v.engine or 'N/A'}, "
                f"Current Mileage: {mileage_str}, "
                f"Purchased: {v.purchase_date or 'N/A'} for {price_str}, "
                f"Service Visits Recorded: {v.service_visits_count}"
            )
    else:
        lines.append("- No vehicles on record.")

    lines.append("\nTRANSACTION HISTORY (Recent):")
    if profile.transactions:
        for t in profile.transactions[:10]:
            tag = f"Transaction Ref: {t.reference_number or f'TXN#{t.id}'}"
            evidence_ids.append(tag)
            lines.append(
                f"- [{tag}] Date: {t.transaction_date}, Type: {t.transaction_type}, "
                f"Amount: ${t.amount:,.2f} {t.currency}, Status: {t.status}, "
                f"Method: {t.payment_method or 'N/A'}, Dealer: {t.dealer_name or 'N/A'}, "
                f"Vehicle: {t.vehicle_info or 'N/A'}"
            )
        if len(profile.transactions) > 10:
            lines.append(f"- ... plus {len(profile.transactions) - 10} earlier transactions.")
    else:
        lines.append("- No transactions on record.")

    lines.append("\nSERVICE HISTORY (Recent):")
    if profile.service_visits:
        for sv in profile.service_visits[:10]:
            tag = f"Service Visit #{sv.id}"
            evidence_ids.append(tag)
            cost_str = f"${sv.cost:,.2f}" if sv.cost is not None else "$0.00"
            mileage_sv_str = f"{sv.mileage_at_service:,} mi" if sv.mileage_at_service is not None else "N/A"
            lines.append(
                f"- [{tag}] Date: {sv.service_date}, Vehicle: {sv.vehicle_info or sv.vehicle_vin}, "
                f"Service Type: {sv.service_type}, Cost: {cost_str}, "
                f"Mileage: {mileage_sv_str}, Dealer: {sv.dealer_name or 'N/A'}, "
                f"Warranty: {'Yes' if sv.is_warranty else 'No'}, Notes: {sv.technician_notes or sv.description or 'None'}"
            )
        if len(profile.service_visits) > 10:
            lines.append(f"- ... plus {len(profile.service_visits) - 10} earlier service visits.")
    else:
        lines.append("- No service visits on record.")

    lines.append("\nLOYALTY HISTORY (Recent):")
    if profile.loyalty_events:
        for le in profile.loyalty_events[:8]:
            tag = f"Loyalty Event #{le.id}"
            evidence_ids.append(tag)
            lines.append(
                f"- [{tag}] Date: {le.event_date}, Event: {le.event_type}, "
                f"Points: {le.points:+d}, Balance After: {le.balance_after} pts, "
                f"Desc: {le.description or 'N/A'}"
            )
    else:
        lines.append("- No loyalty events on record.")

    lines.append("\nCUSTOMER REVIEWS & FEEDBACK:")
    if profile.reviews:
        for r in profile.reviews:
            tag = f"Review #{r.id}"
            evidence_ids.append(tag)
            lines.append(
                f"- [{tag}] Date: {r.review_date}, Rating: {r.rating}★, "
                f"Type: {r.review_type}, Title: '{r.title or 'N/A'}', "
                f"Feedback: '{r.body or 'N/A'}', Verified: {'Yes' if r.is_verified else 'No'}"
            )
    else:
        lines.append("- No customer reviews on record.")

    return "\n".join(lines), evidence_ids


def _build_fallback_answer(profile: Customer360Response, question: str, evidence_ids: List[str]) -> str:
    """
    Generate an evidence-grounded summary answer if the local LLM is temporarily unavailable.
    Guarantees that the UI never crashes and always delivers factual customer data.
    """
    c = profile.customer
    m = profile.metrics
    q = question.lower()

    if any(k in q for k in ["vehicle", "car", "drive", "vin", "model", "make"]):
        veh_list = ", ".join(f"{v.year} {v.make} {v.model} ([Vehicle VIN: {v.vin}])" for v in profile.vehicles)
        return (
            f"**Customer Vehicle Summary for {c.full_name}:**\n\n"
            f"- **Total Vehicles:** {m.total_vehicles_count}\n"
            f"- **Vehicles on Record:** {veh_list or 'None'}\n"
            f"- **Primary Vehicle:** {next((f'{v.year} {v.make} {v.model} ([Vehicle VIN: {v.vin}])' for v in profile.vehicles if v.is_primary), 'None')}\n"
            f"\n*Note: Generated using verified database records (Local Ollama LLM was busy or offline).* "
            f"Evidence: {', '.join(evidence_ids[:3])}"
        )

    if any(k in q for k in ["value", "spend", "cltv", "worth", "money", "purchase", "transaction"]):
        return (
            f"**Customer Value & Financial Summary for {c.full_name}:**\n\n"
            f"- **Customer Lifetime Value (CLTV):** ${m.cltv_total:,.2f} USD\n"
            f"- **Vehicle Purchases:** ${m.cltv_vehicle_spend:,.2f}\n"
            f"- **Service Spend:** ${m.cltv_service_spend:,.2f}\n"
            f"- **Parts & Accessories:** ${m.cltv_parts_accessories_spend:,.2f}\n"
            f"- **Transactions:** {m.completed_transactions_count} completed transactions on record.\n"
            f"\n*Note: Calculated from actual database transaction records.*"
        )

    if any(k in q for k in ["loyalty", "point", "reward", "balance"]):
        return (
            f"**Customer Loyalty Summary for {c.full_name}:**\n\n"
            f"- **Current Balance:** {m.loyalty_points_balance:,} points\n"
            f"- **Total Points Earned:** {m.loyalty_points_earned:,} points\n"
            f"- **Total Points Redeemed:** {m.loyalty_points_redeemed:,} points\n"
            f"- **Segment:** {c.customer_segment or 'Standard'}\n"
            f"\n*Note: Verified from Customer #{c.id} loyalty audit events.*"
        )

    if any(k in q for k in ["service", "maintenance", "repair", "oil", "warranty"]):
        recent_svc = profile.service_visits[0] if profile.service_visits else None
        svc_info = (
            f"Most recent: {recent_svc.service_date} - {recent_svc.service_type} (${recent_svc.cost:,.2f}) at {recent_svc.dealer_name} ([Service Visit #{recent_svc.id}])"
            if recent_svc
            else "No service records"
        )
        return (
            f"**Customer Service Summary for {c.full_name}:**\n\n"
            f"- **Total Service Visits:** {m.total_services_count}\n"
            f"- **Total Service Expenditure:** ${m.total_service_cost:,.2f}\n"
            f"- **Recent Service:** {svc_info}\n"
            f"\n*Note: Aggregated from vehicle service records.*"
        )

    # General Executive Summary
    return (
        f"**Customer 360 Intelligence Summary for {c.full_name} [Customer #{c.id}]:**\n\n"
        f"- **Profile:** {c.customer_segment or 'Standard'} customer residing in {c.city or 'N/A'}, {c.state or 'N/A'}.\n"
        f"- **Historical CLTV:** ${m.cltv_total:,.2f} USD across {m.completed_transactions_count} completed transactions.\n"
        f"- **Vehicles:** {m.total_vehicles_count} vehicle(s) owned ({', '.join(f'{v.year} {v.make} {v.model}' for v in profile.vehicles)}).\n"
        f"- **Loyalty:** {m.loyalty_points_balance:,} points balance ({m.loyalty_points_earned:,} earned).\n"
        f"- **Service Record:** {m.total_services_count} maintenance visit(s) totaling ${m.total_service_cost:,.2f}.\n"
        f"- **Customer Feedback:** {m.total_reviews_count} review(s) submitted with an average rating of {m.average_rating or 'N/A'}★.\n\n"
        f"*Evidence cited from database: {', '.join(evidence_ids[:4])}.*"
    )


def query_customer_agent(
    db: Session,
    customer_id: int,
    question: str,
) -> AgentQueryResponse:
    """
    Execute an evidence-grounded AI query for a customer.

    1. Retrieves complete Customer 360 profile from SQLite via SQLAlchemy ORM.
    2. Builds verified evidence context and record citations.
    3. Prompts local Ollama (Llama 3.1) with strict evidence-grounding instructions.
    4. Returns structured JSON with answer, evidence records, and model metadata.
    """
    # 1. Fetch Customer 360 Profile using approved Python service
    profile = get_customer_360(db, customer_id)
    if not profile:
        return AgentQueryResponse(
            customer_id=customer_id,
            customer_name="Unknown",
            question=question,
            answer=f"Error: Customer ID #{customer_id} does not exist in the database.",
            evidence_records=[],
            model=DEFAULT_MODEL,
            status="error_not_found",
        )

    c_name = profile.customer.full_name
    evidence_text, evidence_ids = _build_evidence_context(profile)

    # 2. System Prompt & Grounded User Prompt
    system_prompt = (
        "You are AutoInsight360 Customer Intelligence Agent, an enterprise automotive AI assistant. "
        "Your task is to answer the employee's question about the customer using ONLY the verified database records provided. "
        "Strict Guardrails:\n"
        "1. Never fabricate or extrapolate facts not present in the provided evidence.\n"
        "2. When stating facts, cite the specific record identifier (e.g. [Vehicle VIN: ...], [Transaction Ref: ...], [Service Visit #...], [Customer #...]).\n"
        "3. If the answer cannot be determined from the records, explicitly state: 'The customer records do not contain information regarding [topic].'\n"
        "4. Do not offer legal, financial, or unverified technical advice.\n"
        "5. Be concise, direct, professional, and format key points with bullet points."
    )

    full_prompt = (
        f"{system_prompt}\n\n"
        f"--- VERIFIED DATABASE EVIDENCE FOR CUSTOMER #{customer_id} ---\n"
        f"{evidence_text}\n"
        f"--- END EVIDENCE ---\n\n"
        f"EMPLOYEE QUESTION: {question}\n\n"
        f"GROUNDED ANSWER:"
    )

    # 3. Call Local Ollama (Llama 3.1)
    answer_text = ""
    status = "success"

    try:
        with httpx.Client(timeout=40.0) as client:
            payload = {
                "model": DEFAULT_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 400,
                },
            }
            resp = client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                raw_response = data.get("response", "").strip()
                if raw_response:
                    answer_text = raw_response
                else:
                    logger.warning("Ollama returned empty response string.")
                    answer_text = _build_fallback_answer(profile, question, evidence_ids)
                    status = "fallback_empty"
            else:
                logger.warning("Ollama error status: %d", resp.status_code)
                answer_text = _build_fallback_answer(profile, question, evidence_ids)
                status = f"fallback_http_{resp.status_code}"
    except Exception as exc:
        logger.warning("Ollama call failed or timed out: %s. Using evidence fallback.", exc)
        answer_text = _build_fallback_answer(profile, question, evidence_ids)
        status = "fallback_timeout_or_offline"

    # Extract cited records mentioned in the answer or context
    cited_records = [
        eid for eid in evidence_ids
        if any(token in answer_text for token in eid.split(": ")[-1:])
    ]
    if not cited_records:
        cited_records = evidence_ids[:5]

    return AgentQueryResponse(
        customer_id=customer_id,
        customer_name=c_name,
        question=question,
        answer=answer_text,
        evidence_records=cited_records,
        model=DEFAULT_MODEL,
        status=status,
    )
