# Copyright (c) 2026, POSAwesome contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from posawesome.posawesome.doctype.pos_closing_shift.closing_processing.utils import get_base_value


REPORT_VIEWS = {"Daily Summary", "Shift Summary", "Invoice Details"}
PAYMENT_CATEGORIES = {"All", "Cash", "Card", "Other"}
DIFFERENCE_TOLERANCE = 0.005


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	openings = get_opening_shifts(filters)
	if not openings:
		return get_columns(filters), [], _("No POS opening shifts matched the selected filters.")

	profile_settings = get_profile_settings({row.pos_profile for row in openings if row.pos_profile})
	closing_by_shift = get_closing_shifts([row.name for row in openings])
	invoices = get_invoices(openings, profile_settings)
	payment_rows = get_invoice_payments(invoices)
	reconciliation_rows = get_reconciliation_rows(closing_by_shift)
	mop_types = get_mode_of_payment_types(payment_rows, reconciliation_rows, profile_settings)
	currencies = get_company_currencies({row.company for row in openings if row.company})

	shift_rows, invoice_rows = build_report_rows(
		openings,
		closing_by_shift,
		invoices,
		payment_rows,
		reconciliation_rows,
		profile_settings,
		mop_types,
		currencies,
	)

	shift_rows = apply_shift_filters(shift_rows, filters)
	view = filters.report_view

	if view == "Daily Summary":
		data = build_daily_rows(shift_rows)
	elif view == "Invoice Details":
		data = apply_invoice_filters(invoice_rows, shift_rows, filters)
	else:
		data = shift_rows

	message = None if data else _("No transactions matched the selected report filters.")
	return (
		get_columns(filters),
		data,
		message,
		get_chart(view, data),
		get_report_summary(shift_rows, data, view),
	)


def validate_filters(filters):
	filters.report_view = filters.get("report_view") or "Daily Summary"
	filters.payment_category = filters.get("payment_category") or "All"
	filters.shift_status = filters.get("shift_status") or "All"

	if filters.report_view not in REPORT_VIEWS:
		frappe.throw(_("Invalid report view."))
	if filters.payment_category not in PAYMENT_CATEGORIES:
		frappe.throw(_("Invalid mode of payment filter."))
	if not filters.get("company"):
		frappe.throw(_("Company is required."))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required."))
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))


def get_opening_shifts(filters):
	db_filters = {
		"company": filters.company,
		"posting_date": ["between", [filters.from_date, filters.to_date]],
		"docstatus": ["<", 2],
	}

	if filters.get("cashier"):
		db_filters["user"] = filters.cashier
	if filters.get("pos_profile"):
		db_filters["pos_profile"] = filters.pos_profile
	if filters.get("opening_shift"):
		db_filters["name"] = filters.opening_shift
	if filters.shift_status != "All":
		db_filters["status"] = filters.shift_status

	return frappe.get_list(
		"POS Opening Shift",
		filters=db_filters,
		fields=[
			"name",
			"posting_date",
			"period_start_date",
			"period_end_date",
			"status",
			"company",
			"pos_profile",
			"user",
			"pos_closing_shift",
			"docstatus",
		],
		order_by="posting_date desc, period_start_date desc",
		limit_page_length=0,
	)


def get_profile_settings(profile_names):
	if not profile_names:
		return {}

	rows = frappe.get_all(
		"POS Profile",
		filters={"name": ["in", list(profile_names)]},
		fields=[
			"name",
			"company",
			"posa_cash_mode_of_payment",
			"create_pos_invoice_instead_of_sales_invoice",
		],
		limit_page_length=0,
	)
	return {row.name: row for row in rows}


def get_closing_shifts(opening_shift_names):
	if not opening_shift_names:
		return {}

	rows = frappe.get_list(
		"POS Closing Shift",
		filters={
			"pos_opening_shift": ["in", opening_shift_names],
			"docstatus": ["<", 2],
		},
		fields=[
			"name",
			"pos_opening_shift",
			"posting_date",
			"period_start_date",
			"period_end_date",
			"company",
			"pos_profile",
			"user",
			"grand_total",
			"net_total",
			"total_quantity",
			"docstatus",
			"creation",
		],
		order_by="docstatus desc, creation desc",
		limit_page_length=0,
	)

	closing_by_shift = {}
	for row in rows:
		closing_by_shift.setdefault(row.pos_opening_shift, row)
	return closing_by_shift


def get_invoices(openings, profile_settings):
	shift_names_by_doctype = defaultdict(list)
	for opening in openings:
		settings = profile_settings.get(opening.pos_profile) or {}
		doctype = (
			"POS Invoice"
			if cint(settings.get("create_pos_invoice_instead_of_sales_invoice"))
			else "Sales Invoice"
		)
		shift_names_by_doctype[doctype].append(opening.name)

	fields = [
		"name",
		"posting_date",
		"posting_time",
		"customer",
		"customer_name",
		"owner",
		"company",
		"pos_profile",
		"posa_pos_opening_shift",
		"is_return",
		"return_against",
		"currency",
		"conversion_rate",
		"grand_total",
		"base_grand_total",
		"net_total",
		"base_net_total",
		"total_qty",
		"change_amount",
		"base_change_amount",
	]
	invoices = []

	for doctype, shift_names in shift_names_by_doctype.items():
		if not shift_names or not frappe.get_meta(doctype).has_field("posa_pos_opening_shift"):
			continue

		rows = frappe.get_list(
			doctype,
			filters={
				"docstatus": 1,
				"posa_pos_opening_shift": ["in", shift_names],
			},
			fields=fields,
			order_by="posting_date asc, posting_time asc, creation asc",
			limit_page_length=0,
		)
		for row in rows:
			row.invoice_doctype = doctype
		invoices.extend(rows)

	return invoices


def get_invoice_payments(invoices):
	if not invoices:
		return []

	invoice_names = [row.name for row in invoices]
	invoice_doctypes = sorted({row.invoice_doctype for row in invoices})
	return frappe.get_all(
		"Sales Invoice Payment",
		filters={
			"parent": ["in", invoice_names],
			"parenttype": ["in", invoice_doctypes],
			"parentfield": "payments",
		},
		fields=["parent", "parenttype", "mode_of_payment", "type", "amount", "base_amount", "idx"],
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)


def get_reconciliation_rows(closing_by_shift):
	closing_names = [row.name for row in closing_by_shift.values()]
	if not closing_names:
		return []

	return frappe.get_all(
		"POS Closing Shift Detail",
		filters={"parent": ["in", closing_names], "parentfield": "payment_reconciliation"},
		fields=[
			"parent",
			"mode_of_payment",
			"opening_amount",
			"expected_amount",
			"closing_amount",
			"difference",
			"idx",
		],
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)


def get_mode_of_payment_types(payment_rows, reconciliation_rows, profile_settings):
	names = {row.get("mode_of_payment") for row in payment_rows + reconciliation_rows}
	names.update(row.get("posa_cash_mode_of_payment") for row in profile_settings.values())
	names.discard(None)
	names.discard("")
	if not names:
		return {}

	return {
		row.name: row.type
		for row in frappe.get_all(
			"Mode of Payment",
			filters={"name": ["in", list(names)]},
			fields=["name", "type"],
			limit_page_length=0,
		)
	}


def get_company_currencies(companies):
	return {
		company: frappe.get_cached_value("Company", company, "default_currency")
		for company in companies
	}


def build_report_rows(
	openings,
	closing_by_shift,
	invoices,
	payment_rows,
	reconciliation_rows,
	profile_settings,
	mop_types,
	currencies,
):
	invoices_by_shift = defaultdict(list)
	for invoice in invoices:
		invoices_by_shift[invoice.posa_pos_opening_shift].append(invoice)

	payments_by_invoice = defaultdict(list)
	for payment in payment_rows:
		payments_by_invoice[(payment.parenttype, payment.parent)].append(payment)

	reconciliation_by_closing = defaultdict(list)
	for row in reconciliation_rows:
		reconciliation_by_closing[row.parent].append(row)

	shift_rows = []
	invoice_rows = []
	for opening in openings:
		closing = closing_by_shift.get(opening.name)
		settings = profile_settings.get(opening.pos_profile) or {}
		cash_mode = settings.get("posa_cash_mode_of_payment") or "Cash"
		currency = currencies.get(opening.company)
		shift_invoices = invoices_by_shift.get(opening.name, [])

		shift_row, shift_invoice_rows = build_shift_row(
			opening,
			closing,
			shift_invoices,
			payments_by_invoice,
			reconciliation_by_closing.get(closing.name, []) if closing else [],
			mop_types,
			cash_mode,
			currency,
		)
		shift_rows.append(shift_row)
		invoice_rows.extend(shift_invoice_rows)

	return shift_rows, invoice_rows


def build_shift_row(
	opening,
	closing,
	invoices,
	payments_by_invoice,
	reconciliation_rows,
	mop_types,
	cash_mode,
	currency,
):
	row = frappe._dict(
		{
			"report_date": opening.posting_date,
			"opening_shift": opening.name,
			"closing_shift": closing.name if closing else None,
			"closing_status": get_closing_status(closing),
			"shift_status": opening.status,
			"cashier": opening.user,
			"pos_profile": opening.pos_profile,
			"company": opening.company,
			"currency": currency,
			"period_start_date": opening.period_start_date,
			"period_end_date": closing.period_end_date if closing else opening.period_end_date,
			"invoice_count": len(invoices),
			"gross_sales": 0,
			"returns_total": 0,
			"actual_sales": 0,
			"actual_net_total": 0,
			"actual_quantity": 0,
			"cash_payment": 0,
			"card_payment": 0,
			"other_payment": 0,
			"invoice_payment_total": 0,
			"saved_closing_total": flt(closing.grand_total) if closing else 0,
			"saved_closing_net_total": flt(closing.net_total) if closing else 0,
			"saved_closing_quantity": flt(closing.total_quantity) if closing else 0,
			"opening_cash": 0,
			"opening_card": 0,
			"opening_other": 0,
			"expected_cash": 0,
			"expected_card": 0,
			"expected_other": 0,
			"counted_cash": 0,
			"counted_card": 0,
			"counted_other": 0,
			"cash_difference": 0,
			"card_difference": 0,
			"other_difference": 0,
		}
	)

	invoice_rows = []
	for invoice in invoices:
		invoice_total = get_base_value(
			invoice, "grand_total", "base_grand_total", invoice.get("conversion_rate")
		)
		invoice_net_total = get_base_value(
			invoice, "net_total", "base_net_total", invoice.get("conversion_rate")
		)
		category_amounts, payment_methods = get_invoice_payment_totals(
			invoice,
			payments_by_invoice.get((invoice.invoice_doctype, invoice.name), []),
			mop_types,
			cash_mode,
		)

		row.actual_sales += invoice_total
		row.actual_net_total += invoice_net_total
		row.actual_quantity += flt(invoice.total_qty)
		if invoice_total >= 0:
			row.gross_sales += invoice_total
		else:
			row.returns_total += abs(invoice_total)

		for category in ("cash", "card", "other"):
			row[f"{category}_payment"] += category_amounts[category]
		row.invoice_payment_total += sum(category_amounts.values())

		invoice_rows.append(
			frappe._dict(
				{
					"report_date": opening.posting_date,
					"posting_date": invoice.posting_date,
					"posting_time": invoice.posting_time,
					"invoice_doctype": invoice.invoice_doctype,
					"invoice": invoice.name,
					"opening_shift": opening.name,
					"closing_shift": closing.name if closing else None,
					"shift_status": opening.status,
					"cashier": opening.user,
					"created_by": invoice.owner,
					"pos_profile": opening.pos_profile,
					"company": opening.company,
					"customer": invoice.customer,
					"customer_name": invoice.customer_name,
					"is_return": invoice.is_return,
					"return_against": invoice.return_against,
					"invoice_total": invoice_total,
					"invoice_net_total": invoice_net_total,
					"quantity": flt(invoice.total_qty),
					"cash_payment": category_amounts["cash"],
					"card_payment": category_amounts["card"],
					"other_payment": category_amounts["other"],
					"invoice_payment_total": sum(category_amounts.values()),
					"credit_or_unpaid": invoice_total - sum(category_amounts.values()),
					"payment_methods": ", ".join(payment_methods),
					"currency": currency,
				}
			)
		)

	for detail in reconciliation_rows:
		category = get_payment_category(
			detail.mode_of_payment,
			mop_types.get(detail.mode_of_payment),
			cash_mode,
		)
		row[f"opening_{category}"] += flt(detail.opening_amount)
		row[f"expected_{category}"] += flt(detail.expected_amount)
		row[f"counted_{category}"] += flt(detail.closing_amount)
		row[f"{category}_difference"] += flt(detail.difference)

	row.sales_difference = row.actual_sales - row.saved_closing_total
	row.quantity_difference = row.actual_quantity - row.saved_closing_quantity
	row.expected_total = sum(row[f"expected_{category}"] for category in ("cash", "card", "other"))
	row.counted_total = sum(row[f"counted_{category}"] for category in ("cash", "card", "other"))
	row.payment_difference = sum(
		row[f"{category}_difference"] for category in ("cash", "card", "other")
	)
	row.has_difference = has_difference(row)

	for invoice_row in invoice_rows:
		invoice_row.shift_sales_difference = row.sales_difference
		invoice_row.shift_has_difference = row.has_difference

	return row, invoice_rows


def get_invoice_payment_totals(invoice, payment_rows, mop_types, cash_mode):
	totals = {"cash": 0, "card": 0, "other": 0}
	payment_methods = []
	for payment in payment_rows:
		category = get_payment_category(
			payment.mode_of_payment,
			payment.get("type") or mop_types.get(payment.mode_of_payment),
			cash_mode,
		)
		totals[category] += get_base_value(
			payment, "amount", "base_amount", invoice.get("conversion_rate")
		)
		if payment.mode_of_payment and payment.mode_of_payment not in payment_methods:
			payment_methods.append(payment.mode_of_payment)

	change_amount = get_base_value(
		invoice, "change_amount", "base_change_amount", invoice.get("conversion_rate")
	)
	if change_amount:
		totals["cash"] -= change_amount

	return totals, payment_methods


def get_payment_category(mode_of_payment, payment_type=None, cash_mode="Cash"):
	mode = (mode_of_payment or "").strip().lower()
	payment_type = (payment_type or "").strip().lower()
	cash_mode = (cash_mode or "Cash").strip().lower()

	if mode == cash_mode or payment_type == "cash" or mode == "cash":
		return "cash"
	if "card" in mode or payment_type == "bank":
		return "card"
	return "other"


def get_closing_status(closing):
	if not closing:
		return _("Not Created")
	return _("Submitted") if cint(closing.docstatus) == 1 else _("Draft")


def has_difference(row, payment_category="All"):
	if abs(flt(row.get("sales_difference"))) >= DIFFERENCE_TOLERANCE:
		return True

	if payment_category != "All":
		return abs(flt(row.get(f"{payment_category.lower()}_difference"))) >= DIFFERENCE_TOLERANCE

	return any(
		abs(flt(row.get(f"{category}_difference"))) >= DIFFERENCE_TOLERANCE
		for category in ("cash", "card", "other")
	)


def apply_shift_filters(rows, filters):
	category = filters.payment_category
	filtered = []
	for row in rows:
		if category != "All" and not category_has_activity(row, category.lower()):
			continue
		if cint(filters.get("differences_only")) and not has_difference(row, category):
			continue
		filtered.append(row)
	return filtered


def category_has_activity(row, category):
	return any(
		abs(flt(row.get(fieldname))) >= DIFFERENCE_TOLERANCE
		for fieldname in (
			f"{category}_payment",
			f"opening_{category}",
			f"expected_{category}",
			f"counted_{category}",
			f"{category}_difference",
		)
	)


def apply_invoice_filters(invoice_rows, shift_rows, filters):
	allowed_shifts = {row.opening_shift for row in shift_rows}
	category = filters.payment_category
	result = []
	for row in invoice_rows:
		if row.opening_shift not in allowed_shifts:
			continue
		if category != "All" and abs(flt(row.get(f"{category.lower()}_payment"))) < DIFFERENCE_TOLERANCE:
			continue
		result.append(row)
	return result


def build_daily_rows(shift_rows):
	numeric_fields = [
		"invoice_count",
		"gross_sales",
		"returns_total",
		"actual_sales",
		"saved_closing_total",
		"sales_difference",
		"cash_payment",
		"card_payment",
		"other_payment",
		"invoice_payment_total",
		"expected_cash",
		"expected_card",
		"expected_other",
		"counted_cash",
		"counted_card",
		"counted_other",
		"cash_difference",
		"card_difference",
		"other_difference",
		"expected_total",
		"counted_total",
		"payment_difference",
	]
	grouped = {}

	for shift in shift_rows:
		key = (shift.report_date, shift.cashier, shift.pos_profile)
		if key not in grouped:
			grouped[key] = frappe._dict(
				{
					"report_date": shift.report_date,
					"cashier": shift.cashier,
					"pos_profile": shift.pos_profile,
					"company": shift.company,
					"currency": shift.currency,
					"shift_count": 0,
					"open_shifts": 0,
					"closed_shifts": 0,
					"discrepancy_shift_count": 0,
					**{fieldname: 0 for fieldname in numeric_fields},
				}
			)

		row = grouped[key]
		row.shift_count += 1
		if shift.shift_status == "Closed":
			row.closed_shifts += 1
		else:
			row.open_shifts += 1
		if shift.has_difference:
			row.discrepancy_shift_count += 1
		for fieldname in numeric_fields:
			row[fieldname] += flt(shift.get(fieldname))

	return sorted(
		grouped.values(),
		key=lambda row: (getdate(row.report_date), row.cashier or "", row.pos_profile or ""),
		reverse=True,
	)


def get_columns(filters):
	view = filters.report_view
	if view == "Daily Summary":
		columns = get_daily_columns()
	elif view == "Invoice Details":
		columns = get_invoice_columns()
	else:
		columns = get_shift_columns()

	return insert_payment_columns(columns, filters.payment_category, view)


def get_daily_columns():
	return [
		column(_("Business Date"), "report_date", "Date", 105),
		column(_("Cashier"), "cashier", "Link", 170, "User"),
		column(_("POS Profile"), "pos_profile", "Link", 150, "POS Profile"),
		column(_("Shifts"), "shift_count", "Int", 70),
		column(_("Closed"), "closed_shifts", "Int", 70),
		column(_("Open"), "open_shifts", "Int", 65),
		column(_("Invoices"), "invoice_count", "Int", 75),
		currency_column(_("Gross Sales"), "gross_sales"),
		currency_column(_("Returns"), "returns_total"),
		currency_column(_("Actual Sales"), "actual_sales"),
		currency_column(_("Saved Closing"), "saved_closing_total"),
		currency_column(_("Sales Difference"), "sales_difference"),
		column(_("Discrepant Shifts"), "discrepancy_shift_count", "Int", 115),
		column(_("Currency"), "currency", "Link", 85, "Currency"),
	]


def get_shift_columns():
	return [
		column(_("Business Date"), "report_date", "Date", 105),
		column(_("Opening Shift"), "opening_shift", "Link", 185, "POS Opening Shift"),
		column(_("Closing Shift"), "closing_shift", "Link", 185, "POS Closing Shift"),
		column(_("Closing Document"), "closing_status", "Data", 115),
		column(_("Shift Status"), "shift_status", "Data", 100),
		column(_("Cashier"), "cashier", "Link", 170, "User"),
		column(_("POS Profile"), "pos_profile", "Link", 150, "POS Profile"),
		column(_("Started"), "period_start_date", "Datetime", 155),
		column(_("Ended"), "period_end_date", "Datetime", 155),
		column(_("Invoices"), "invoice_count", "Int", 75),
		currency_column(_("Gross Sales"), "gross_sales"),
		currency_column(_("Returns"), "returns_total"),
		currency_column(_("Actual Sales"), "actual_sales"),
		currency_column(_("Saved Closing"), "saved_closing_total"),
		currency_column(_("Sales Difference"), "sales_difference"),
		column(_("Actual Qty"), "actual_quantity", "Float", 95),
		column(_("Saved Qty"), "saved_closing_quantity", "Float", 90),
		column(_("Qty Difference"), "quantity_difference", "Float", 105),
		column(_("Currency"), "currency", "Link", 85, "Currency"),
	]


def get_invoice_columns():
	return [
		column(_("Business Date"), "report_date", "Date", 105),
		column(_("Posting Date"), "posting_date", "Date", 100),
		column(_("Posting Time"), "posting_time", "Time", 95),
		column(_("Document Type"), "invoice_doctype", "Link", 110, "DocType"),
		column(_("Invoice"), "invoice", "Dynamic Link", 145, "invoice_doctype"),
		column(_("Opening Shift"), "opening_shift", "Link", 180, "POS Opening Shift"),
		column(_("Closing Shift"), "closing_shift", "Link", 180, "POS Closing Shift"),
		column(_("Shift Status"), "shift_status", "Data", 95),
		column(_("Cashier"), "cashier", "Link", 165, "User"),
		column(_("Created By"), "created_by", "Link", 165, "User"),
		column(_("POS Profile"), "pos_profile", "Link", 145, "POS Profile"),
		column(_("Customer"), "customer", "Link", 145, "Customer"),
		column(_("Customer Name"), "customer_name", "Data", 150),
		column(_("Return"), "is_return", "Check", 65),
		column(_("Return Against"), "return_against", "Data", 130),
		currency_column(_("Invoice Total"), "invoice_total"),
		currency_column(_("Net Total"), "invoice_net_total"),
		column(_("Qty"), "quantity", "Float", 75),
		currency_column(_("Paid Total"), "invoice_payment_total"),
		currency_column(_("Credit / Unpaid"), "credit_or_unpaid"),
		column(_("Payment Methods"), "payment_methods", "Data", 150),
		currency_column(_("Shift Sales Difference"), "shift_sales_difference", 145),
		column(_("Currency"), "currency", "Link", 85, "Currency"),
	]


def insert_payment_columns(columns, payment_category, view):
	insert_at = next(
		(index for index, item in enumerate(columns) if item["fieldname"] == "currency"), len(columns)
	)
	categories = ("Cash", "Card", "Other") if payment_category == "All" else (payment_category,)
	payment_columns = []

	for category_label in categories:
		category = category_label.lower()
		payment_columns.append(currency_column(_(f"{category_label} Payments"), f"{category}_payment"))
		if view != "Invoice Details":
			payment_columns.extend(
				[
					currency_column(_(f"Expected {category_label}"), f"expected_{category}"),
					currency_column(_(f"Counted {category_label}"), f"counted_{category}"),
					currency_column(_(f"{category_label} Difference"), f"{category}_difference"),
				]
			)

	if view != "Invoice Details":
		payment_columns.extend(
			[
				currency_column(_("Expected Total"), "expected_total"),
				currency_column(_("Counted Total"), "counted_total"),
				currency_column(_("Payment Difference"), "payment_difference"),
			]
		)

	return columns[:insert_at] + payment_columns + columns[insert_at:]


def column(label, fieldname, fieldtype, width, options=None):
	definition = {
		"label": label,
		"fieldname": fieldname,
		"fieldtype": fieldtype,
		"width": width,
	}
	if options:
		definition["options"] = options
	return definition


def currency_column(label, fieldname, width=120):
	return column(label, fieldname, "Currency", width, "currency")


def get_chart(view, data):
	if not data:
		return None

	rows = list(reversed(data[:20]))
	if view == "Daily Summary":
		labels = [str(row.report_date) for row in rows]
		actual_values = [row.actual_sales for row in rows]
		closing_values = [row.saved_closing_total for row in rows]
	elif view == "Shift Summary":
		labels = [row.opening_shift for row in rows]
		actual_values = [row.actual_sales for row in rows]
		closing_values = [row.saved_closing_total for row in rows]
	else:
		labels = [row.invoice for row in rows]
		actual_values = [row.invoice_total for row in rows]
		closing_values = [row.invoice_payment_total for row in rows]

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Actual Sales"), "values": actual_values},
				{
					"name": _("Saved Closing") if view != "Invoice Details" else _("Paid Total"),
					"values": closing_values,
				},
			],
		},
		"type": "bar",
		"colors": ["#2490ef", "#7cd6fd"],
	}


def get_report_summary(shift_rows, data, view):
	actual_sales = sum(flt(row.actual_sales) for row in shift_rows)
	saved_closing = sum(flt(row.saved_closing_total) for row in shift_rows)
	sales_difference = sum(flt(row.sales_difference) for row in shift_rows)
	counted_total = sum(flt(row.counted_total) for row in shift_rows)
	payment_difference = sum(flt(row.payment_difference) for row in shift_rows)
	invoice_count = (
		len(data)
		if view == "Invoice Details"
		else sum(cint(row.invoice_count) for row in shift_rows)
	)
	currency = shift_rows[0].currency if shift_rows else None

	return [
		{
			"value": actual_sales,
			"indicator": "Blue",
			"label": _("Actual Sales"),
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"value": saved_closing,
			"indicator": "Green",
			"label": _("Saved Closing"),
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"value": sales_difference,
			"indicator": "Red" if abs(sales_difference) >= DIFFERENCE_TOLERANCE else "Green",
			"label": _("Sales Difference"),
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"value": counted_total,
			"indicator": "Blue",
			"label": _("Counted Payments"),
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"value": payment_difference,
			"indicator": "Red" if abs(payment_difference) >= DIFFERENCE_TOLERANCE else "Green",
			"label": _("Payment Difference"),
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"value": invoice_count,
			"indicator": "Blue",
			"label": _("Submitted Invoices"),
			"datatype": "Int",
		},
	]
