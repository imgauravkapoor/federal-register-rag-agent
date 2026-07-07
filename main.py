"""
main.py
--------
FastAPI server - ek hi kaam: user ki query lo, agent ko bhejo, response wapas do.
Demo ke liye simple rakha hai - no auth, no history management.
"""

import sys
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.append(os.path.dirname(__file__))
from agent.agent import run_agent

app = FastAPI(title="Federal Register RAG Agent")

# UI folder serve karne ke liye
app.mount("/static", StaticFiles(directory="ui"), name="static")


# ── Request/Response models ──
class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str


# ── Main chat endpoint ──
@app.post("/chat", response_model=QueryResponse)
def chat(request: QueryRequest):
    """
    User query leta hai, agent se answer mangta hai, return karta hai.
    Tool calls internally hoti hain - end user ko kabhi nahi dikhti.
    """
    answer = run_agent(request.query)
    return QueryResponse(answer=answer)


# ── UI serve karne ke liye ──
@app.get("/")
def serve_ui():
    return FileResponse("ui/index.html")


# ── Health check ──
@app.get("/health")
def health():
    return {"status": "ok"}
