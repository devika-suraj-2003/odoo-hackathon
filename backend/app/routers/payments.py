from fastapi import APIRouter

router = APIRouter(tags=["Payments"])

# TODO: Implement payment endpoints
# GET  /payments
# GET  /payments/{id}
# POST /payments/process
# POST /payments/{id}/refund


@router.get("/", summary="Payments status / placeholder")
def get_payments_status():
    """Placeholder endpoint for the Payments router."""
    return {"status": "ok", "message": "Payments router is registered"}
