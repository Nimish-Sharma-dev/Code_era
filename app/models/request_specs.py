from pydantic import BaseModel
from typing import List, Optional


class WalletUpdateRequest(BaseModel):
    income: Optional[float]
    expenses: Optional[float]
    loans: Optional[List[str]]


class ChatbotRequest(BaseModel):
    query: str
    context: Optional[dict] = None
