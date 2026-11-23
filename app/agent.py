import json
import logging
from typing import Any, Dict, List, Optional
from sqlmodel import Session, select

from .config import settings
from .db import engine
from .models import ConversationMessage
from .schemas import ChatRequest, ChatResponse, Citation
from .tools import (
    create_ticket,
    incident_search,
    knowledge_base_search,
    list_user_tickets,
    service_status,
    web_search,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert enterprise IT support AI assistant for corporate employees.
Your job is to diagnose technical issues, guide users through step-by-step solutions, and escalate issues when necessary.

Guidelines:
1. Always prefer internal knowledge base documents and historical resolved incidents over public web information.
2. Respect department permissions: pass the user's department to internal search tools.
3. Check service health when users report connectivity or service disruption issues (VPN, GitLab, Jira, Okta, etc.).
4. When citing internal documents, always mention the source clearly in format: [source: filename].
5. Escalate and create a ticket ONLY when the user explicitly requests escalation, or when an issue requires IT technician intervention (e.g. hardware replacement, admin access grant, account unlock).
6. Be concise, structured, professional, and actionable. Provide numbered troubleshooting steps.
"""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "knowledge_base_search",
            "description": "Search authorized internal IT documentation, SOPs, and troubleshooting guides.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords or question describing the technical problem.",
                    },
                    "department": {
                        "type": "string",
                        "description": "Department name to enforce access control (e.g. engineering, it, hr, sales, finance, all).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "incident_search",
            "description": "Search database of past resolved IT incidents for precedent solutions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Issue description or keywords to match against historical tickets.",
                    },
                    "department": {
                        "type": "string",
                        "description": "Department filter for incident records.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "service_status",
            "description": "Check the real-time operational status and latency of internal and corporate services.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Name of service to check (e.g. vpn, gitlab, jira, okta, slack, aws, github, zoom, email).",
                    },
                },
                "required": ["service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Escalate the issue to the IT Helpdesk by creating an official support ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Brief summary of the issue.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description including steps taken and current symptoms.",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Impact and urgency level.",
                    },
                },
                "required": ["title", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_user_tickets",
            "description": "List existing tickets created by the current user to check ticket status.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the public web for technical documentation, library issues, or vendor vendor advisories when internal sources are insufficient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Web search query.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

AVAILABLE_FUNCTIONS = {
    "knowledge_base_search": knowledge_base_search,
    "incident_search": incident_search,
    "service_status": service_status,
    "create_ticket": create_ticket,
    "list_user_tickets": list_user_tickets,
    "web_search": web_search,
}


def get_conversation_history(conversation_id: str, limit: int = 12) -> List[Dict[str, str]]:
    """Retrieve recent conversation history from database."""
    with Session(engine) as session:
        statement = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at)
        )
        records = session.exec(statement).all()

    return [{"role": msg.role, "content": msg.content} for msg in records[-limit:]]


def save_message(conversation_id: str, user_id: str, role: str, content: str) -> None:
    """Store conversation turn into SQLite."""
    with Session(engine) as session:
        message = ConversationMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
        )
        session.add(message)
        session.commit()


def run_mock_agent(req: ChatRequest) -> ChatResponse:
    """
    Fallback agent when OpenAI API key is not configured or mock mode is enabled.
    Performs deterministic tool execution (RAG + Incidents + Service status) and builds answer.
    """
    tools_used: List[str] = []
    citations: List[Citation] = []
    escalated_ticket: Optional[str] = None

    # Check service status if user mentions a service
    msg_lower = req.message.lower()
    services_to_check = ["vpn", "gitlab", "jira", "okta", "slack", "aws", "github", "zoom", "email"]
    service_info = []
    for s in services_to_check:
        if s in msg_lower:
            status = service_status(s)
            tools_used.append("service_status")
            service_info.append(f"• **{status['service']}**: {status['status'].upper()} - {status['message']}")

    # Knowledge base search
    kb_results = knowledge_base_search(req.message, department=req.department)
    if kb_results:
        tools_used.append("knowledge_base_search")
        for r in kb_results:
            citations.append(Citation(source=r["source"], text=r["text"][:300]))

    # Incident search
    inc_results = incident_search(req.message, department=req.department)
    if inc_results:
        tools_used.append("incident_search")

    # Check for escalation request
    if any(kw in msg_lower for kw in ["escalate", "create ticket", "open ticket", "raise ticket"]):
        ticket = create_ticket(
            user_id=req.user_id,
            department=req.department,
            title=f"Support Request from {req.user_id}: {req.message[:50]}",
            description=req.message,
            priority="medium",
        )
        tools_used.append("create_ticket")
        escalated_ticket = ticket["ticket_id"]

    # Construct synthesized answer
    sections = [
        f"**Enterprise IT Support Agent** *(Offline/Mock Mode)*\n\n"
        f"I received your inquiry for department `{req.department}`: \"{req.message}\""
    ]

    if service_info:
        sections.append("### Service Health Status\n" + "\n".join(service_info))

    if kb_results:
        sections.append("### Relevant Knowledge Base Guidance")
        for res in kb_results[:2]:
            sections.append(f"- **[source: {res['source']}]**\n> {res['text'][:400]}...")

    if inc_results:
        sections.append("### Historical Incident Precedents")
        for inc in inc_results[:2]:
            sections.append(f"- **{inc['ticket_id']} ({inc['title']})**: Resolution: *{inc['resolution']}*")

    if escalated_ticket:
        sections.append(f"\n🚨 **Support Ticket Created**: Ticket ID `{escalated_ticket}` has been opened for the IT Helpdesk.")
    elif not kb_results and not inc_results and not service_info:
        sections.append("\nNo exact internal match found. Suggested next steps:\n1. Verify your network connection and corporate VPN profile.\n2. Check Single Sign-On credentials in Okta.\n3. Type 'escalate' or 'create ticket' if you would like me to open a support ticket for our IT team.")

    answer_text = "\n\n".join(sections)
    save_message(req.conversation_id, req.user_id, "user", req.message)
    save_message(req.conversation_id, req.user_id, "assistant", answer_text)

    return ChatResponse(
        answer=answer_text,
        citations=citations,
        tools_used=list(set(tools_used)),
        escalated_ticket_id=escalated_ticket,
    )


def run_agent(req: ChatRequest) -> ChatResponse:
    """
    Main entrypoint for agent execution.
    Runs OpenAI tool-calling loop or mock fallback.
    """
    # If no OpenAI key or mock requested, use the robust mock agent
    if not settings.openai_api_key or settings.enable_mock_llm:
        return run_mock_agent(req)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
    except Exception as e:
        logger.error("Failed to initialize OpenAI client: %s", e)
        return run_mock_agent(req)

    # Prepare message thread
    history = get_conversation_history(req.conversation_id)
    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": req.message})

    tools_used: List[str] = []
    citations: List[Citation] = []
    escalated_ticket_id: Optional[str] = None

    for round_num in range(settings.max_tool_rounds):
        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.2,
            )
        except Exception as e:
            logger.error("Error calling OpenAI chat completion: %s", e)
            return ChatResponse(
                answer=f"An error occurred while communicating with the AI service: {str(e)}. Please check your API key configuration.",
                citations=citations,
                tools_used=tools_used,
                escalated_ticket_id=escalated_ticket_id,
            )

        assistant_msg = response.choices[0].message

        # Convert OpenAI message to dict format for continuing conversation
        msg_dict: Dict[str, Any] = {
            "role": "assistant",
            "content": assistant_msg.content or "",
        }
        if assistant_msg.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant_msg.tool_calls
            ]

        messages.append(msg_dict)

        # If model generated a direct text response without tool calls, finish
        if not assistant_msg.tool_calls:
            final_answer = assistant_msg.content or "I could not produce an answer."
            save_message(req.conversation_id, req.user_id, "user", req.message)
            save_message(req.conversation_id, req.user_id, "assistant", final_answer)
            return ChatResponse(
                answer=final_answer,
                citations=citations,
                tools_used=list(set(tools_used)),
                escalated_ticket_id=escalated_ticket_id,
            )

        # Execute each requested tool call
        for tool_call in assistant_msg.tool_calls:
            func_name = tool_call.function.name
            tools_used.append(func_name)

            try:
                raw_args = tool_call.function.arguments or "{}"
                call_args = json.loads(raw_args)
            except Exception:
                call_args = {}

            # Inject contextual parameters
            if func_name in {"knowledge_base_search", "incident_search"}:
                call_args.setdefault("department", req.department)
            elif func_name == "create_ticket":
                call_args.setdefault("user_id", req.user_id)
                call_args.setdefault("department", req.department)
            elif func_name == "list_user_tickets":
                call_args.setdefault("user_id", req.user_id)

            func = AVAILABLE_FUNCTIONS.get(func_name)
            if not func:
                result = {"error": f"Tool '{func_name}' is not recognized."}
            else:
                try:
                    result = func(**call_args)
                except Exception as ex:
                    logger.exception("Error executing tool %s: %s", func_name, ex)
                    result = {"error": f"Execution error in tool {func_name}: {str(ex)}"}

            # Collect citations and ticket escalations
            if func_name == "knowledge_base_search" and isinstance(result, list):
                for item in result:
                    if isinstance(item, dict) and "source" in item:
                        citations.append(
                            Citation(
                                source=item["source"],
                                text=item.get("text", "")[:400],
                            )
                        )

            if func_name == "create_ticket" and isinstance(result, dict):
                escalated_ticket_id = result.get("ticket_id")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    limit_answer = (
        "I could not complete the investigation within the tool-call limit. "
        "Please specify your query in more detail or request ticket escalation."
    )
    save_message(req.conversation_id, req.user_id, "user", req.message)
    save_message(req.conversation_id, req.user_id, "assistant", limit_answer)

    return ChatResponse(
        answer=limit_answer,
        citations=citations,
        tools_used=list(set(tools_used)),
        escalated_ticket_id=escalated_ticket_id,
    )
