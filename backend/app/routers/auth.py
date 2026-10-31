from fastapi import APIRouter

router = APIRouter(tags=["Auth"])

# TODO: Implement authentication endpoints
# POST /auth/register
# POST /auth/login
# POST /auth/refresh
# POST /auth/logout


@router.get("/", summary="Auth status / placeholder")
def get_auth_status():
    """Placeholder endpoint for the Auth router."""
    return {"status": "ok", "message": "Auth router is registered"}
