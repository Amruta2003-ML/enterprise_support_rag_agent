import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlmodel import Session, select

from .config import settings
from .db import engine
from .models import Incident, SupportTicket
from .rag import search as rag_search

logger = logging.getLogger(__name__)

# Enterprise Services Catalog
SERVICE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "vpn": {
        "service": "VPN Gateway (GlobalProtect / WireGuard)",
        "status": "operational",
        "message": "All corporate VPN concentrators are operational with 99.98% uptime.",
        "latency_ms": 18,
    },
    "gitlab": {
        "service": "Internal GitLab & CI/CD Runners",
        "status": "operational",
        "message": "GitLab enterprise instance and shared runner fleet are fully functional.",
        "latency_ms": 24,
    },
    "jira": {
        "service": "Atlassian Jira & Confluence",
        "status": "operational",
        "message": "Jira Service Management and Confluence cloud services operational.",
        "latency_ms": 45,
    },
    "okta": {
        "service": "Okta SSO & Identity Provider",
        "status": "operational",
        "message": "Single Sign-On, MFA push notification, and directory sync operating normally.",
        "latency_ms": 15,
    },
    "slack": {
        "service": "Enterprise Slack Workspace",
        "status": "operational",
        "message": "Corporate messaging and integrations operational.",
        "latency_ms": 30,
    },
    "aws": {
        "service": "AWS Cloud Infrastructure & IAM",
        "status": "operational",
        "message": "Production VPCs, Direct Connect, and IAM roles operational.",
        "latency_ms": 12,
    },
    "github": {
        "service": "GitHub Enterprise Cloud",
        "status": "operational",
        "message": "GitHub repositories and Actions runners reachable.",
        "latency_ms": 35,
    },
    "email": {
        "service": "Google Workspace / M365 Corporate Mail",
        "status": "operational",
        "message": "Corporate email routing, calendar, and spam filtering active.",
        "latency_ms": 20,
    },
    "zoom": {
        "service": "Zoom Corporate Video Conferencing",
        "status": "operational",
        "message": "Conference rooms and Zoom Phone systems functioning normally.",
        "latency_ms": 22,
    },
}


def knowledge_base_search(query: str, department: str = "all") -> List[Dict[str, str]]:
    """
    Search internal IT documentation vectors matching the query and user's department permissions.
    """
    return rag_search(query=query, department=department)


def incident_search(query: str, department: str = "all") -> List[Dict[str, Any]]:
    """
    Search historical resolved IT incidents in the database for precedent solutions.
    """
    dept_lower = (department or "all").lower()

    with Session(engine) as session:
        statement = select(Incident).order_by(Incident.created_at.desc())
        all_incidents = session.exec(statement).all()

    # Filter by department scope
    applicable: List[Incident] = []
    for inc in all_incidents:
        inc_dept = (inc.department or "all").lower()
        if inc_dept in {"all", dept_lower} or dept_lower == "it":
            applicable.append(inc)

    terms = [term for term in query.lower().split() if len(term) > 2]
    matched_incidents: List[Dict[str, Any]] = []

    for item in applicable:
        haystack = f"{item.title} {item.description} {item.resolution}".lower()
        score = sum(1 for term in terms if term in haystack)
        if score > 0 or not terms:
            matched_incidents.append({
                "ticket_id": item.ticket_id,
                "title": item.title,
                "description": item.description,
                "resolution": item.resolution,
                "department": item.department,
                "status": item.status,
                "score": score,
            })

    matched_incidents.sort(key=lambda x: x["score"], reverse=True)
    return matched_incidents[:5]


def service_status(service: str) -> Dict[str, Any]:
    """
    Check the current health and status of an enterprise IT service.
    """
    key = service.strip().lower()
    for registered_key, info in SERVICE_REGISTRY.items():
        if registered_key in key or key in registered_key:
            return info

    return {
        "service": service,
        "status": "unknown",
        "message": f"Service '{service}' is not in the monitored enterprise registry.",
        "latency_ms": None,
    }


def list_all_services() -> List[Dict[str, Any]]:
    """Retrieve health and status of all monitored enterprise services."""
    return [
        {"key": k, **v}
        for k, v in SERVICE_REGISTRY.items()
    ]


def create_ticket(
    user_id: str,
    department: str,
    title: str,
    description: str,
    priority: str = "medium",
) -> Dict[str, Any]:
    """
    Escalate an issue and create an official IT support ticket.
    """
    ticket_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    valid_priorities = {"low", "medium", "high", "critical"}
    safe_priority = priority.lower() if priority.lower() in valid_priorities else "medium"

    with Session(engine) as session:
        new_ticket = SupportTicket(
            ticket_id=ticket_id,
            user_id=user_id,
            department=department,
            title=title,
            description=description,
            priority=safe_priority,
            status="open",
        )
        session.add(new_ticket)
        session.commit()
        session.refresh(new_ticket)

    logger.info("Created support ticket %s for user %s", ticket_id, user_id)
    return {
        "ticket_id": ticket_id,
        "status": "open",
        "priority": safe_priority,
        "message": f"Support ticket {ticket_id} created successfully and assigned to IT Helpdesk.",
    }


def list_user_tickets(user_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve open and recent support tickets for a specific employee.
    """
    with Session(engine) as session:
        statement = select(SupportTicket).where(
            SupportTicket.user_id == user_id
        ).order_by(SupportTicket.created_at.desc())
        tickets = session.exec(statement).all()

    return [
        {
            "ticket_id": t.ticket_id,
            "title": t.title,
            "description": t.description,
            "department": t.department,
            "priority": t.priority,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
        }
        for t in tickets
    ]


def web_search(query: str) -> List[Dict[str, Any]]:
    """
    Query the public web via Tavily API when internal documentation is insufficient.
    """
    if not settings.tavily_api_key:
        return [{"error": "Tavily web search is not configured (missing TAVILY_API_KEY in .env)."}]

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(query=query, max_results=5)
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
            }
            for item in response.get("results", [])
        ]
    except Exception as e:
        logger.error("Error during Tavily web search: %s", e)
        return [{"error": f"Web search failed: {str(e)}"}]
