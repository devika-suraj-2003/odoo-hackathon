
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

from app.database import get_db
from app.models.template import QuotationTemplate, TemplateLine

router = APIRouter(tags=["Templates"])


# ---------------- REQUEST SCHEMAS ----------------

class TemplateLineCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(default=1, gt=0)
    unit_price: int = Field(default=0, ge=0)


class TemplateCreate(BaseModel):
    name: str
    validity_days: int = Field(default=30, gt=0)
    plan_id: int
    lines: List[TemplateLineCreate]


# ---------------- RESPONSE SCHEMAS ----------------

class TemplateLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(validation_alias="qty")
    unit_price: int


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    validity_days: int
    plan_id: int
    lines: List[TemplateLineResponse]


# ---------------- GET ALL TEMPLATES ----------------

@router.get("/", response_model=List[TemplateResponse])
def get_templates(db: Session = Depends(get_db)):
    return db.query(QuotationTemplate).all()


# ---------------- CREATE TEMPLATE ----------------

@router.post("/", response_model=TemplateResponse)
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db)
):
    template = QuotationTemplate(
        name=data.name,
        validity_days=data.validity_days,
        plan_id=data.plan_id
    )

    template.lines = [
        TemplateLine(
            product_id=line.product_id,
            variant_id=line.variant_id,
            qty=line.quantity,
            unit_price=line.unit_price
        )
        for line in data.lines
    ]

    db.add(template)
    db.commit()
    db.refresh(template)

    return template


# ---------------- GET TEMPLATE BY ID ----------------

@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    template = db.query(QuotationTemplate).filter(
        QuotationTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=404,
            detail="Template not found"
        )

    return template


# ---------------- UPDATE TEMPLATE ----------------

@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    data: TemplateCreate,
    db: Session = Depends(get_db)
):
    template = db.query(QuotationTemplate).filter(
        QuotationTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=404,
            detail="Template not found"
        )

    template.name = data.name
    template.validity_days = data.validity_days
    template.plan_id = data.plan_id

    template.lines.clear()

    template.lines.extend([
        TemplateLine(
            product_id=line.product_id,
            variant_id=line.variant_id,
            qty=line.quantity,
            unit_price=line.unit_price
        )
        for line in data.lines
    ])

    db.commit()
    db.refresh(template)

    return template


# ---------------- DELETE TEMPLATE ----------------

@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    template = db.query(QuotationTemplate).filter(
        QuotationTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=404,
            detail="Template not found"
        )

    db.delete(template)
    db.commit()

    return {
        "message": "Template deleted successfully"
    }
