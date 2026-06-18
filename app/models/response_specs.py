from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class LoanModel(BaseModel):
    id: str
    balance: float
    interest_rate: float


class WalletModel(BaseModel):
    id: str
    asset_type: str
    balance: float


class WalletResponse(BaseModel):
    user_id: str
    loans: List[LoanModel]
    wallets: List[WalletModel]
    expenses: List[Dict[str, Any]]
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class MarketResponse(BaseModel):
    user_id: str
    asset_signals: List[Dict[str, Any]]
    sentiment_snapshot: Dict[str, Any]


class ChatbotResponse(BaseModel):
    user_id: str
    query: str
    response: str
    context: Dict[str, Any]
