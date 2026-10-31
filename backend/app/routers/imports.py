"""
imports.py — Bulk import endpoints for Brightloop Subscription Management System.
Supports CSV customer batch import.
"""

import csv
import io
from typing import List, Set

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.imports import CustomerImportSummary, FailedRow
from app.schemas.user import UserResponse, validate_email_address, validate_password_rules
from app.core.security import get_password_hash
from app.core.dependencies import require_staff_or_admin

router = APIRouter(tags=["Imports"])

REQUIRED_COLUMNS = ["name", "email", "password", "phone", "state"]


@router.get("", summary="Imports status / placeholder")
@router.get("/", summary="Imports status / placeholder", include_in_schema=False)
def get_imports_status():
    """Placeholder endpoint for the Imports router."""
    return {"status": "ok", "message": "Imports router is registered"}


@router.post(
    "/customers",
    response_model=CustomerImportSummary,
    status_code=status.HTTP_200_OK,
    summary="Import customers from a CSV file",
)
def import_customers(
    file: UploadFile = File(..., description="CSV file containing customer records"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin),
):
    """
    Bulk import customers from an uploaded CSV file:
    - Accessible to authenticated Admin and Staff users.
    - Requires CSV columns: 'name', 'email', 'password', 'phone', 'state'.
    - Validates each row independently.
    - Creates valid customers with role='customer' and hashed passwords.
    - Prevents duplicate emails (both in DB and within the same file).
    - Returns a summary of successful imports and failed rows with row numbers and reasons.
    """
    if file.filename and not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file (.csv)",
        )

    try:
        content_bytes = file.file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}",
        )

    if not content_bytes or not content_bytes.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty",
        )

    try:
        text = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content_bytes.decode("latin-1")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to decode file text as UTF-8 or Latin-1",
            )

    reader = csv.reader(io.StringIO(text))
    try:
        header_row = next(reader)
    except StopIteration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty",
        )

    # Normalize headers
    col_map = {}
    for idx, col in enumerate(header_row):
        norm = col.strip().lower()
        if norm:
            col_map[norm] = idx

    missing = [col for col in REQUIRED_COLUMNS if col not in col_map]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns in CSV header: {', '.join(missing)}",
        )

    name_idx = col_map["name"]
    email_idx = col_map["email"]
    pwd_idx = col_map["password"]
    phone_idx = col_map["phone"]
    state_idx = col_map["state"]

    successful_users: List[User] = []
    failed_rows: List[FailedRow] = []
    seen_emails_in_batch: Set[str] = set()
    total_data_rows = 0

    # Line numbers start at 2 (line 1 is the header)
    for line_num, row in enumerate(reader, start=2):
        # Ignore completely empty rows (e.g. blank lines at end of file)
        if not any(cell.strip() for cell in row):
            continue

        total_data_rows += 1

        name = row[name_idx].strip() if len(row) > name_idx else ""
        raw_email = row[email_idx].strip() if len(row) > email_idx else ""
        password = row[pwd_idx].strip() if len(row) > pwd_idx else ""
        phone = row[phone_idx].strip() if len(row) > phone_idx else ""
        state = row[state_idx].strip() if len(row) > state_idx else ""

        # Validate name
        if not name:
            failed_rows.append(
                FailedRow(
                    row=line_num,
                    row_number=line_num,
                    email=raw_email or None,
                    reason="Name is required and cannot be empty",
                )
            )
            continue
        if len(name) > 150:
            failed_rows.append(
                FailedRow(
                    row=line_num,
                    row_number=line_num,
                    email=raw_email or None,
                    reason="Name must not exceed 150 characters",
                )
            )
            continue

        # Validate email
        if not raw_email:
            failed_rows.append(
                FailedRow(
                    row=line_num,
                    row_number=line_num,
                    email=None,
                    reason="Email is required and cannot be empty",
                )
            )
            continue

        try:
            norm_email = validate_email_address(raw_email)
        except Exception as ve:
            failed_rows.append(
                FailedRow(
                    row=line_num,
                    row_number=line_num,
                    email=raw_email,
                    reason=f"Invalid email address: {str(ve)}",
                )
            )
            continue

        # Check duplicate email in current batch
        if norm_email in seen_emails_in_batch:
            failed_rows.append(
                FailedRow(
                    row=line_num,
                    row_number=line_num,
                    email=norm_email,
                    reason=f"Duplicate email '{norm_email}' in CSV batch",
                )
            )
            continue

        # Check duplicate email in database
        existing_user = db.query(User.id).filter(User.email == norm_email).first()
        if existing_user is not None:
            failed_rows.append(
                FailedRow(
                    row=line_num,
                    row_number=line_num,
                    email=norm_email,
                    reason=f"User with email '{norm_email}' already exists",
                )
            )
            continue

        # Validate password
        if not password:
            failed_rows.append(
                FailedRow(
                    row=line_num,
                    row_number=line_num,
                    email=norm_email,
                    reason="Password is required and cannot be empty",
                )
            )
            continue

        try:
            validate_password_rules(password)
        except Exception as ve:
            failed_rows.append(
                FailedRow(
                    row=line_num,
                    row_number=line_num,
                    email=norm_email,
                    reason=f"Password does not meet complexity requirements: {str(ve)}",
                )
            )
            continue

        # Validate phone
        phone_val = phone if phone else None
        if phone_val and len(phone_val) > 20:
            failed_rows.append(
                FailedRow(
                    row=line_num,
                    row_number=line_num,
                    email=norm_email,
                    reason="Phone must not exceed 20 characters",
                )
            )
            continue

        # Validate state
        state_val = state if state else None
        if state_val and len(state_val) > 100:
            failed_rows.append(
                FailedRow(
                    row=line_num,
                    row_number=line_num,
                    email=norm_email,
                    reason="State must not exceed 100 characters",
                )
            )
            continue

        # Create valid customer
        new_customer = User(
            name=name,
            email=norm_email,
            password_hash=get_password_hash(password),
            role="customer",
            phone=phone_val,
            state=state_val,
        )
        db.add(new_customer)
        successful_users.append(new_customer)
        seen_emails_in_batch.add(norm_email)

    if successful_users:
        try:
            db.commit()
            for user in successful_users:
                db.refresh(user)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error committing imported customers: {str(e)}",
            )

    return CustomerImportSummary(
        total_rows=total_data_rows,
        successful_imports=len(successful_users),
        success_count=len(successful_users),
        failed_imports=len(failed_rows),
        failed_count=len(failed_rows),
        imported_customers=[UserResponse.model_validate(u) for u in successful_users],
        failed_rows=failed_rows,
    )
