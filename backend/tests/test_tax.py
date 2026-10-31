"""
Unit Tests for Tax Management, Decimal Arithmetic, Rounding, and Indian GST Rules.
"""

import sys
import os
from decimal import Decimal
import unittest
from unittest.mock import patch

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.tax import Tax
from app.services.tax import (
    calculate_tax,
    calculate_gst,
    apply_tax_to_amount,
    DEFAULT_TAX_SEEDS,
    get_company_state,
)


class TestTaxCalculations(unittest.TestCase):
    """Test tax calculation logic, rounding rules, and GST split rules."""

    def test_standard_tax_calculation(self):
        """Test calculation of standard 18% tax on ₹100 (10000 paise)."""
        subtotal_paise = 10000  # ₹100
        rate = Decimal("18.00")  # 18%

        result = calculate_tax(subtotal_paise, rate)
        self.assertEqual(result["subtotal_paise"], 10000)
        self.assertEqual(result["tax_rate"], Decimal("18.00"))
        self.assertEqual(result["tax_amount_paise"], 1800)  # ₹18
        self.assertEqual(result["total_paise"], 11800)  # ₹118

    def test_zero_tax_rate(self):
        """Test tax calculation when rate is 0%."""
        subtotal_paise = 5000  # ₹50
        rate = Decimal("0.00")

        result = calculate_tax(subtotal_paise, rate)
        self.assertEqual(result["tax_amount_paise"], 0)
        self.assertEqual(result["total_paise"], 5000)

    def test_rounding_half_up_rule(self):
        """
        Verify ROUND_HALF_UP rounding:
        - 150 paise at 5% = 7.50 paise -> rounds up to 8 paise
        - 155 paise at 18% = 27.90 paise -> rounds up to 28 paise
        - 140 paise at 5% = 7.00 paise -> 7 paise
        """
        res1 = calculate_tax(150, Decimal("5.00"))
        self.assertEqual(res1["tax_amount_paise"], 8)
        self.assertEqual(res1["total_paise"], 158)

        res2 = calculate_tax(155, Decimal("18.00"))
        self.assertEqual(res2["tax_amount_paise"], 28)
        self.assertEqual(res2["total_paise"], 183)

        res3 = calculate_tax(140, Decimal("5.00"))
        self.assertEqual(res3["tax_amount_paise"], 7)
        self.assertEqual(res3["total_paise"], 147)

    def test_invalid_subtotal_or_rate(self):
        """Verify that negative amounts or invalid rates raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_tax(-100, Decimal("18.00"))

        with self.assertRaises(ValueError):
            calculate_tax(1000, Decimal("-1.00"))

        with self.assertRaises(ValueError):
            calculate_tax(1000, Decimal("105.00"))

    def test_gst_intra_state_split(self):
        """
        Test Indian GST intra-state transaction:
        When Customer State == Company State, tax must split into equal CGST and SGST.
        For 18% GST on ₹100 (10000 paise):
        - CGST: 9% = 900 paise
        - SGST: 9% = 900 paise
        - Total Tax: 1800 paise
        - IGST: 0 paise
        """
        res = calculate_gst(
            subtotal_paise=10000,
            tax_rate=Decimal("18.00"),
            customer_state="Kerala",
            company_state="Kerala",
        )
        self.assertEqual(res["tax_amount_paise"], 1800)
        self.assertEqual(res["total_paise"], 11800)

        breakdown = res["gst_breakdown"]
        self.assertTrue(breakdown["is_intra_state"])
        self.assertEqual(breakdown["cgst_rate"], Decimal("9.00"))
        self.assertEqual(breakdown["cgst_amount_paise"], 900)
        self.assertEqual(breakdown["sgst_rate"], Decimal("9.00"))
        self.assertEqual(breakdown["sgst_amount_paise"], 900)
        self.assertEqual(breakdown["igst_rate"], Decimal("0.0"))
        self.assertEqual(breakdown["igst_amount_paise"], 0)

    def test_gst_inter_state_igst(self):
        """
        Test Indian GST inter-state transaction:
        When Customer State != Company State, full rate applies as IGST.
        For 18% GST on ₹100 (10000 paise):
        - IGST: 18% = 1800 paise
        - CGST: 0 paise
        - SGST: 0 paise
        - Total Tax: 1800 paise
        """
        res = calculate_gst(
            subtotal_paise=10000,
            tax_rate=Decimal("18.00"),
            customer_state="Maharashtra",
            company_state="Kerala",
        )
        self.assertEqual(res["tax_amount_paise"], 1800)
        self.assertEqual(res["total_paise"], 11800)

        breakdown = res["gst_breakdown"]
        self.assertFalse(breakdown["is_intra_state"])
        self.assertEqual(breakdown["igst_rate"], Decimal("18.00"))
        self.assertEqual(breakdown["igst_amount_paise"], 1800)
        self.assertEqual(breakdown["cgst_amount_paise"], 0)
        self.assertEqual(breakdown["sgst_amount_paise"], 0)

    def test_intra_state_gst_rounding_components_equal_total(self):
        """Rounded CGST and SGST components must sum to the rounded GST total."""
        result = calculate_gst(
            subtotal_paise=10,
            tax_rate=Decimal("5.00"),
            customer_state="Kerala",
            company_state="Kerala",
        )
        breakdown = result["gst_breakdown"]
        self.assertEqual(result["tax_amount_paise"], 1)
        self.assertEqual(
            breakdown["cgst_amount_paise"] + breakdown["sgst_amount_paise"],
            result["tax_amount_paise"],
        )

    def test_company_state_defaults_to_kerala(self):
        """Kerala is the company-state fallback when configuration is blank or absent."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_company_state(), "Kerala")
        with patch.dict(os.environ, {"COMPANY_STATE": "  "}):
            self.assertEqual(get_company_state(), "Kerala")

    def test_apply_tax_to_amount_integration(self):
        """Test the integration helper apply_tax_to_amount for invoice line calculations."""
        active_tax = Tax(
            id=1,
            name="GST 18%",
            rate=Decimal("18.00"),
            tax_type="gst",
            is_active=True,
        )
        # With GST state breakdown
        res = apply_tax_to_amount(
            subtotal_paise=20000,
            tax=active_tax,
            customer_state="Kerala",
        )
        self.assertEqual(res["total_paise"], 23600)
        self.assertTrue(res["gst_breakdown"]["is_intra_state"])

        # Deactivated tax raises error
        inactive_tax = Tax(
            id=2,
            name="Old GST",
            rate=Decimal("18.00"),
            tax_type="gst",
            is_active=False,
        )
        with self.assertRaises(ValueError):
            apply_tax_to_amount(20000, inactive_tax)

    def test_seed_tax_defaults(self):
        """Verify that default seed data defines 5% and 18% GST rates."""
        names = [s["name"] for s in DEFAULT_TAX_SEEDS]
        rates = [s["rate"] for s in DEFAULT_TAX_SEEDS]
        self.assertIn("GST 5%", names)
        self.assertIn("GST 18%", names)
        self.assertIn(Decimal("5.00"), rates)
        self.assertIn(Decimal("18.00"), rates)


if __name__ == "__main__":
    unittest.main()
