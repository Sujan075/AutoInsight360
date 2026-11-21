"""
AutoInsight360 - AI Agents Package
===================================
Evidence-grounded AI agent using local Ollama (Llama 3.1).
"""

from .customer_agent import query_customer_agent, check_ollama_status

__all__ = [
    "query_customer_agent",
    "check_ollama_status",
]
