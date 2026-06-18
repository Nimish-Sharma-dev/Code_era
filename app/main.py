from fastapi import FastAPI
from app.api.endpoints import wallet, market, chatbot

app = FastAPI(title="Code Era Financial Advisor Backend")

app.include_router(wallet.router, prefix="/api/wallet", tags=["wallet"])
app.include_router(market.router, prefix="/api/market", tags=["market"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["chatbot"])


@app.get("/health", summary="Health check")
def health_check() -> dict:
    return {"status": "ok"}
