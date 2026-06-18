from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_db
from app.models.request_specs import ChatbotRequest
from app.models.response_specs import ChatbotResponse

router = APIRouter()


@router.post("/query", response_model=ChatbotResponse)
async def query_chatbot(payload: ChatbotRequest, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    return {
        "user_id": current_user["id"],
        "query": payload.query,
        "response": "This is a placeholder Saras AI response.",
        "context": {},
    }
