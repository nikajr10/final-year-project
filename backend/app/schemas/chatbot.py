from pydantic import BaseModel
from typing import Optional


class ChatMessage(BaseModel):
    """A single message in the conversation history."""
    role: str   # "user" or "ai"
    text: str


class ChatRequest(BaseModel):
    """
    Request body for the /api/chat/chat endpoint.

    - 'message': free text typed by the user
    - 'action':  quick-action button identifier (low_stock, today_sales, etc.)
    - 'history': previous messages for conversation context (optional)

    At least one of 'message' or 'action' must be provided.
    """
    message: Optional[str] = None
    action: Optional[str] = None
    history: Optional[list[ChatMessage]] = None


class ChatResponse(BaseModel):
    """Response body returned by the chatbot."""
    status: str
    reply: str