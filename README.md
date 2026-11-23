# Enterprise IT Support RAG Agent

An autonomous, enterprise-grade AI IT Helpdesk and Support Agent built with **FastAPI**, **OpenAI Tool Calling**, **ChromaDB Vector Retrieval (RAG)**, **SQLModel / SQLite Incident Precedents**, and **Department-Aware Access Control (RBAC)**.

---

## Key Features

- **Autonomous Agent Loop:** Uses OpenAI function calling to autonomously diagnose issues, retrieve knowledge, query incident history, inspect service health, and escalate tickets.
- **Department-Aware Retrieval (RBAC):** Restricts internal documentation and historical incident visibility based on user department (`engineering`, `hr`, `finance`, `sales`, `it`, or `all`).
- **ChromaDB Vector Knowledge Base:** Persistent vector storage supporting Markdown, PDF, and plain-text SOPs with chunking and citation tracking.
- **Historical Incident Search:** Searches past resolved tickets to recommend proven fixes before opening new tickets.
- **Enterprise Service Registry:** Real-time operational status monitor for core infrastructure (VPN, GitLab, Jira, Okta SSO, Slack, AWS, GitHub, etc.).
- **Automatic Ticket Escalation:** Creates structured support tickets with unique IDs (`INC-XXXXXXXX`) when human technician intervention is needed.
- **Embedded Web Portal:** Built-in responsive web dashboard with live chat, service health indicators, citation previews, and ticket tracking.
- **Automated Evaluation Suite & Pytest:** Built-in benchmarking suite testing diagnostic accuracy across realistic corporate IT scenarios.

---

## Architecture Overview

```
                      +-----------------------------+
                      |   Employee / Client App     |
                      |   (Web UI / REST API)       |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |    FastAPI Support Server   |
                      +--------------+--------------+
                                     |
                      +--------------v--------------+
                      |   IT Support AI Agent Loop  |
                      +----+---------+---------+----+
                           |         |         |
          +----------------+         |         +-----------------+
          v                          v                           v
+-------------------+      +-------------------+       +-------------------+
|   ChromaDB RAG    |      |  SQL Incident DB  |       |  Service Monitor  |
| (Vector SOPs/Docs)|      | (Past Precedents) |       | (VPN/Okta/GitLab) |
+-------------------+      +-------------------+       +-------------------+
          |                          |                           |
          +--------------------------+---------------------------+
                                     |
                                     v
                      +-----------------------------+
                      | Ticket Escalation / Answer  |
                      +-----------------------------+
```

---

## Directory Structure

```
enterprise_it_support_rag_agent/
├── app/
│   ├── __init__.py
│   ├── agent.py          # OpenAI agent loop & function calling dispatcher
│   ├── config.py         # Settings & environment variable configuration
│   ├── db.py             # SQLModel database engine & session dependency
│   ├── main.py           # FastAPI application, REST endpoints & Web UI
│   ├── models.py         # SQLModel database schemas (Incidents, Tickets, Chat)
│   ├── rag.py            # ChromaDB vector store, chunking & document ingestion
│   ├── schemas.py        # Pydantic validation models
│   └── tools.py          # Enterprise support tools (RAG, Incidents, Status, Tickets)
├── data/
│   ├── docs/             # Corporate SOPs, guides, and metadata.json
│   ├── app.db            # SQLite database file (created on seed)
│   └── chroma/           # Persistent Chroma vector database
├── scripts/
│   ├── seed.py           # Seeds enterprise documentation & historical incidents
│   ├── ingest.py         # Ingests docs into ChromaDB vector store
│   └── evaluate.py       # Automated benchmark evaluation suite
├── tests/
│   ├── test_api.py       # FastAPI endpoint tests
│   ├── test_rag.py       # Vector retrieval & chunking unit tests
│   └── test_tools.py     # Tool execution & ticket creation tests
├── .dockerignore
├── .env.example          # Environment variables template
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Quickstart

### 1. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Open `.env` and set your `OPENAI_API_KEY`:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

> **Note:** The agent includes an offline fallback mode that executes tools and answers queries even if no OpenAI API key is supplied!

### 2. Install Dependencies

```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Seed Knowledge Base & Database

```bash
python scripts/seed.py
python scripts/ingest.py
```

### 4. Run the Server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Interactive Web Portal:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger REST Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Running with Docker

Run the entire application in a container with Docker Compose:

```bash
docker compose up --build
```

Access the UI at `http://localhost:8000`.

---

## API Examples

### Chat Request (cURL)

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "emp_1042",
    "department": "engineering",
    "message": "VPN says connected but internal GitLab is unreachable.",
    "conversation_id": "session_demo"
  }'
```

### List Service Health

```bash
curl http://127.0.0.1:8000/services
```

### Query Historical Incidents

```bash
curl "http://127.0.0.1:8000/incidents?department=engineering"
```

---

## Testing & Evaluation

### Run Automated Tests (Pytest)

```bash
pytest -v
```

### Run Benchmark Evaluation

```bash
python scripts/evaluate.py
```

---

## Production Deployment Considerations

1. **PostgreSQL & Redis:** Replace SQLite with AWS RDS / Cloud SQL PostgreSQL and use Redis for distributed conversation sessions.
2. **SSO & RBAC Integration:** Replace the demo department dropdown with Okta / Azure AD SAML or OIDC bearer token authentication.
3. **ITSM Integration:** Connect `create_ticket` to Jira Service Management or ServiceNow REST APIs.
4. **Audit Logging & Tracing:** Attach OpenTelemetry traces to monitor latency, token usage, and retrieval fidelity.
