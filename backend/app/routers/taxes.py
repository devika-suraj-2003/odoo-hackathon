from fastapi import APIRouter

router = APIRouter(tags=["Taxes"])

# TODO: Implement tax rule endpoints
# GET    /taxes
# POST   /taxes
# GET    /taxes/{id}
# PUT    /taxes/{id}
# DELETE /taxes/{id}


@router.get("/", summary="Taxes status / placeholder")
def get_taxes_status():
    """Placeholder endpoint for the Taxes router."""
    return {"status": "ok", "message": "Taxes router is registered"}
