"""
Tests for Tax API Endpoints, Router Handlers, Lifespan Seeding, and CRUD Operations.
"""

import sys
import os
import unittest
from decimal import Decimal
from fastapi import HTTPException
from pydantic import ValidationError

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base, engine, SessionLocal
from app.services.tax import seed_default_taxes
from app.routers.taxes import (
    create_tax,
    list_taxes,
    get_tax,
    update_tax,
    deactivate_tax,
    calculate_tax_endpoint,
)
from app.schemas.tax import (
    TaxCreate,
    TaxUpdate,
    TaxType,
    TaxCalculateRequest,
)
from app.main import health_check


class TestTaxRouterEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create tables and seed initial taxes."""
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        seed_default_taxes(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_health_check(self):
        """Verify GET / health check returns status ok."""
        res = health_check()
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["service"], "Brightloop Subscription Management System")

    def test_list_seeded_taxes(self):
        """Verify seeded default taxes (5% and 18% GST) are returned."""
        taxes = list_taxes(db=self.db)
        names = [t.name for t in taxes]
        self.assertIn("GST 5%", names)
        self.assertIn("GST 18%", names)

    def test_create_and_get_tax(self):
        """Verify creating and retrieving a custom tax rule."""
        payload = TaxCreate(
            name="GST 12%",
            rate=Decimal("12.00"),
            tax_type=TaxType.GST,
            description="12% rate for specific categories",
            is_active=True,
        )
        created = create_tax(tax_in=payload, db=self.db)
        self.assertEqual(created.name, "GST 12%")
        self.assertEqual(created.rate, Decimal("12.00"))

        retrieved = get_tax(tax_id=created.id, db=self.db)
        self.assertEqual(retrieved.id, created.id)
        self.assertEqual(retrieved.name, "GST 12%")

    def test_create_duplicate_tax_raises_400(self):
        """Creating a tax with an existing name must raise 400 Bad Request."""
        payload = TaxCreate(
            name="gst 18%",
            rate=Decimal("18.00"),
            tax_type=TaxType.GST,
        )
        with self.assertRaises(HTTPException) as cm:
            create_tax(tax_in=payload, db=self.db)
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("already exists", cm.exception.detail)

    def test_tax_inputs_reject_invalid_values(self):
        """Tax rules and calculations reject blank labels and unsupported precision."""
        with self.assertRaises(ValidationError):
            TaxCreate(name="   ", rate=Decimal("18.00"))
        with self.assertRaises(ValidationError):
            TaxCreate(name="GST 12.345%", rate=Decimal("12.345"))
        with self.assertRaises(ValidationError):
            TaxCalculateRequest(
                subtotal_paise=100,
                tax_rate=Decimal("5.00"),
                customer_state="   ",
            )
        with self.assertRaises(ValidationError):
            TaxCalculateRequest(subtotal_paise=100.5, tax_rate=Decimal("5.00"))
        with self.assertRaises(ValidationError):
            TaxCalculateRequest(subtotal_paise=100, tax_rate=Decimal("5.001"))
        with self.assertRaises(ValidationError):
            TaxCalculateRequest(subtotal_paise=100, tax_id=1.5)

    def test_get_nonexistent_tax_raises_404(self):
        """Retrieving a non-existent tax ID must raise 404 Not Found."""
        with self.assertRaises(HTTPException) as cm:
            get_tax(tax_id=99999, db=self.db)
        self.assertEqual(cm.exception.status_code, 404)

    def test_update_tax(self):
        """Updating tax fields must succeed and reflect in the database."""
        new_rule = create_tax(
            tax_in=TaxCreate(name="To Update", rate=Decimal("4.00")),
            db=self.db,
        )
        update_payload = TaxUpdate(name="Updated Name", rate=Decimal("4.50"))
        updated = update_tax(tax_id=new_rule.id, tax_in=update_payload, db=self.db)
        self.assertEqual(updated.name, "Updated Name")
        self.assertEqual(updated.rate, Decimal("4.50"))

    def test_soft_deactivate_tax(self):
        """DELETE deactivates a tax (is_active = False) and prevents duplicate deactivation."""
        new_rule = create_tax(
            tax_in=TaxCreate(name="To Deactivate", rate=Decimal("8.00")),
            db=self.db,
        )
        deactivated = deactivate_tax(tax_id=new_rule.id, db=self.db)
        self.assertFalse(deactivated.is_active)

        # Deactivating again raises 400
        with self.assertRaises(HTTPException) as cm:
            deactivate_tax(tax_id=new_rule.id, db=self.db)
        self.assertEqual(cm.exception.status_code, 400)

    def test_calculate_endpoint_intra_state_gst(self):
        """Calculate endpoint with same state (Kerala) divides tax into CGST & SGST."""
        req = TaxCalculateRequest(
            subtotal_paise=50000,  # ₹500
            tax_rate=Decimal("18.00"),
            customer_state="Kerala",
        )
        res = calculate_tax_endpoint(calc_in=req, db=self.db)
        self.assertEqual(res.subtotal_paise, 50000)
        self.assertEqual(res.tax_amount_paise, 9000)  # ₹90
        self.assertEqual(res.total_paise, 59000)  # ₹590

        breakdown = res.gst_breakdown
        self.assertIsNotNone(breakdown)
        self.assertTrue(breakdown.is_intra_state)
        self.assertEqual(breakdown.cgst_amount_paise, 4500)
        self.assertEqual(breakdown.sgst_amount_paise, 4500)
        self.assertEqual(breakdown.igst_amount_paise, 0)

    def test_calculate_endpoint_inter_state_gst(self):
        """Calculate endpoint with different state (Delhi vs Kerala) applies full IGST."""
        req = TaxCalculateRequest(
            subtotal_paise=50000,  # ₹500
            tax_rate=Decimal("18.00"),
            customer_state="Delhi",
        )
        res = calculate_tax_endpoint(calc_in=req, db=self.db)
        self.assertEqual(res.subtotal_paise, 50000)
        self.assertEqual(res.tax_amount_paise, 9000)
        self.assertEqual(res.total_paise, 59000)

        breakdown = res.gst_breakdown
        self.assertIsNotNone(breakdown)
        self.assertFalse(breakdown.is_intra_state)
        self.assertEqual(breakdown.igst_amount_paise, 9000)
        self.assertEqual(breakdown.cgst_amount_paise, 0)
        self.assertEqual(breakdown.sgst_amount_paise, 0)

    def test_calculate_by_tax_id(self):
        """Calculate endpoint using registered tax_id (GST 18%)."""
        taxes = list_taxes(db=self.db)
        gst_18 = next(t for t in taxes if t.name == "GST 18%")

        req = TaxCalculateRequest(
            subtotal_paise=10000,  # ₹100
            tax_id=gst_18.id,
        )
        res = calculate_tax_endpoint(calc_in=req, db=self.db)
        self.assertEqual(res.subtotal_paise, 10000)
        self.assertEqual(res.effective_tax_rate, Decimal("18.00"))
        self.assertEqual(res.tax_amount_paise, 1800)
        self.assertEqual(res.total_paise, 11800)

    def test_calculate_missing_id_and_rate_raises_400(self):
        """Calculate endpoint without tax_id or tax_rate raises 400 Bad Request."""
        req = TaxCalculateRequest(subtotal_paise=10000)
        with self.assertRaises(HTTPException) as cm:
            calculate_tax_endpoint(calc_in=req, db=self.db)
        self.assertEqual(cm.exception.status_code, 400)

    def test_calculate_rejects_inactive_tax(self):
        """Deactivated tax rules cannot be applied to new calculations."""
        tax = create_tax(
            tax_in=TaxCreate(name="Inactive GST", rate=Decimal("5.00")),
            db=self.db,
        )
        deactivate_tax(tax_id=tax.id, db=self.db)
        req = TaxCalculateRequest(subtotal_paise=10000, tax_id=tax.id)
        with self.assertRaises(HTTPException) as cm:
            calculate_tax_endpoint(calc_in=req, db=self.db)
        self.assertEqual(cm.exception.status_code, 400)

    def test_calculate_rejects_multiple_rate_sources(self):
        """A calculation must use either a saved tax or a custom rate, not both."""
        tax = next(t for t in list_taxes(db=self.db) if t.name == "GST 18%")
        req = TaxCalculateRequest(
            subtotal_paise=10000,
            tax_id=tax.id,
            tax_rate=Decimal("5.00"),
        )
        with self.assertRaises(HTTPException) as cm:
            calculate_tax_endpoint(calc_in=req, db=self.db)
        self.assertEqual(cm.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
