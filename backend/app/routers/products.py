"""
products.py — Product and ProductVariant management endpoints for Brightloop Subscription Management System.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.user import User
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.core.dependencies import get_current_user, require_admin

router = APIRouter(tags=["Products"])


@router.get(
    "",
    response_model=List[ProductResponse],
    summary="List all products with nested variants",
)
def list_products(
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of products to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve all products with nested variants:
    - Accessible to all authenticated users (admin, staff, customer).
    - Supports pagination via skip and limit query parameters.
    """
    stmt = (
        select(Product)
        .options(selectinload(Product.variants))
        .offset(skip)
        .limit(limit)
    )
    products = db.scalars(stmt).all()
    return products


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product details with nested variants",
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a single product by ID with its nested variants:
    - Accessible to all authenticated users (admin, staff, customer).
    - Returns HTTP 404 if product does not exist.
    """
    stmt = (
        select(Product)
        .options(selectinload(Product.variants))
        .where(Product.id == product_id)
    )
    product = db.scalars(stmt).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    return product


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product with variants",
)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create product and variants in a single database transaction:
    - Only administrators can create products.
    - Automatically links product_id to each variant.
    - Returns created product with nested variants.
    """
    try:
        product = Product(
            name=product_in.name,
            type=product_in.type,
            sales_price=product_in.sales_price,
            cost_price=product_in.cost_price,
            notes=product_in.notes,
        )
        for v in product_in.variants:
            variant = ProductVariant(
                attribute=v.attribute,
                value=v.value,
                extra_price=v.extra_price,
            )
            product.variants.append(variant)

        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create product: {str(e)}",
        )


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product and synchronize nested variants",
)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update product details and synchronize nested variants:
    - Only administrators can update products.
    - Updates scalar attributes if provided.
    - If 'variants' list is provided:
        * Updates existing variants matching submitted IDs.
        * Creates new variants if ID is not provided.
        * Removes variants omitted from the submitted list (replacement semantics).
        * Rejects with HTTP 400 if a variant ID belongs to another product.
        * Rejects with HTTP 404 if a variant ID does not exist.
    - All modifications are committed within a single database transaction.
    """
    stmt = (
        select(Product)
        .options(selectinload(Product.variants))
        .where(Product.id == product_id)
    )
    product = db.scalars(stmt).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    try:
        # Update scalar fields
        update_data = product_in.model_dump(exclude_unset=True)
        for field in ["name", "type", "sales_price", "cost_price", "notes"]:
            if field in update_data:
                setattr(product, field, update_data[field])

        # Synchronize variants if provided
        if product_in.variants is not None:
            existing_variants_by_id = {v.id: v for v in product.variants}
            submitted_ids = set()

            for v_in in product_in.variants:
                if v_in.id is not None:
                    # Check if this variant belongs to the current product
                    if v_in.id in existing_variants_by_id:
                        # Update existing variant
                        v_obj = existing_variants_by_id[v_in.id]
                        v_obj.attribute = v_in.attribute
                        v_obj.value = v_in.value
                        v_obj.extra_price = v_in.extra_price
                        submitted_ids.add(v_in.id)
                    else:
                        # Variant ID does not belong to this product
                        foreign_variant = db.get(ProductVariant, v_in.id)
                        if foreign_variant is not None:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Variant with ID {v_in.id} belongs to another product",
                            )
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Variant with ID {v_in.id} not found",
                            )
                else:
                    # New variant to be created
                    new_v = ProductVariant(
                        attribute=v_in.attribute,
                        value=v_in.value,
                        extra_price=v_in.extra_price,
                    )
                    product.variants.append(new_v)

            # Remove omitted variants (replacement semantics)
            for v_existing in list(product.variants):
                if v_existing.id is not None and v_existing.id not in submitted_ids:
                    product.variants.remove(v_existing)
                    db.delete(v_existing)

        db.commit()
        db.refresh(product)
        return product
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update product: {str(e)}",
        )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a product and cascade to variants",
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Safely delete a product:
    - Only administrators can delete products.
    - Associated variants are deleted via cascade configuration.
    - Returns HTTP 404 if product not found.
    """
    stmt = (
        select(Product)
        .options(selectinload(Product.variants))
        .where(Product.id == product_id)
    )
    product = db.scalars(stmt).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )

    try:
        db.delete(product)
        db.commit()
        return {
            "status": "ok",
            "message": f"Product with ID {product_id} and associated variants deleted successfully",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete product: {str(e)}",
        )
