from pydantic import BaseModel
from typing import List, Optional


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class SessionPreview(BaseModel):
    session_id: str
    preview: str
    name: str
    updated_at: float


class HistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessage]


class UploadResponse(BaseModel):
    file_id: str
    status: str
    message: str
