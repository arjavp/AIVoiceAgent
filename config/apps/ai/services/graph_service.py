"""
LangGraph Workflow Orchestrator
===============================
Three separate LangGraph workflows, each with its own state machine:
  1. RAGWorkflow       — retrieve context from vector DB
  2. TicketWorkflow    — validate → create support ticket in DB
  3. EmailWorkflow     — validate → save email draft in DB

All DB-touching nodes are synchronous (Django ORM).
agent.py calls them via `asyncio.to_thread(workflow.run, ...)`.
"""

import os
import time
import traceback
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from .rag_service import get_rag_service


# ─────────────────────────────────────────────────
#  1.  RAG Workflow
# ─────────────────────────────────────────────────

class RAGState(TypedDict):
    query: str
    context: str


class RAGWorkflow:
    """START → retrieve → END"""

    def __init__(self):
        self.rag = get_rag_service()
        self.graph = self._build()

    def _build(self):
        wf = StateGraph(RAGState)

        def retrieve(state: RAGState):
            ctx = self.rag.retrieve(state["query"])
            has_ctx = ctx and ctx != "No relevant documents found."
            print(f"🔍 RAG Retrieved: {len(ctx)} chars, relevant={has_ctx}")
            return {"context": ctx}

        wf.add_node("retrieve", retrieve)
        wf.add_edge(START, "retrieve")
        wf.add_edge("retrieve", END)
        return wf.compile()

    def run(self, query: str) -> str:
        result = self.graph.invoke({"query": query, "context": ""})
        return result["context"]


# ─────────────────────────────────────────────────
#  2.  Ticket Workflow
# ─────────────────────────────────────────────────

VALID_PRIORITIES = {"low", "medium", "high", "urgent"}


class TicketState(TypedDict):
    title: str
    description: str
    priority: str
    ticket_id: str
    status: str
    result: str


class TicketWorkflow:
    """START → validate → create_ticket → END"""

    def __init__(self):
        self.graph = self._build()

    def _build(self):
        wf = StateGraph(TicketState)

        # ── Node 1: validate & clean inputs ──
        def validate(state: TicketState):
            title = (state.get("title") or "").strip() or "Untitled Ticket"
            description = (state.get("description") or "").strip() or title
            priority = (state.get("priority") or "medium").lower().strip()
            if priority not in VALID_PRIORITIES:
                priority = "medium"
            print(f"✅ Ticket validated: '{title}' | priority={priority}")
            return {"title": title, "description": description, "priority": priority}

        # ── Node 2: persist to DB ──
        def create_ticket(state: TicketState):
            from apps.ai.models import Ticket

            try:
                ticket = Ticket.objects.create(
                    title=state["title"],
                    description=state["description"],
                    priority=state["priority"],
                    status="open",
                )
                tid = str(ticket.id)[:8]
                print(f"🎫 Ticket saved to DB: {ticket.id}")
                return {
                    "ticket_id": str(ticket.id),
                    "status": "open",
                    "result": (
                        f"Ticket #{tid} created: '{state['title']}' "
                        f"({state['priority']}). Status: Open."
                    ),
                }
            except Exception as exc:
                print(f"❌ Ticket DB error: {exc}")
                traceback.print_exc()
                return {
                    "ticket_id": "",
                    "status": "error",
                    "result": f"I tried to create a ticket for '{state['title']}' but hit an error. Please try again.",
                }

        wf.add_node("validate", validate)
        wf.add_node("create_ticket", create_ticket)

        wf.add_edge(START, "validate")
        wf.add_edge("validate", "create_ticket")
        wf.add_edge("create_ticket", END)
        return wf.compile()

    def run(self, title: str, description: str, priority: str = "medium") -> str:
        result = self.graph.invoke({
            "title": title,
            "description": description,
            "priority": priority,
            "ticket_id": "",
            "status": "",
            "result": "",
        })
        return result["result"]


# ─────────────────────────────────────────────────
#  3.  Email Workflow
# ─────────────────────────────────────────────────

class EmailState(TypedDict):
    subject: str
    body: str
    recipient: str
    email_id: str
    result: str


class EmailWorkflow:
    """START → validate → save_draft → END"""

    def __init__(self):
        self.graph = self._build()

    def _build(self):
        wf = StateGraph(EmailState)

        # ── Node 1: validate & clean inputs ──
        def validate(state: EmailState):
            subject = (state.get("subject") or "").strip() or "No Subject"
            body = (state.get("body") or "").strip() or "(empty)"
            recipient = (state.get("recipient") or "").strip()
            print(f"✅ Email validated: subject='{subject}', to='{recipient}'")
            return {"subject": subject, "body": body, "recipient": recipient}

        # ── Node 2: persist to DB ──
        def save_draft(state: EmailState):
            from apps.ai.models import DraftEmail

            try:
                draft = DraftEmail.objects.create(
                    subject=state["subject"],
                    body=state["body"],
                    recipient=state["recipient"],
                )
                print(f"📧 Email draft saved to DB: {draft.id}")

                resp = f"Email draft saved: '{state['subject']}'."
                if state["recipient"]:
                    resp += f" To: {state['recipient']}."
                return {"email_id": str(draft.id), "result": resp}
            except Exception as exc:
                print(f"❌ Email DB error: {exc}")
                traceback.print_exc()
                return {
                    "email_id": "",
                    "result": f"I drafted the email but couldn't save it. Subject: '{state['subject']}'. Please try again.",
                }

        wf.add_node("validate", validate)
        wf.add_node("save_draft", save_draft)

        wf.add_edge(START, "validate")
        wf.add_edge("validate", "save_draft")
        wf.add_edge("save_draft", END)
        return wf.compile()

    def run(self, subject: str, body: str, recipient: str = "") -> str:
        result = self.graph.invoke({
            "subject": subject,
            "body": body,
            "recipient": recipient,
            "email_id": "",
            "result": "",
        })
        return result["result"]


# ─────────────────────────────────────────────────
#  Singleton Accessors  (one instance per process)
# ─────────────────────────────────────────────────

_rag_wf: RAGWorkflow | None = None
_ticket_wf: TicketWorkflow | None = None
_email_wf: EmailWorkflow | None = None


def get_rag_workflow() -> RAGWorkflow:
    global _rag_wf
    if _rag_wf is None:
        _rag_wf = RAGWorkflow()
        print("✅ LangGraph RAG Workflow initialized")
    return _rag_wf


def get_ticket_workflow() -> TicketWorkflow:
    global _ticket_wf
    if _ticket_wf is None:
        _ticket_wf = TicketWorkflow()
        print("✅ LangGraph Ticket Workflow initialized")
    return _ticket_wf


def get_email_workflow() -> EmailWorkflow:
    global _email_wf
    if _email_wf is None:
        _email_wf = EmailWorkflow()
        print("✅ LangGraph Email Workflow initialized")
    return _email_wf
