from fastapi import APIRouter

router = APIRouter(tags=["Reports"])

# TODO: Implement analytics / reporting endpoints
# GET /reports/revenue
# GET /reports/churn
# GET /reports/subscriptions/summary
# GET /reports/mrr          (Monthly Recurring Revenue)
# GET /reports/arr          (Annual Recurring Revenue)


@router.get("/", summary="Reports status / placeholder")
def get_reports_status():
    """Placeholder endpoint for the Reports router."""
    return {"status": "ok", "message": "Reports router is registered"}
