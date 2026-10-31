from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.report import monthly_revenue, report_summary

router = APIRouter(tags=["Reports"])


@router.get("")
@router.get("/", include_in_schema=False)
def get_report_summary(db: Session = Depends(get_db)):
    return report_summary(db)


@router.get("/summary")
def get_report_summary_endpoint(db: Session = Depends(get_db)):
    return report_summary(db)


@router.get("/mrr")
def get_mrr(db: Session = Depends(get_db)):
    return {"mrr": report_summary(db)["mrr"]}


@router.get("/arr")
def get_arr(db: Session = Depends(get_db)):
    return {"arr": report_summary(db)["arr"]}


@router.get("/revenue")
def get_revenue(db: Session = Depends(get_db)):
    return {"revenue": report_summary(db)["revenue"]}


@router.get("/outstanding")
def get_outstanding(db: Session = Depends(get_db)):
    summary = report_summary(db)
    return {"outstanding": summary["outstanding"]}


@router.get("/overdue")
def get_overdue(db: Session = Depends(get_db)):
    summary = report_summary(db)
    return {
        "overdue_amount": summary["overdue_amount"],
        "overdue_count": summary["overdue_count"],
    }


@router.get("/monthly-revenue")
def get_monthly_revenue(
    months: int = Query(default=12, ge=1, le=36),
    db: Session = Depends(get_db),
):
    return monthly_revenue(db, months=months)


@router.get("/pdf")
def download_report_pdf(db: Session = Depends(get_db)):
    from app.services.pdf import generate_report_pdf

    pdf = generate_report_pdf(db)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="brightloop-report.pdf"'},
    )
