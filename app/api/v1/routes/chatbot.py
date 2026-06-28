"""RAG chatbot API route."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.connection import get_db
from app.db.postgres.redis_client import get_redis
from app.graph.graph_service import GraphService
from app.middleware.auth_middleware import CurrentUser, rate_limit_check
from app.rag.chatbot import FinancialChatbot
from app.schemas.market import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chatbot"], dependencies=[Depends(rate_limit_check)])


@router.post("", response_model=ChatResponse, summary="Chat with the AI financial advisor")
async def chat(
    request: ChatRequest,
    current_user: CurrentUser = None,
):
    """
    Send a message to the RAG-powered financial advisor chatbot.

    The chatbot:
    - Retrieves your financial context from the knowledge graph
    - Performs semantic search over your financial data
    - Generates a personalised response using an open-source LLM
    - Maintains conversation history per session_id

    Start a new conversation by omitting session_id.
    """
    redis = get_redis()
    graph = GraphService()
    chatbot = FinancialChatbot(redis_client=redis, graph_service=graph)

    result = await chatbot.chat(
        user_id=str(current_user.id),
        message=request.message,
        session_id=request.conversation_id,
        include_portfolio_context=request.include_portfolio_context,
    )
    return ChatResponse(**result)


@router.delete("/session/{session_id}", status_code=204, summary="Clear conversation history")
async def clear_session(
    session_id: str,
    current_user: CurrentUser = None,
):
    """Delete the conversation memory for a session."""
    from app.rag.chatbot import ConversationMemory
    redis = get_redis()
    memory = ConversationMemory(redis_client=redis)
    await memory.clear(session_id)
