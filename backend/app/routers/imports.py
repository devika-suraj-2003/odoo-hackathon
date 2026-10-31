from fastapi import APIRouter

router = APIRouter(tags=["Imports"])

# TODO: Implement CSV / bulk-import endpoints
# POST /imports/subscriptions   (CSV upload)
# GET  /imports/history
# GET  /imports/{id}/status


@router.get("/", summary="Imports status / placeholder")
def get_imports_status():
    """Placeholder endpoint for the Imports router."""
    return {"status": "ok", "message": "Imports router is registered"}
