from fastapi import APIRouter

router = APIRouter(tags=["Templates"])

# TODO: Implement invoice/email template endpoints
# GET    /templates
# POST   /templates
# GET    /templates/{id}
# PUT    /templates/{id}
# DELETE /templates/{id}


@router.get("/", summary="Templates status / placeholder")
def get_templates_status():
    """Placeholder endpoint for the Templates router."""
    return {"status": "ok", "message": "Templates router is registered"}
