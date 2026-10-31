from fastapi import APIRouter

router = APIRouter(tags=["Settings"])

# TODO: Implement application settings endpoints
# GET /settings
# PUT /settings


@router.get("/", summary="Settings status / placeholder")
def get_settings_status():
    """Placeholder endpoint for the Settings router."""
    return {"status": "ok", "message": "Settings router is registered"}
