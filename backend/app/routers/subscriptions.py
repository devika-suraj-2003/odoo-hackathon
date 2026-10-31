from fastapi import APIRouter

router = APIRouter(tags=["Subscriptions"])

# TODO: Implement subscription lifecycle endpoints
# GET    /subscriptions
# POST   /subscriptions
# GET    /subscriptions/{id}
# PUT    /subscriptions/{id}
# DELETE /subscriptions/{id}
# POST   /subscriptions/{id}/cancel
# POST   /subscriptions/{id}/pause
# POST   /subscriptions/{id}/resume


@router.get("/", summary="Subscriptions status / placeholder")
def get_subscriptions_status():
    """Placeholder endpoint for the Subscriptions router."""
    return {"status": "ok", "message": "Subscriptions router is registered"}
