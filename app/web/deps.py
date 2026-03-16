# app/web/deps.py

from app.hyperstate.response import ActorContext


async def get_current_actor() -> ActorContext:
    """Mock actor dependency."""
    return ActorContext(id="user-123", roles=["customer", "manager"])
