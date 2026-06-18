from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_db
from app.models.response_specs import MarketResponse

router = APIRouter()


@router.get("/predictions", response_model=MarketResponse)
async def fetch_market_subgraph(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    return {
        "user_id": current_user["id"],
        "asset_signals": [],
        "sentiment_snapshot": {},
    }
