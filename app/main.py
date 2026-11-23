import logging
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from .agent import run_agent
from .db import engine, get_session, init_db
from .models import Incident, SupportTicket
from .rag import collection, get_knowledge_stats, ingest
from .schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    IncidentResponse,
    ServiceStatusItem,
    TicketCreateRequest,
    TicketResponse,
)
from .tools import create_ticket, list_all_services

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables are created
    logger.info("Initializing Enterprise IT Support database...")
    init_db()
    yield
    # Shutdown logic if needed
    logger.info("Application shutdown.")


app = FastAPI(
    title="Enterprise IT Support RAG Agent",
    description="Intelligent AI Agent for enterprise IT support with RAG, incident search, service health, and automated ticketing.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for cross-origin frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check(session: Session = Depends(get_session)):
    """Health check endpoint indicating database connectivity and Chroma status."""
    try:
        session.exec(select(Incident).limit(1))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {e}"

    chroma_count = 0
    try:
        chroma_count = collection.count()
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        database=db_status,
        chroma_chunks=chroma_count,
        version="1.0.0",
    )


@app.post("/chat", response_model=ChatResponse, tags=["Agent"])
def chat(req: ChatRequest):
    """
    Main conversational IT Support endpoint.
    Retrieves internal docs, checks incidents & service status, and escalates tickets.
    """
    return run_agent(req)


@app.get("/services", response_model=List[ServiceStatusItem], tags=["Services"])
def get_services():
    """Retrieve the real-time operational status of all monitored corporate services."""
    services = list_all_services()
    return [
        ServiceStatusItem(
            service=s["service"],
            status=s["status"],
            message=s["message"],
            latency_ms=s.get("latency_ms"),
        )
        for s in services
    ]


@app.get("/incidents", response_model=List[IncidentResponse], tags=["Incidents"])
def get_incidents(
    department: Optional[str] = Query(default=None, description="Filter by department"),
    session: Session = Depends(get_session),
):
    """Query historical resolved IT incidents."""
    statement = select(Incident).order_by(Incident.created_at.desc())
    if department and department.lower() != "all":
        statement = statement.where(
            (Incident.department == department.lower()) | (Incident.department == "all")
        )
    incidents = session.exec(statement).all()
    return [
        IncidentResponse(
            ticket_id=i.ticket_id,
            title=i.title,
            description=i.description,
            resolution=i.resolution,
            department=i.department,
            status=i.status,
        )
        for i in incidents
    ]


@app.get("/tickets", response_model=List[TicketResponse], tags=["Ticketing"])
def get_tickets(
    user_id: Optional[str] = Query(default=None, description="Filter by user ID"),
    department: Optional[str] = Query(default=None, description="Filter by department"),
    session: Session = Depends(get_session),
):
    """List support tickets with optional filtering."""
    statement = select(SupportTicket).order_by(SupportTicket.created_at.desc())
    if user_id:
        statement = statement.where(SupportTicket.user_id == user_id)
    if department and department.lower() != "all":
        statement = statement.where(SupportTicket.department == department.lower())
    tickets = session.exec(statement).all()
    return [
        TicketResponse(
            ticket_id=t.ticket_id,
            user_id=t.user_id,
            department=t.department,
            title=t.title,
            description=t.description,
            priority=t.priority,
            status=t.status,
            created_at=t.created_at,
        )
        for t in tickets
    ]


@app.post("/tickets", response_model=TicketResponse, tags=["Ticketing"])
def create_support_ticket(req: TicketCreateRequest):
    """Manually create an official IT support ticket."""
    result = create_ticket(
        user_id=req.user_id,
        department=req.department,
        title=req.title,
        description=req.description,
        priority=req.priority,
    )
    with Session(engine) as session:
        ticket = session.exec(
            select(SupportTicket).where(SupportTicket.ticket_id == result["ticket_id"])
        ).first()
    if not ticket:
        raise HTTPException(status_code=500, detail="Failed to retrieve created ticket.")
    return TicketResponse(
        ticket_id=ticket.ticket_id,
        user_id=ticket.user_id,
        department=ticket.department,
        title=ticket.title,
        description=ticket.description,
        priority=ticket.priority,
        status=ticket.status,
        created_at=ticket.created_at,
    )


@app.get("/tickets/{ticket_id}", response_model=TicketResponse, tags=["Ticketing"])
def get_ticket_detail(ticket_id: str, session: Session = Depends(get_session)):
    """Fetch details of a specific support ticket by ticket ID."""
    ticket = session.exec(
        select(SupportTicket).where(SupportTicket.ticket_id == ticket_id)
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketResponse(
        ticket_id=ticket.ticket_id,
        user_id=ticket.user_id,
        department=ticket.department,
        title=ticket.title,
        description=ticket.description,
        priority=ticket.priority,
        status=ticket.status,
        created_at=ticket.created_at,
    )


@app.get("/knowledge/stats", tags=["Knowledge"])
def knowledge_stats():
    """Retrieve vector knowledge base statistics."""
    return get_knowledge_stats()


@app.post("/knowledge/ingest", tags=["Knowledge"])
def trigger_ingest():
    """Trigger re-ingestion of data/docs into vector storage."""
    count = ingest()
    return {"status": "success", "chunks_ingested": count}


@app.get("/", response_class=HTMLResponse, tags=["UI"])
def web_ui():
    """Serve the interactive Enterprise IT Support Web Portal."""
    return HTML_UI_CONTENT


HTML_UI_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise IT Support - AI Helpdesk</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .custom-scroll::-webkit-scrollbar { width: 6px; }
        .custom-scroll::-webkit-scrollbar-track { background: #1e293b; }
        .custom-scroll::-webkit-scrollbar-thumb { background: #3b82f6; border-radius: 3px; }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">
    <!-- Header -->
    <header class="bg-slate-900 border-b border-slate-800 px-6 py-4 flex flex-wrap items-center justify-between shadow-md">
        <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
                <i class="fa-solid fa-headset text-xl"></i>
            </div>
            <div>
                <h1 class="font-bold text-lg text-white tracking-wide">Enterprise IT Support</h1>
                <p class="text-xs text-slate-400">Autonomous RAG Agent & Incident Resolution</p>
            </div>
        </div>
        <div class="flex items-center space-x-4 mt-2 sm:mt-0">
            <div class="flex items-center bg-slate-800/80 rounded-lg px-3 py-1.5 border border-slate-700">
                <i class="fa-solid fa-building text-slate-400 text-xs mr-2"></i>
                <select id="departmentSelect" class="bg-transparent text-sm text-slate-200 focus:outline-none">
                    <option value="all" class="bg-slate-900">Department: All</option>
                    <option value="engineering" class="bg-slate-900" selected>Engineering</option>
                    <option value="it" class="bg-slate-900">IT / Admin</option>
                    <option value="hr" class="bg-slate-900">HR & People</option>
                    <option value="finance" class="bg-slate-900">Finance</option>
                    <option value="sales" class="bg-slate-900">Sales</option>
                </select>
            </div>
            <a href="/docs" target="_blank" class="text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-2 rounded-lg font-medium transition flex items-center shadow-sm">
                <i class="fa-solid fa-code text-xs mr-1.5"></i> API Docs
            </a>
        </div>
    </header>

    <!-- Main Container -->
    <main class="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-4 gap-6">
        <!-- Left Sidebar: Services & Quick Prompts -->
        <div class="lg:col-span-1 space-y-5">
            <!-- Service Health Widget -->
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-sm">
                <div class="flex items-center justify-between mb-3">
                    <h2 class="text-sm font-semibold text-slate-200 flex items-center">
                        <i class="fa-solid fa-server text-blue-400 mr-2 text-xs"></i> Service Health
                    </h2>
                    <span class="inline-flex items-center text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded-full">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1 animate-pulse"></span> Live
                    </span>
                </div>
                <div id="servicesList" class="space-y-2 text-xs">
                    <div class="text-slate-500 animate-pulse">Loading service status...</div>
                </div>
            </div>

            <!-- Quick Troubleshoot Prompts -->
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-sm">
                <h2 class="text-sm font-semibold text-slate-200 mb-3 flex items-center">
                    <i class="fa-solid fa-bolt text-amber-400 mr-2 text-xs"></i> Quick Prompts
                </h2>
                <div class="space-y-2">
                    <button onclick="setPrompt('VPN is connected but GitLab is unreachable.')" class="w-full text-left text-xs bg-slate-800/60 hover:bg-slate-800 text-slate-300 p-2.5 rounded-xl border border-slate-700/60 transition flex items-center">
                        <i class="fa-solid fa-network-wired text-blue-400 mr-2"></i> VPN & GitLab Unreachable
                    </button>
                    <button onclick="setPrompt('How do I reset my Okta MFA push notifications?')" class="w-full text-left text-xs bg-slate-800/60 hover:bg-slate-800 text-slate-300 p-2.5 rounded-xl border border-slate-700/60 transition flex items-center">
                        <i class="fa-solid fa-key text-emerald-400 mr-2"></i> Okta MFA Reset
                    </button>
                    <button onclick="setPrompt('How do I request a Docker Desktop license?')" class="w-full text-left text-xs bg-slate-800/60 hover:bg-slate-800 text-slate-300 p-2.5 rounded-xl border border-slate-700/60 transition flex items-center">
                        <i class="fa-brands fa-docker text-cyan-400 mr-2"></i> Request Docker License
                    </button>
                    <button onclick="setPrompt('I received a suspicious phishing email. What should I do?')" class="w-full text-left text-xs bg-slate-800/60 hover:bg-slate-800 text-slate-300 p-2.5 rounded-xl border border-slate-700/60 transition flex items-center">
                        <i class="fa-solid fa-shield-halved text-rose-400 mr-2"></i> Report Phishing Email
                    </button>
                    <button onclick="setPrompt('Internal DNS resolution fails after connecting to Wi-Fi.')" class="w-full text-left text-xs bg-slate-800/60 hover:bg-slate-800 text-slate-300 p-2.5 rounded-xl border border-slate-700/60 transition flex items-center">
                        <i class="fa-solid fa-wifi text-indigo-400 mr-2"></i> Corporate Wi-Fi & DNS
                    </button>
                </div>
            </div>

            <!-- Escalated Tickets Box -->
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-sm">
                <div class="flex items-center justify-between mb-3">
                    <h2 class="text-sm font-semibold text-slate-200 flex items-center">
                        <i class="fa-solid fa-ticket text-purple-400 mr-2 text-xs"></i> Recent Tickets
                    </h2>
                    <button onclick="fetchTickets()" class="text-slate-400 hover:text-white text-xs">
                        <i class="fa-solid fa-rotate-right"></i>
                    </button>
                </div>
                <div id="ticketsList" class="space-y-2 text-xs max-h-40 overflow-y-auto custom-scroll">
                    <div class="text-slate-500">No recent tickets yet.</div>
                </div>
            </div>
        </div>

        <!-- Chat Area -->
        <div class="lg:col-span-3 flex flex-col bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl min-h-[550px] max-h-[82vh]">
            <!-- Chat Messages Log -->
            <div id="chatBox" class="flex-1 p-5 overflow-y-auto custom-scroll space-y-4">
                <div class="flex items-start space-x-3">
                    <div class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shrink-0">
                        <i class="fa-solid fa-robot text-sm"></i>
                    </div>
                    <div class="bg-slate-800/90 border border-slate-700/60 rounded-2xl rounded-tl-none p-4 max-w-2xl text-sm leading-relaxed">
                        <p class="font-semibold text-blue-400 mb-1">IT Support AI Agent</p>
                        <p class="text-slate-200">Hello! I am your Enterprise IT Support assistant. I can diagnose network & VPN issues, search internal documentation and historical incidents, check service availability, and escalate support tickets when needed. How can I help you today?</p>
                    </div>
                </div>
            </div>

            <!-- Input Box -->
            <div class="p-4 bg-slate-900/95 border-t border-slate-800">
                <form id="chatForm" class="flex items-center space-x-3">
                    <input id="messageInput" type="text" placeholder="Type your IT issue (e.g. 'VPN is connected but GitLab is unreachable')..." 
                           class="flex-1 bg-slate-800 text-slate-100 placeholder-slate-500 text-sm rounded-xl px-4 py-3 border border-slate-700 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition" />
                    <button type="submit" id="sendBtn" class="bg-blue-600 hover:bg-blue-500 text-white px-5 py-3 rounded-xl font-medium text-sm transition flex items-center shadow-lg shadow-blue-600/30">
                        <span>Send</span>
                        <i class="fa-solid fa-paper-plane ml-2 text-xs"></i>
                    </button>
                </form>
            </div>
        </div>
    </main>

    <footer class="bg-slate-900 border-t border-slate-800 py-3 text-center text-xs text-slate-500">
        Enterprise IT Support RAG System • FastAPI • ChromaDB • SQLModel • Multi-Department RBAC
    </footer>

    <script>
        const chatBox = document.getElementById('chatBox');
        const chatForm = document.getElementById('chatForm');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const departmentSelect = document.getElementById('departmentSelect');
        const servicesList = document.getElementById('servicesList');
        const ticketsList = document.getElementById('ticketsList');

        const conversationId = 'session_' + Math.random().toString(36).substring(2, 9);
        const userId = 'employee_' + Math.random().toString(36).substring(2, 6);

        function setPrompt(text) {
            messageInput.value = text;
            messageInput.focus();
        }

        async function fetchServices() {
            try {
                const res = await fetch('/services');
                const data = await res.json();
                servicesList.innerHTML = '';
                data.forEach(s => {
                    const isOperational = s.status === 'operational';
                    const iconColor = isOperational ? 'text-emerald-400' : 'text-amber-400';
                    const badge = isOperational 
                        ? '<span class="text-[10px] text-emerald-400 bg-emerald-950/70 border border-emerald-800/60 px-1.5 py-0.5 rounded">Operational</span>'
                        : '<span class="text-[10px] text-amber-400 bg-amber-950/70 border border-amber-800/60 px-1.5 py-0.5 rounded">' + s.status + '</span>';
                    
                    servicesList.innerHTML += `
                        <div class="flex items-center justify-between p-2 rounded-lg bg-slate-800/40 border border-slate-800 hover:border-slate-700 transition">
                            <div class="flex items-center truncate mr-2">
                                <i class="fa-solid fa-circle text-[7px] ${iconColor} mr-2"></i>
                                <span class="font-medium text-slate-300 truncate">${s.service}</span>
                            </div>
                            ${badge}
                        </div>
                    `;
                });
            } catch (err) {
                servicesList.innerHTML = '<div class="text-rose-400">Error loading services</div>';
            }
        }

        async function fetchTickets() {
            try {
                const res = await fetch('/tickets');
                const data = await res.json();
                if (!data || data.length === 0) {
                    ticketsList.innerHTML = '<div class="text-slate-500">No tickets found.</div>';
                    return;
                }
                ticketsList.innerHTML = '';
                data.slice(0, 5).forEach(t => {
                    ticketsList.innerHTML += `
                        <div class="p-2 rounded-lg bg-slate-800/50 border border-slate-700/60">
                            <div class="flex justify-between items-center text-[11px] mb-1">
                                <span class="font-mono text-blue-400 font-bold">${t.ticket_id}</span>
                                <span class="text-[9px] uppercase px-1.5 py-0.2 rounded bg-slate-700 text-slate-300">${t.status}</span>
                            </div>
                            <div class="text-[11px] text-slate-300 truncate">${t.title}</div>
                        </div>
                    `;
                });
            } catch (err) {
                ticketsList.innerHTML = '<div class="text-slate-500">Failed to load tickets.</div>';
            }
        }

        function appendMessage(role, text, citations = [], toolsUsed = [], ticketId = null) {
            const isUser = role === 'user';
            const msgDiv = document.createElement('div');
            msgDiv.className = `flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`;

            const iconDiv = document.createElement('div');
            iconDiv.className = `w-8 h-8 rounded-lg flex items-center justify-center text-white shrink-0 ${isUser ? 'bg-indigo-600' : 'bg-blue-600'}`;
            iconDiv.innerHTML = isUser ? '<i class="fa-solid fa-user text-sm"></i>' : '<i class="fa-solid fa-robot text-sm"></i>';

            const contentDiv = document.createElement('div');
            contentDiv.className = `max-w-2xl text-sm leading-relaxed p-4 rounded-2xl ${isUser ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-slate-800/90 text-slate-200 border border-slate-700/60 rounded-tl-none'}`;

            if (!isUser) {
                let toolsHtml = '';
                if (toolsUsed && toolsUsed.length > 0) {
                    toolsHtml = `<div class="mb-2 flex flex-wrap gap-1.5">` + 
                        toolsUsed.map(t => `<span class="inline-flex items-center text-[10px] bg-blue-950/80 text-blue-300 border border-blue-800/60 px-2 py-0.5 rounded-full"><i class="fa-solid fa-wrench mr-1 text-[8px]"></i>${t}</span>`).join('') +
                        `</div>`;
                }

                let ticketHtml = '';
                if (ticketId) {
                    ticketHtml = `
                        <div class="my-2.5 p-3 rounded-xl bg-purple-950/60 border border-purple-800/80 text-purple-200 flex items-center justify-between">
                            <div class="flex items-center">
                                <i class="fa-solid fa-ticket text-purple-400 mr-2 text-base"></i>
                                <div>
                                    <div class="text-xs font-bold text-white">Ticket Escalated: ${ticketId}</div>
                                    <div class="text-[10px] text-purple-300">An IT technician has been assigned.</div>
                                </div>
                            </div>
                        </div>
                    `;
                }

                let citationsHtml = '';
                if (citations && citations.length > 0) {
                    citationsHtml = `<div class="mt-3 pt-2.5 border-t border-slate-700/80"><div class="text-[11px] font-semibold text-slate-400 mb-1 flex items-center"><i class="fa-solid fa-book-open mr-1.5 text-xs text-blue-400"></i> Referenced Knowledge:</div><div class="space-y-1">` +
                        citations.map(c => `<div class="text-[11px] bg-slate-900/80 p-2 rounded-lg border border-slate-700/50"><span class="font-mono text-blue-300 font-semibold">[${c.source}]</span> <span class="text-slate-400">${c.text.substring(0, 160)}...</span></div>`).join('') +
                        `</div></div>`;
                }

                contentDiv.innerHTML = `
                    <p class="font-semibold text-blue-400 text-xs mb-1">IT Support AI Agent</p>
                    ${toolsHtml}
                    <div class="whitespace-pre-line text-slate-200">${text}</div>
                    ${ticketHtml}
                    ${citationsHtml}
                `;
            } else {
                contentDiv.textContent = text;
            }

            msgDiv.appendChild(iconDiv);
            msgDiv.appendChild(contentDiv);
            chatBox.appendChild(msgDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (!message) return;

            appendMessage('user', message);
            messageInput.value = '';
            messageInput.disabled = true;
            sendBtn.disabled = true;
            sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-sm"></i>';

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        department: departmentSelect.value,
                        message: message,
                        conversation_id: conversationId,
                    })
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Server error');
                }

                const data = await response.json();
                appendMessage('assistant', data.answer, data.citations, data.tools_used, data.escalated_ticket_id);

                if (data.escalated_ticket_id) {
                    fetchTickets();
                }
            } catch (err) {
                appendMessage('assistant', 'Sorry, I encountered an issue processing your request: ' + err.message);
            } finally {
                messageInput.disabled = false;
                sendBtn.disabled = false;
                sendBtn.innerHTML = '<span>Send</span><i class="fa-solid fa-paper-plane ml-2 text-xs"></i>';
                messageInput.focus();
            }
        });

        // Initialize UI components
        fetchServices();
        fetchTickets();
    </script>
</body>
</html>
"""
