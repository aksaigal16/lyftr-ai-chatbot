from sqlalchemy import func
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import init_db, get_db
from models import Message
from llm import generate_reply, AllProvidersUnavailable


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("SQLite database initialized successfully!")
    yield


app = FastAPI(
    title="Lyftr AI Chatbot",
    description="LLM Chatbot with Key Failover and Response Caching",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=10000)


def current_time():
    return datetime.now(timezone.utc).isoformat()


def parse_failure_header(value):
    failures = {}

    if not value:
        return failures

    for item in value.split(","):
        if "=" not in item:
            continue

        key, status = item.strip().split("=", 1)

        try:
            failures[key.strip()] = int(status.strip())
        except ValueError:
            continue

    return failures


@app.get("/")
def home():
    return {"message": "Welcome to Lyftr AI Chatbot"}


@app.get("/health")
def health():
    from llm import API_KEYS

    return {
        "status": "ok",
        "keys_configured": len(API_KEYS),
        "cache_enabled": True
    }


@app.post("/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    simulate_failure: str | None = Header(
        default=None,
        alias="X-Simulate-Failure"
    )
):
    session_id = request.session_id
    user_text = request.message.strip()

    if not user_text:
        raise HTTPException(
            status_code=422,
            detail="Message cannot be empty"
        )

    # Save the new user message
    user_message = Message(
        session_id=session_id,
        role="user",
        content=user_text,
        created_at=current_time()
    )

    db.add(user_message)
    db.commit()

    # Retrieve the complete conversation
    history = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id.asc())
        .all()
    )

    llm_messages = [
        {
            "role": item.role,
            "content": item.content
        }
        for item in history
    ]

    # Parse optional failure simulation header
    simulated_failures = parse_failure_header(
        simulate_failure
    )

    try:
        result = generate_reply(
            llm_messages,
            simulated_failures=simulated_failures
        )

    except AllProvidersUnavailable:
        raise HTTPException(
            status_code=503,
            detail="all providers unavailable"
        )

    except Exception as error:
        print(f"Chat generation failed: {error}")

        raise HTTPException(
            status_code=502,
            detail="AI provider request failed"
        )

    # Save the assistant response and metadata
    metadata = {
        "model": result["model"],
        "resolution_source": result["resolution_source"],
        "latency_ms": result["latency_ms"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "key_id": result["key_id"],
        "fallback_attempts": result["fallback_attempts"]
    }

    assistant_message = Message(
        session_id=session_id,
        role="assistant",
        content=result["reply"],
        metadata_json=json.dumps(metadata),
        created_at=current_time()
    )

    db.add(assistant_message)
    db.commit()

    return {
        "session_id": session_id,
        "reply": result["reply"],
        "metadata": metadata
    }


@app.get("/sessions/{session_id}/messages")
def get_messages(
    session_id: str,
    db: Session = Depends(get_db)
):
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id.asc())
        .all()
    )

    if not messages:
        raise HTTPException(
            status_code=404,
            detail="session not found"
        )

    result = []

    for message in messages:
        item = {
            "role": message.role,
            "content": message.content
        }

        if message.role == "assistant" and message.metadata_json:
            item["metadata"] = json.loads(
                message.metadata_json
            )

        result.append(item)

    return {
        "session_id": session_id,
        "messages": result
    }


@app.get("/sessions")
def get_sessions(db: Session = Depends(get_db)):

    # Find all unique sessions and their latest message ID
    session_rows = (
        db.query(
            Message.session_id,
            func.max(Message.id).label("last_message_id")
        )
        .group_by(Message.session_id)
        .order_by(func.max(Message.id).desc())
        .all()
    )

    sessions = []

    for row in session_rows:

        # Get the first user message for the chat title
        first_message = (
            db.query(Message)
            .filter(
                Message.session_id == row.session_id,
                Message.role == "user"
            )
            .order_by(Message.id.asc())
            .first()
        )

        # Get the latest message for the timestamp
        last_message = (
            db.query(Message)
            .filter(Message.id == row.last_message_id)
            .first()
        )

        sessions.append({
            "session_id": row.session_id,
            "title": (
                first_message.content[:40]
                if first_message else "New Chat"
            ),
            "updated_at": last_message.created_at
        })

    return {"sessions": sessions}

@app.get("/sessions")
def get_sessions(db: Session = Depends(get_db)):

    sessions = (
        db.query(
            Message.session_id,
            func.max(Message.id).label("last_message_id")
        )
        .group_by(Message.session_id)
        .order_by(func.max(Message.id).desc())
        .all()
    )

    result = []

    for session in sessions:

        first_message = (
            db.query(Message)
            .filter(
                Message.session_id == session.session_id,
                Message.role == "user"
            )
            .order_by(Message.id.asc())
            .first()
        )

        last_message = (
            db.query(Message)
            .filter(Message.id == session.last_message_id)
            .first()
        )

        result.append({
            "session_id": session.session_id,
            "title": (
                first_message.content[:40]
                if first_message else "New Chat"
            ),
            "updated_at": last_message.created_at
        })

    return {"sessions": result}