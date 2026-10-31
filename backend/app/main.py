"""
main.py — FastAPI application factory for the Brightloop Subscription Management System.

Responsibilities:
  - Create and configure the FastAPI application instance.
  - Register CORS middleware (React dev server at http://localhost:5173).
  - Mount all domain routers under the /api prefix.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.routers import (
    auth,
    users,
    products,
    plans,
    settings,
    imports,
    templates,
    subscriptions,
    invoices,
    taxes,
    discounts,
    payments,
    reports,
)

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Brightloop Subscription Management System",
    description="Backend API for managing subscriptions, plans, billing and reporting.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow the React frontend running on Vite's default dev port.
# Add production origins here when deploying.
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server (React frontend)
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# Each router is mounted under /api/<domain> and tagged for Swagger grouping.
# ---------------------------------------------------------------------------
app.include_router(auth.router,          prefix="/api/auth",          tags=["Auth"])
app.include_router(users.router,         prefix="/api/users",         tags=["Users"])
app.include_router(products.router,      prefix="/api/products",      tags=["Products"])
app.include_router(plans.router,         prefix="/api/plans",         tags=["Plans"])
app.include_router(settings.router,      prefix="/api/settings",      tags=["Settings"])
app.include_router(imports.router,       prefix="/api/imports",       tags=["Imports"])
app.include_router(templates.router,     prefix="/api/templates",     tags=["Templates"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["Subscriptions"])
app.include_router(invoices.router,      prefix="/api/invoices",      tags=["Invoices"])
app.include_router(taxes.router,         prefix="/api/taxes",         tags=["Taxes"])
app.include_router(discounts.router,     prefix="/api/discounts",     tags=["Discounts"])
app.include_router(payments.router,      prefix="/api/payments",      tags=["Payments"])
app.include_router(reports.router,       prefix="/api/reports",       tags=["Reports"])


# ---------------------------------------------------------------------------
# OpenAPI schema customization
# Deduplicate operation tags so Swagger UI renders cleanly.
# ---------------------------------------------------------------------------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "tags" in operation:
                operation["tags"] = list(dict.fromkeys(operation["tags"]))
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
