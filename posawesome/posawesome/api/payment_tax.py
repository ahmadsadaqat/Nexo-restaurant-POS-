# -*- coding: utf-8 -*-
# Copyright (c) 2026, defendicon and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, cint


def _get_payment_tax_mappings(pos_profile):
    """Return the payment-method → tax-template mappings from POS Profile.

    Returns a dict keyed by mode_of_payment name to tax template name,
    or an empty dict if the feature is disabled or unconfigured.
    """
    if not pos_profile:
        return {}

    enabled = cint(
        frappe.get_cached_value("POS Profile", pos_profile, "posa_enable_payment_tax_templates")
    )
    if not enabled:
        return {}

    rows = frappe.get_all(
        "POS Payment Tax Template",
        filters={"parent": pos_profile, "parenttype": "POS Profile"},
        fields=["mode_of_payment", "tax_template"],
        order_by="idx asc",
    )

    return {row.mode_of_payment: row.tax_template for row in rows if row.mode_of_payment and row.tax_template}


def resolve_tax_template_for_payments(pos_profile, payments):
    """Determine which tax template to use based on payment method amounts.

    Args:
        pos_profile: POS Profile name.
        payments: list of dicts/objects with 'mode_of_payment' and 'amount'.

    Returns:
        str or None: The tax template name to use, or None to keep the default.
    """
    mappings = _get_payment_tax_mappings(pos_profile)
    if not mappings:
        return None

    if not payments:
        return None

    # Find the dominant payment method (highest positive amount)
    best_mop = None
    best_amount = 0

    for payment in payments:
        if hasattr(payment, "get"):
            mop = payment.get("mode_of_payment")
            amount = flt(payment.get("amount", 0))
        else:
            mop = getattr(payment, "mode_of_payment", None)
            amount = flt(getattr(payment, "amount", 0))

        if not mop or amount <= 0:
            continue

        if mop in mappings and amount > best_amount:
            best_amount = amount
            best_mop = mop

    if best_mop:
        return mappings[best_mop]

    return None


def apply_payment_tax_template(invoice_doc, payments=None):
    """Apply the correct tax template based on payment methods on the invoice.

    This replaces the invoice's taxes child table with rows from the
    resolved template. If no payment-specific template matches, the
    invoice taxes are left unchanged (using the default POS Profile template).

    Args:
        invoice_doc: The Sales/POS Invoice document object.
        payments: Optional list of payment rows. If None, uses invoice_doc.payments.

    Returns:
        bool: True if the tax template was changed, False otherwise.
    """
    if not invoice_doc.pos_profile:
        return False

    if payments is None:
        payments = invoice_doc.get("payments") or []

    template_name = resolve_tax_template_for_payments(invoice_doc.pos_profile, payments)
    if not template_name:
        return False

    # Check if the template is already applied
    current_template = invoice_doc.get("taxes_and_charges")
    if current_template == template_name:
        return False

    # Fetch the template and apply its tax rows
    try:
        template_doc = frappe.get_cached_doc("Sales Taxes and Charges Template", template_name)
    except frappe.DoesNotExistError:
        frappe.log_error(
            f"Tax template '{template_name}' configured in POS Profile "
            f"'{invoice_doc.pos_profile}' does not exist.",
            "POS Payment Tax Template Error",
        )
        return False

    # Clear existing taxes and apply from template
    invoice_doc.set("taxes", [])
    invoice_doc.taxes_and_charges = template_name

    for row in template_doc.taxes:
        tax_row = invoice_doc.append("taxes", {})
        tax_row.update(
            {
                "charge_type": row.charge_type,
                "account_head": row.account_head,
                "description": row.description,
                "rate": row.rate,
                "tax_amount": row.tax_amount if row.charge_type == "Actual" else 0,
                "cost_center": row.cost_center,
                "included_in_print_rate": row.included_in_print_rate,
                "included_in_paid_amount": row.get("included_in_paid_amount") or 0,
            }
        )

    # Recalculate taxes and totals
    if hasattr(invoice_doc, "calculate_taxes_and_totals"):
        invoice_doc.calculate_taxes_and_totals()

    return True


@frappe.whitelist()
def get_tax_template_for_payment(pos_profile, payments):
    """API endpoint to resolve the tax template for given payments.

    Args:
        pos_profile: POS Profile name.
        payments: JSON string or list of payment rows.

    Returns:
        dict with 'tax_template' (name or None) and 'taxes' (list of tax rows).
    """
    import json

    if isinstance(payments, str):
        payments = json.loads(payments)

    template_name = resolve_tax_template_for_payments(pos_profile, payments)

    result = {"tax_template": template_name, "taxes": []}

    if template_name:
        try:
            template_doc = frappe.get_cached_doc("Sales Taxes and Charges Template", template_name)
            result["taxes"] = [
                {
                    "charge_type": row.charge_type,
                    "account_head": row.account_head,
                    "description": row.description,
                    "rate": row.rate,
                    "tax_amount": row.tax_amount if row.charge_type == "Actual" else 0,
                    "cost_center": row.cost_center,
                    "included_in_print_rate": row.included_in_print_rate,
                    "included_in_paid_amount": row.get("included_in_paid_amount") or 0,
                }
                for row in template_doc.taxes
            ]
        except frappe.DoesNotExistError:
            result["tax_template"] = None

    return result


@frappe.whitelist()
def test_sales_invoice_table():
    import frappe
    # reset status
    frappe.db.set_value("Table", "Table No. 3", "status", "Available")
    frappe.db.commit()
    doc = frappe.get_doc({
        "doctype": "Sales Invoice",
        "company": "Nexo ERP (Demo)",
        "customer": "Test Lead Name",
        "posa_table_no": "Table No. 3",
        "is_pos": 1,
        "items": [{
            "item_code": "Plumber",
            "qty": 1,
            "rate": 10
        }]
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    status = frappe.db.get_value("Table", "Table No. 3", "status")
    return {"status_after_insert": status, "docname": doc.name}

