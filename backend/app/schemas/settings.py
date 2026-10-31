"""
settings.py — Pydantic schemas for Application Settings and Time Machine API.
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class TimeTravelRequest(BaseModel):
    """
    Request schema to advance simulated time.
    """
    days: int = Field(
        ...,
        gt=0,
        description="Number of days to advance simulated time (must be greater than 0)",
        examples=[30],
    )


class TimeTravelResponse(BaseModel):
    """
    Response schema returning the updated time machine state.
    """
    status: str = Field(default="ok")
    message: str
    simulated_today: date
    real_today: date
    days_advanced: int
    invoices_generated: int = 0


class TimeTravelResetResponse(BaseModel):
    """
    Response schema after resetting time travel to real date.
    """
    status: str = Field(default="ok")
    message: str
    simulated_today: Optional[date] = None
    real_today: date

