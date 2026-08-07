# Copyright (c) 2020, Youssef Restom and contributors
# For license information, please see license.txt

"""Public invoice API facade backed by `invoice_processing` modules."""

import frappe
import time
from frappe import _
from frappe.utils import flt
from posawesome.posawesome.api.erpnext_compat import resolve_make_sales_invoice_from_order
from posawesome.posawesome.api.tax_contracts import apply_pos_tax_inclusion_contract
from posawesome.posawesome.api.invoice_processing.utils import (
    _get_return_validity_settings,
    _build_invoice_remarks,
    _set_return_valid_upto,
    _validate_return_window,
    get_latest_rate,
    get_price_list_currency,
    get_available_currencies,
)
from posawesome.posawesome.api.invoice_processing.stock import (
    _strip_client_freebies_from_payload,
    _validate_stock_on_invoice,
    _apply_item_name_overrides,
    _deduplicate_free_items,
    _merge_duplicate_taxes,
    _auto_set_return_batches,
    _collect_stock_errors,
    _should_block,
)
from posawesome.posawesome.api.invoice_processing.creation import (
    update_invoice,
    submit_invoice,
    submit_in_background_job,
    repair_invoice_submission,
    validate_cart_items,
)
from posawesome.posawesome.api.invoice_processing.returns import (
    search_invoices_for_return,
    validate_return_items,
    get_invoice_for_return,
)
from posawesome.posawesome.api.invoice_processing.payment import _create_change_payment_entries
from posawesome.posawesome.api.invoice_processing.data import get_last_invoice_rates
from posawesome.posawesome.api.utils import log_perf_event


@frappe.whitelist()
def get_draft_invoices(
    pos_opening_shift=None,
    doctype="Sales Invoice",
    limit_page_length=0,
    company=None,
    pos_profile=None,
    cashier=None,
    is_supervisor=0,
):
    started_at = time.perf_counter()
    try:
        limit_page_length = int(limit_page_length or 0)
    except (TypeError, ValueError):
        limit_page_length = 0
    if limit_page_length < 0:
        limit_page_length = 0

    supervisor_scope = int(is_supervisor or 0)
    filters = {
        "docstatus": 0,
    }
    if supervisor_scope and company:
        filters["company"] = company
        if pos_profile:
            filters["pos_profile"] = pos_profile
        if cashier:
            filters["owner"] = cashier
    else:
        filters["posa_pos_opening_shift"] = pos_opening_shift
    if frappe.db.has_column(doctype, "posa_is_printed"):
        filters["posa_is_printed"] = 0

    requested_fields = [
        "name",
        "customer",
        "customer_name",
        "posting_date",
        "posting_time",
        "grand_total",
        "currency",
        "pos_profile",
        "owner",
        "modified_by",
        "posa_order_type",
        "custom_rider",
        "custom_delivery_status",
        "custom_rider_trip_reference",
    ]
    fields = [f for f in requested_fields if frappe.db.has_column(doctype, f)]

    invoices_list = frappe.get_list(
        doctype,
        filters=filters,
        fields=fields,
        limit_page_length=limit_page_length,
        order_by="modified desc",
    )
    for invoice in invoices_list:
        invoice["doctype"] = doctype
    log_perf_event(
        "get_draft_invoices",
        started_at,
        doctype=doctype,
        rows=len(invoices_list),
    )
    return invoices_list


@frappe.whitelist()
def get_invoice_list(
    doctype="Sales Invoice",
    filters=None,
    fields=None,
    order_by=None,
    limit_page_length=0,
):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    if isinstance(fields, str):
        fields = frappe.parse_json(fields)

    fields = fields or [
        "name",
        "customer",
        "customer_name",
        "posting_date",
        "posting_time",
        "grand_total",
        "paid_amount",
        "outstanding_amount",
        "status",
        "currency",
        "pos_profile",
        "owner",
        "modified_by",
        "posa_order_type",
        "custom_rider",
        "custom_delivery_status",
        "custom_rider_trip_reference",
    ]

    valid_fields = [f for f in fields if frappe.db.has_column(doctype, f)]

    try:
        limit_page_length = int(limit_page_length or 0)
    except (TypeError, ValueError):
        limit_page_length = 0

    return frappe.get_list(
        doctype,
        filters=filters,
        fields=valid_fields,
        order_by=order_by,
        limit_page_length=limit_page_length,
    )


@frappe.whitelist()
def get_draft_invoice_doc(invoice_name, doctype="Sales Invoice"):
    started_at = time.perf_counter()
    doc = frappe.get_cached_doc(doctype, invoice_name)
    log_perf_event(
        "get_draft_invoice_doc",
        started_at,
        doctype=doctype,
        invoice=invoice_name,
        items=len(getattr(doc, "items", []) or []),
    )
    return doc


@frappe.whitelist()
def delete_invoice(invoice):
    from frappe import _
    from posawesome.posawesome.api.invoice import delete_invoice_submission_ledger_entries_for_invoice

    doctype = "Sales Invoice"
    if frappe.db.exists("POS Invoice", invoice):
        doctype = "POS Invoice"
    elif not frappe.db.exists("Sales Invoice", invoice):
        frappe.throw(_("Invoice {0} does not exist").format(invoice))

    if frappe.db.has_column(doctype, "posa_is_printed") and frappe.get_value(
        doctype, invoice, "posa_is_printed"
    ):
        frappe.throw(_("This invoice {0} cannot be deleted").format(invoice))

    frappe.delete_doc(doctype, invoice, force=1)
    delete_invoice_submission_ledger_entries_for_invoice(doctype, invoice)
    return _("Invoice {0} Deleted").format(invoice)


@frappe.whitelist()
def fetch_exchange_rate_pair(from_currency, to_currency):
    """Return exchange rate payload expected by POS multi-currency UI."""

    if not from_currency or not to_currency:
        frappe.throw("from_currency and to_currency are required")

    if from_currency == to_currency:
        from frappe.utils import nowdate

        return {
            "exchange_rate": 1,
            "date": nowdate(),
        }

    exchange_rate, rate_date = get_latest_rate(from_currency, to_currency)
    return {
        "exchange_rate": exchange_rate,
        "date": rate_date,
    }


@frappe.whitelist()
def create_sales_invoice_from_order(sales_order):
    """Backward-compatible facade for legacy frontend method path."""

    if not sales_order:
        frappe.throw("sales_order is required")

    if not frappe.db.exists("Sales Order", sales_order):
        frappe.throw(f"Sales Order {sales_order} does not exist")

    sales_order_doc = frappe.get_doc("Sales Order", sales_order)
    invoice_doc = resolve_make_sales_invoice_from_order()(sales_order)
    invoice_doc.flags.ignore_permissions = True
    invoice_doc.run_method("set_missing_values")
    apply_pos_tax_inclusion_contract(invoice_doc, source_doc=sales_order_doc, recalculate=False)
    invoice_doc.run_method("calculate_taxes_and_totals")
    return invoice_doc


@frappe.whitelist()
def delete_sales_invoice(sales_invoice):
    """Backward-compatible facade for legacy frontend method path."""

    if not sales_invoice:
        frappe.throw("sales_invoice is required")

    if frappe.db.exists("Sales Invoice", sales_invoice):
        frappe.delete_doc("Sales Invoice", sales_invoice, force=1)
    return True


@frappe.whitelist()
def update_invoice_from_order(data):
    """Backward-compatible facade used by order-to-invoice flow."""

    return update_invoice(data)


def make_automatic_payment_for_invoice(doctype, name):
    """Automatically create and submit a Payment Entry for unpaid delivery invoices upon rider assignment."""

    if doctype not in ("Sales Invoice", "POS Invoice"):
        return

    doc = frappe.get_doc(doctype, name)

    # 1. Handle Draft Document (docstatus == 0)
    if doc.docstatus == 0:
        mode_of_payment = None
        if hasattr(doc, "pos_profile") and doc.pos_profile:
            mode_of_payment = frappe.db.get_value("POS Profile", doc.pos_profile, "posa_cash_mode_of_payment")
        if not mode_of_payment:
            mode_of_payment = "Cash"

        cash_account = (
            frappe.db.get_value(
                "Mode of Payment Account",
                {"parent": mode_of_payment, "company": doc.company},
                "default_account",
            )
            or frappe.get_value("Company", doc.company, "default_cash_account")
        )

        if hasattr(doc, "payments"):
            current_paid = sum(flt(p.amount) for p in doc.payments)
            needed = flt(doc.grand_total) - current_paid
            if needed > 0:
                doc.append(
                    "payments",
                    {
                        "mode_of_payment": mode_of_payment,
                        "amount": needed,
                        "account": cash_account,
                        "type": "Cash",
                    },
                )
            doc.paid_amount = flt(doc.grand_total)
            doc.outstanding_amount = 0

        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.save()
        try:
            doc.submit()
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Auto Submit Draft Invoice Error")
        return

    # 2. Handle Submitted Document (docstatus == 1) with outstanding balance
    if doc.docstatus == 1 and flt(doc.outstanding_amount) > 0:
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        pe = get_payment_entry(doctype, name)

        if not pe.mode_of_payment:
            mode_of_payment = None
            if hasattr(doc, "pos_profile") and doc.pos_profile:
                mode_of_payment = frappe.db.get_value(
                    "POS Profile", doc.pos_profile, "posa_cash_mode_of_payment"
                )
            if not mode_of_payment:
                mode_of_payment = "Cash"
            pe.mode_of_payment = mode_of_payment

        if not pe.paid_to:
            cash_account = (
                frappe.db.get_value(
                    "Mode of Payment Account",
                    {"parent": pe.mode_of_payment, "company": doc.company},
                    "default_account",
                )
                or frappe.get_value("Company", doc.company, "default_cash_account")
            )
            pe.paid_to = cash_account

        pe.flags.ignore_permissions = True
        pe.insert(ignore_permissions=True)
        pe.submit()


@frappe.whitelist()
def assign_rider(doctype, name, rider=None, delivery_status=None, trip_reference=None):
    if not doctype or not name:
        frappe.throw(_("Document type and name are required"))

    if not frappe.db.exists(doctype, name):
        frappe.throw(_("{0} {1} does not exist").format(doctype, name))

    rider = str(rider or "").strip()
    status = str(delivery_status or ("Assigned" if rider else "Not Assigned")).strip()

    updates = {
        "custom_rider": rider,
        "custom_delivery_status": status,
    }
    if trip_reference is not None:
        updates["custom_rider_trip_reference"] = str(trip_reference).strip()

    frappe.db.set_value(doctype, name, updates)

    # Automatically process payment entry when assigning a rider
    if rider:
        try:
            make_automatic_payment_for_invoice(doctype, name)
        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                "Automatic Payment Creation on Rider Assignment Failed",
            )

    updated_doc = (
        frappe.db.get_value(
            doctype,
            name,
            ["custom_rider", "custom_delivery_status", "outstanding_amount", "status", "paid_amount"],
            as_dict=True,
        )
        or {}
    )

    return {
        "doctype": doctype,
        "name": name,
        "custom_rider": updated_doc.get("custom_rider", rider),
        "custom_delivery_status": updated_doc.get("custom_delivery_status", status),
        "outstanding_amount": flt(updated_doc.get("outstanding_amount", 0)),
        "status": updated_doc.get("status", "Paid"),
        "paid_amount": flt(updated_doc.get("paid_amount", 0)),
    }


