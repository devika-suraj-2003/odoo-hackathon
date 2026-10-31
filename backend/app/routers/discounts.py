from fastapi import APIRouter

router = APIRouter(tags=["Discounts"])

# TODO: Implement discount / coupon endpoints
# GET    /discounts
# POST   /discounts
# GET    /discounts/{id}
# PUT    /discounts/{id}
# DELETE /discounts/{id}
# POST   /discounts/validate   (check coupon code validity)


@router.get("/", summary="Discounts status / placeholder")
def get_discounts_status():
    """Placeholder endpoint for the Discounts router."""
    return {"status": "ok", "message": "Discounts router is registered"}
