from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_db
from app.models.request_specs import WalletUpdateRequest
from app.models.response_specs import WalletResponse

router = APIRouter()


@router.get("/profile", response_model=WalletResponse)
async def get_wallet_profile(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    return {
        "user_id": current_user["id"],
        "loans": [],
        "wallets": [],
        "expenses": [],
    }


@router.post("/update", response_model=WalletResponse)
async def update_wallet(payload: WalletUpdateRequest, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    return {
        "user_id": current_user["id"],
        "message": "Wallet update received",
        "details": payload.dict(),
    }
