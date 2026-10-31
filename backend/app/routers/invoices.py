from fastapi import APIRouter

router = APIRouter(tags=["Invoices"])

# TODO: Implement invoice endpoints
# GET  /invoices
# GET  /invoices/{id}
# POST /invoices/{id}/send
# POST /invoices/{id}/void


@router.get("/", summary="Invoices status / placeholder")
def get_invoices_status():
    """Placeholder endpoint for the Invoices router."""
    return {"status": "ok", "message": "Invoices router is registered"}
