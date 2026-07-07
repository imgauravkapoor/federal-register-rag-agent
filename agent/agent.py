"""
agent.py
---------
Agent ka core logic:
1. Tools define karo (LLM ko batao kya available hai)
2. User query LLM ko bhejo
3. LLM tool call maange toh execute karo
4. Result wapas LLM ko bhejo
5. LLM final answer do
"""

import json
import mysql.connector
import sys
import os
from openai import OpenAI  # Ollama OpenAI-compatible API expose karta hai

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import DB_CONFIG

# ─────────────────────────────────────────────
# Ollama client setup
# Base URL change karke Ollama ka local server point kiya hai
# ─────────────────────────────────────────────
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Ollama ko key ki zaroorat nahi, but parameter required hai isliye dummy value
)
MODEL = "qwen2.5:0.5b"


# ─────────────────────────────────────────────
# TOOLS (actual Python functions jo MySQL query karenge)
# ─────────────────────────────────────────────

def search_documents(keyword: str, limit: int = 5) -> str:
    """
    Title ya abstract mein keyword dhoodhta hai.
    LIKE query use ki hai - simple text search.
    """
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)  # dictionary=True se rows dict format mein milti hain

    query = """
        SELECT document_number, title, abstract, publication_date, agencies, doc_type
        FROM documents
        WHERE title LIKE %s OR abstract LIKE %s
        ORDER BY publication_date DESC
        LIMIT %s
    """
    like_keyword = f"%{keyword}%"
    cursor.execute(query, (like_keyword, like_keyword, limit))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if not rows:
        return f"'{keyword}' keyword se koi document nahi mila."

    # Result ko readable string mein convert karo LLM ke liye
    result = f"{len(rows)} documents mile '{keyword}' ke liye:\n\n"
    for row in rows:
        result += f"- [{row['publication_date']}] {row['title']}\n"
        result += f"  Agency: {row['agencies']}\n"
        if row['abstract']:
            result += f"  Summary: {row['abstract'][:200]}...\n"
        result += "\n"
    return result


def get_documents_by_date(start_date: str, end_date: str, limit: int = 5) -> str:
    """
    Date range ke basis pe documents fetch karta hai.
    Format: YYYY-MM-DD
    """
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT document_number, title, publication_date, agencies, doc_type
        FROM documents
        WHERE publication_date BETWEEN %s AND %s
        ORDER BY publication_date DESC
        LIMIT %s
    """
    cursor.execute(query, (start_date, end_date, limit))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if not rows:
        return f"{start_date} se {end_date} ke beech koi document nahi mila."

    result = f"{len(rows)} documents mile {start_date} se {end_date} ke beech:\n\n"
    for row in rows:
        result += f"- [{row['publication_date']}] {row['title']} ({row['doc_type']})\n"
        result += f"  Agency: {row['agencies']}\n\n"
    return result


def get_documents_by_agency(agency_name: str, limit: int = 5) -> str:
    """
    Kisi specific agency ke documents dhoondta hai.
    """
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT document_number, title, publication_date, agencies, doc_type
        FROM documents
        WHERE agencies LIKE %s
        ORDER BY publication_date DESC
        LIMIT %s
    """
    cursor.execute(query, (f"%{agency_name}%", limit))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if not rows:
        return f"'{agency_name}' agency ka koi document nahi mila."

    result = f"'{agency_name}' agency ke {len(rows)} documents:\n\n"
    for row in rows:
        result += f"- [{row['publication_date']}] {row['title']}\n\n"
    return result


# ─────────────────────────────────────────────
# SAFE FUNCTION DISPATCHER
# eval() dangerous hai - isliye dict-based dispatch use kiya
# sirf wahi functions chalenge jo yahan registered hain
# ─────────────────────────────────────────────
AVAILABLE_FUNCTIONS = {
    "search_documents": search_documents,
    "get_documents_by_date": get_documents_by_date,
    "get_documents_by_agency": get_documents_by_agency,
}


# ─────────────────────────────────────────────
# TOOL SCHEMAS (LLM ko batate hain kya available hai)
# Ye JSON schema LLM ko system prompt ke saath bheja jaata hai
# ─────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Federal Register documents mein keyword se search karo (title ya abstract mein)",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Search karne wala word ya phrase, e.g. 'safety', 'environment', 'drug'",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Kitne results chahiye (default 5)",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_documents_by_date",
            "description": "Date range ke basis pe Federal Register documents fetch karo",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD format mein",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD format mein",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Kitne results chahiye (default 5)",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_documents_by_agency",
            "description": "Kisi specific government agency ke documents fetch karo",
            "parameters": {
                "type": "object",
                "properties": {
                    "agency_name": {
                        "type": "string",
                        "description": "Agency ka naam, e.g. 'EPA', 'FDA', 'Coast Guard'",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Kitne results chahiye (default 5)",
                    },
                },
                "required": ["agency_name"],
            },
        },
    },
]


# ─────────────────────────────────────────────
# SYSTEM PROMPT
# LLM ko uski role batata hai
# ─────────────────────────────────────────────
from datetime import datetime, timedelta

def get_system_prompt() -> str:
    today = datetime.today().date()
    last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_month_end = today.replace(day=1) - timedelta(days=1)

    return f"""You are a helpful assistant for querying the US Federal Register database.
Today's date is {today}. Last month was {last_month_start} to {last_month_end}.

Tool usage rules:
- Use search_documents when user asks about a topic, keyword, or subject (e.g. 'safety', 'environment')
- Use get_documents_by_date ONLY when user gives explicit dates or says 'last month'/'this week' etc.
  For last month use: start_date="{last_month_start}", end_date="{last_month_end}"
- Use get_documents_by_agency when user asks about a specific agency

Always use tools before answering. Never make up document titles or dates.
Keep answers concise and factual."""


# ─────────────────────────────────────────────
# MAIN AGENT LOOP
# Ye wo core flow hai: query → LLM → tool call → execute → LLM → response
# ─────────────────────────────────────────────
def run_agent(user_query: str) -> str:
    """
    Ek user query leta hai, agent loop chalata hai, final answer return karta hai.
    Tool calls end user ko kabhi nahi dikhte (JD compulsory condition #1).
    """
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": user_query},
    ]

    print(f"\n[Agent] User query: {user_query}")

    # Agent loop - LLM tab tak chalti rahegi jab tak tool calls hain
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",  # LLM khud decide kare ki tool use karna hai ya nahi
        )

        message = response.choices[0].message

        # ── Case 1: LLM ne tool call manga ──
        if message.tool_calls:
            # Tool calls messages mein add karo (conversation history)
            messages.append(message)

            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                print(f"[Agent] Tool call: {function_name}({arguments})")  # server side log, user nahi dekh sakta

                # Safe dispatch - sirf registered functions chalenge
                func = AVAILABLE_FUNCTIONS.get(function_name)
                if func:
                    result = func(**arguments)
                else:
                    result = f"Error: '{function_name}' function registered nahi hai."

                # Tool result wapas messages mein daalo
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        # ── Case 2: LLM ne final answer diya (koi tool call nahi) ──
        else:
            final_answer = message.content
            print(f"[Agent] Final answer ready.\n")
            return final_answer


# ─────────────────────────────────────────────
# Quick test - directly run karne pe
# ─────────────────────────────────────────────
if __name__ == "__main__":
    test_queries = [
        "Show me documents related to safety from last month",
        "What documents were published by Coast Guard?",
    ]
    for q in test_queries:
        answer = run_agent(q)
        print(f"Query: {q}")
        print(f"Answer: {answer}")
        print("-" * 60)
