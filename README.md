# 🏛️ Federal Register RAG Agent

A User-Facing Chat-Style RAG Agentic System built on top of the **US Federal Register API** — a real government data source that updates daily. The system allows users to query government documents through a conversational chat interface powered by a local LLM with tool-calling capabilities.

---

## 📌 System Architecture

```
User Query
    ↓
Chat UI (HTML/JS)
    ↓
FastAPI Backend (/chat endpoint)
    ↓
Agent Core (LLM + Tool Calling Loop)
    ↓
MySQL Database ← Daily Data Pipeline ← Federal Register API
```

**4 Main Components:**

| Component | File | Responsibility |
|---|---|---|
| Data Pipeline - Downloader | `pipeline/downloader.py` | Fetches raw JSON from Federal Register API, saves to disk |
| Data Pipeline - Processor | `pipeline/processor.py` | Cleans raw data, inserts into MySQL using raw SQL |
| Agent Core | `agent/agent.py` | LLM + tool-calling loop, MySQL query functions |
| API + UI | `main.py` + `ui/index.html` | FastAPI endpoint, simple chat interface |

---

## ⚙️ Tech Stack

- **Language:** Python 3.x
- **LLM:** `qwen2.5:0.5b` via [Ollama](https://ollama.com) (local, no API key needed)
- **LLM Client:** OpenAI Python SDK (Ollama exposes OpenAI-compatible API)
- **Database:** MySQL (raw SQL, no ORM)
- **Backend:** FastAPI
- **Frontend:** Vanilla HTML + CSS + JavaScript
- **Data Source:** [Federal Register Public API](https://www.federalregister.gov/developers/documentation/api/v1) (free, no auth)

---

## 🗂️ Project Structure

```
RAG/
├── config.py                  # MySQL credentials (not committed to git)
├── main.py                    # FastAPI server + UI serving
├── pipeline/
│   ├── downloader.py          # API fetch + raw data save
│   ├── processor.py           # Data cleaning + MySQL insert
│   └── schema.sql             # Database + table definition
├── agent/
│   └── agent.py               # Agent core: tools, schemas, LLM loop
├── ui/
│   └── index.html             # Chat interface
└── data/
    ├── raw/                   # Raw JSON files (timestamped, 1 week kept)
    └── processed/             # Cleaned data copies
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.8+
- MySQL running locally
- [Ollama](https://ollama.com/download) installed

### Step 1: Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/federal-register-rag-agent.git
cd federal-register-rag-agent
```

### Step 2: Install dependencies
```bash
pip install requests mysql-connector-python fastapi uvicorn openai
```

### Step 3: Pull the LLM model
```bash
ollama pull qwen2.5:0.5b
```

### Step 4: Setup MySQL database
```bash
mysql -u root -p < pipeline/schema.sql
```

### Step 5: Configure credentials
Create `config.py` in root (already in `.gitignore`):
```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_MYSQL_PASSWORD",
    "database": "rag_agent_db",
}
```

---

## ▶️ Running the System

### Step 1: Run the data pipeline (fetch + store documents)
```bash
python pipeline/downloader.py
python pipeline/processor.py
```
This fetches the last 60 days of Federal Register documents and stores them in MySQL.

### Step 2: Start the FastAPI server
```bash
uvicorn main:app --reload
```

### Step 3: Open the chat UI
Go to **http://localhost:8000** in your browser.

---

## 💬 Example Queries

| User Query | Tool Called | What Happens |
|---|---|---|
| "Show me documents about safety" | `search_documents(keyword="safety")` | MySQL LIKE search on title + abstract |
| "What did Coast Guard publish?" | `get_documents_by_agency(agency_name="Coast Guard")` | Filter by agency column |
| "Documents from July 2026" | `get_documents_by_date(start_date=..., end_date=...)` | Filter by publication_date range |

---

## 🧠 Key Design Decisions

### 1. Downloader and Processor are Separate
Following **separation of concerns** — downloader only fetches and saves raw data, processor only cleans and inserts. This makes debugging easier: if DB has wrong data, check processor; if no data at all, check downloader.

### 2. Raw Data Saved to Disk with Timestamps
Every pipeline run saves a timestamped raw JSON file. This maintains **at least 1 week of pipeline records** — if today's run fails, yesterday's data is still available for reprocessing.

### 3. Dictionary-Based Function Dispatcher (not eval())
```python
AVAILABLE_FUNCTIONS = {
    "search_documents": search_documents,
    ...
}
func = AVAILABLE_FUNCTIONS.get(function_name)
result = func(**arguments)
```
`eval()` would allow LLM to execute arbitrary Python code — a critical security risk. Dictionary dispatch ensures **only predefined functions can be called**.

### 4. ON DUPLICATE KEY UPDATE — Idempotent Pipeline
Daily pipeline runs fetch overlapping date ranges. Using `ON DUPLICATE KEY UPDATE` ensures the pipeline can run safely multiple times without creating duplicate rows — making it **idempotent**.

### 5. Dynamic System Prompt with Date Injection
`qwen2.5:0.5b` is a small model with weak date arithmetic. Instead of asking the model to calculate "last month", Python pre-calculates the date range and injects it into the system prompt — reducing model load and improving accuracy. This is called **prompt grounding**.

### 6. Tool Calls Hidden from End User
The agent loop only returns `message.content` (final LLM answer) to the API response. Tool call JSON and intermediate results stay inside the `messages` list — **never exposed to the frontend**. This satisfies the core UX requirement of a clean chat interface.

---

## 🔄 How the Agent Loop Works

```
User Query
    ↓
LLM receives: system prompt + user query + tool schemas
    ↓
LLM decides: use tool? → YES → returns tool_call JSON
    ↓
Python parses tool_call → executes MySQL function → gets result
    ↓
Result added to messages → sent back to LLM
    ↓
LLM decides: use another tool? → NO → generates final answer
    ↓
Final answer returned to user (tool calls never visible)
```

---

## 📈 What's Out of Scope (Demo Version)

| Feature | Reason Excluded |
|---|---|
| Vector Database | Out of scope per task requirements |
| Async implementation | Allowed to use sync for demo; production would use `aiohttp` + `aiomysql` |
| Chat history management | Requires user/session ID system — beyond demo scope |
| Authentication | Demo only requires basic chat functionality |
| Cron job scheduler | Manual pipeline run sufficient for demo |

---

## 🔮 Production Improvements (Next Steps)

- Replace sync code with `async/await` using `aiohttp` + `aiomysql`
- Add ChromaDB/FAISS for semantic similarity search (true RAG)
- Set up cron job for automatic daily pipeline runs
- Add chat history with session management
- Containerize with Docker
- Add LLM observability (latency tracking, token cost logging)

---

## 📄 Data Source

**US Federal Register API** — https://www.federalregister.gov/developers/documentation/api/v1

- Free to use, no authentication required
- Updates daily with new government documents
- Contains Executive Orders, Rules, Notices, Proposed Rules from all federal agencies
- Only 2025-2026 data used in this demo (past 60 days)
