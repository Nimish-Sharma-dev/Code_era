from typing import Any

from fastapi import Depends, HTTPException, Security, status


async def get_db() -> Any:
    """Return a database session or driver instance."""
    # Placeholder for Neo4j session injection
    return None


async def get_current_user(token: str = Depends(lambda: "dummy-token")) -> dict:
    """Validate auth token and return current user context."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return {"id": "user_123", "email": "user@example.com"}
