from fastapi import APIRouter

router = APIRouter(tags=["Plans"])

# TODO: Implement subscription plan endpoints
# GET    /plans
# POST   /plans
# GET    /plans/{id}
# PUT    /plans/{id}
# DELETE /plans/{id}


@router.get("/", summary="Plans status / placeholder")
def get_plans_status():
    """Placeholder endpoint for the Plans router."""
    return {"status": "ok", "message": "Plans router is registered"}
