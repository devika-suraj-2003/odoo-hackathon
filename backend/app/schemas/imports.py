"""
imports.py — Pydantic schemas for CSV and bulk import operations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.user import UserResponse


class FailedRow(BaseModel):
    """
    Details of a CSV row that failed validation or creation.
    """
    row: int = Field(..., description="Line number of the row in the CSV file (1-based, header is line 1)")
    row_number: int = Field(..., description="Alias for row line number")
    email: Optional[str] = Field(None, description="Email associated with this row, if provided")
    reason: str = Field(..., description="Description of why this row failed validation or import")


class CustomerImportSummary(BaseModel):
    """
    Summary returned after processing customer CSV import.
    """
    total_rows: int = Field(..., description="Total data rows parsed from the CSV")
    successful_imports: int = Field(..., description="Count of successfully created customer accounts")
    success_count: int = Field(..., description="Alias for successful_imports")
    failed_imports: int = Field(..., description="Count of rows that failed validation or insertion")
    failed_count: int = Field(..., description="Alias for failed_imports")
    imported_customers: List[UserResponse] = Field(default_factory=list, description="List of created customer user objects")
    failed_rows: List[FailedRow] = Field(default_factory=list, description="List of failed rows with line numbers and reasons")

