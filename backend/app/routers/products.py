from fastapi import APIRouter

router = APIRouter(tags=["Products"])

# TODO: Implement product endpoints
# GET    /products
# POST   /products
# GET    /products/{id}
# PUT    /products/{id}
# DELETE /products/{id}
# GET    /products/{id}/variants
# POST   /products/{id}/variants


@router.get("/", summary="Products status / placeholder")
def get_products_status():
    """Placeholder endpoint for the Products router."""
    return {"status": "ok", "message": "Products router is registered"}
