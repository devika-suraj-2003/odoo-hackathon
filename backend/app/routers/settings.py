"""
settings.py — Application Settings and Time Machine endpoints for Brightloop.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session


from app.database import get_db
from app.models.user import User
from app.core.dependencies import require_admin
from app.schemas.settings import (
    TimeTravelRequest,
    TimeTravelResponse,
    TimeTravelResetResponse,
)
from app.services import clock
from app.services.billing import run_billing

router = APIRouter(tags=["Settings"])


@router.get(
    "",
    summary="Get application settings and time machine status",
)
def get_settings_status(db: Session = Depends(get_db)):
    """
    Retrieve application settings and current clock status:
    - Returns real date and simulated date if configured.
    - Preserves existing placeholder compatibility.
    """
    simulated = clock.get_simulated_today(db=db)
    return {
        "status": "ok",
        "message": "Settings router is registered",
        "real_today": date.today().isoformat(),
        "simulated_today": simulated.isoformat() if simulated else None,
        "is_simulated": simulated is not None,
    }


@router.post(
    "/time-travel",
    response_model=TimeTravelResponse,
    summary="Advance simulated time",
)
def time_travel(
    request: TimeTravelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Advance simulated system time by the requested number of days:
    - Restricted to administrators (role='admin').
    - Idempotently updates the existing settings table.
    - Starting point is current today() (either existing simulated date or real date).
    """
    try:
        new_simulated_date = clock.advance_time(
            days=request.days,
            db=db,
        )

        invoices_generated = run_billing(
            db,
            new_simulated_date,
        )

        return TimeTravelResponse(
            status="ok",
            message=(
                f"Time advanced by {request.days} day(s). "
                f"{invoices_generated} recurring invoice(s) generated."
            ),
            simulated_today=new_simulated_date,
            real_today=date.today(),
            days_advanced=request.days,
            invoices_generated=invoices_generated,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while advancing time: {str(e)}",
        )


@router.post(
    "/time-travel/reset",
    response_model=TimeTravelResetResponse,
    summary="Reset time machine to real current date",
)
def reset_time_travel(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Reset simulated time back to real current system date:
    - Restricted to administrators (role='admin').
    - Clears simulated_today in the settings table.
    """
    try:
        clock.reset_simulated_today(db=db)
        return TimeTravelResetResponse(
            status="ok",
            message="Time travel reset successfully. Current date reverted to real date.",
            simulated_today=None,
            real_today=date.today(),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while resetting time: {str(e)}",
        )
