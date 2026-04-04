from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    # 'message' is for typed text. 'action' is for quick-action buttons.
    message: Optional[str] = None
    action: Optional[str] = None  

class ChatResponse(BaseModel):
    status: str
    reply: str