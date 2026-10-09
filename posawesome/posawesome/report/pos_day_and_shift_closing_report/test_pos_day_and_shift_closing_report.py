from unittest import TestCase

import frappe

from posawesome.posawesome.report.pos_day_and_shift_closing_report.pos_day_and_shift_closing_report import (
	apply_shift_filters,
	build_daily_rows,
	build_shift_row,
	get_payment_category,
)


class TestPOSDayAndShiftClosingReport(TestCase):
	def test_payment_category_uses_profile_cash_mode_and_payment_type(self):
		self.assertEqual(get_payment_category("Till Cash", "General", "Till Cash"), "cash")
		self.assertEqual(get_payment_category("Visa", "Bank", "Till Cash"), "card")
		self.assertEqual(get_payment_category("Mobile Wallet", "Phone", "Till Cash"), "other")

	def test_shift_row_compares_live_invoice_totals_with_saved_closing(self):
		opening = frappe._dict(
			{
				"name": "POSA-OS-26-0000001",
				"posting_date": "2026-10-07",
				"period_start_date": "2026-10-07 09:00:00",
				"period_end_date": None,
				"status": "Closed",
				"company": "Test Company",
				"pos_profile": "Main POS",
				"user": "cashier@example.com",
			}
		)
		closing = frappe._dict(
			{
				"name": "POSA-CS-26-0000001",
				"period_end_date": "2026-10-07 18:00:00",
				"grand_total": 0,
				"net_total": 0,
				"total_quantity": 0,
				"docstatus": 1,
			}
		)
		invoices = [
			frappe._dict(
				{
					"name": "SINV-0001",
					"invoice_doctype": "Sales Invoice",
					"posting_date": "2026-10-07",
					"posting_time": "10:00:00",
					"customer": "Walk-in Customer",
					"customer_name": "Walk-in Customer",
					"owner": "cashier@example.com",
					"is_return": 0,
					"return_against": None,
					"conversion_rate": 1,
					"grand_total": 100,
					"base_grand_total": 100,
					"net_total": 90,
					"base_net_total": 90,
					"total_qty": 2,
					"change_amount": 10,
					"base_change_amount": 10,
				}
			),
			frappe._dict(
				{
					"name": "SINV-RET-0001",
					"invoice_doctype": "Sales Invoice",
					"posting_date": "2026-10-07",
					"posting_time": "11:00:00",
					"customer": "Walk-in Customer",
					"customer_name": "Walk-in Customer",
					"owner": "cashier@example.com",
					"is_return": 1,
					"return_against": "SINV-0000",
					"conversion_rate": 1,
					"grand_total": -20,
					"base_grand_total": -20,
					"net_total": -18,
					"base_net_total": -18,
					"total_qty": -1,
					"change_amount": 0,
					"base_change_amount": 0,
				}
			),
		]
		payments = {
			("Sales Invoice", "SINV-0001"): [
				frappe._dict(
					{
						"mode_of_payment": "Cash",
						"type": "Cash",
						"amount": 70,
						"base_amount": 70,
					}
				),
				frappe._dict(
					{
						"mode_of_payment": "Visa",
						"type": "Bank",
						"amount": 40,
						"base_amount": 40,
					}
				),
			],
			("Sales Invoice", "SINV-RET-0001"): [
				frappe._dict(
					{
						"mode_of_payment": "Cash",
						"type": "Cash",
						"amount": -20,
						"base_amount": -20,
					}
				)
			],
		}
		reconciliation = [
			frappe._dict(
				{
					"mode_of_payment": "Cash",
					"opening_amount": 0,
					"expected_amount": 40,
					"closing_amount": 40,
					"difference": 0,
				}
			),
			frappe._dict(
				{
					"mode_of_payment": "Visa",
					"opening_amount": 0,
					"expected_amount": 40,
					"closing_amount": 35,
					"difference": -5,
				}
			),
		]

		row, invoice_rows = build_shift_row(
			opening,
			closing,
			invoices,
			payments,
			reconciliation,
			{"Cash": "Cash", "Visa": "Bank"},
			"Cash",
			"PKR",
		)

		self.assertEqual(row.invoice_count, 2)
		self.assertEqual(row.gross_sales, 100)
		self.assertEqual(row.returns_total, 20)
		self.assertEqual(row.actual_sales, 80)
		self.assertEqual(row.sales_difference, 80)
		self.assertEqual(row.cash_payment, 40)
		self.assertEqual(row.card_payment, 40)
		self.assertEqual(row.card_difference, -5)
		self.assertEqual(row.payment_difference, -5)
		self.assertEqual(len(invoice_rows), 2)
		self.assertTrue(row.has_difference)

	def test_daily_summary_and_cash_filter(self):
		rows = [
			frappe._dict(
				{
					"report_date": "2026-10-07",
					"cashier": "cashier@example.com",
					"pos_profile": "Main POS",
					"company": "Test Company",
					"currency": "PKR",
					"opening_shift": "SHIFT-1",
					"shift_status": "Closed",
					"has_difference": True,
					"invoice_count": 2,
					"gross_sales": 100,
					"returns_total": 20,
					"actual_sales": 80,
					"saved_closing_total": 0,
					"sales_difference": 80,
					"cash_payment": 40,
					"card_payment": 40,
					"other_payment": 0,
					"invoice_payment_total": 80,
					"opening_cash": 0,
					"opening_card": 0,
					"opening_other": 0,
					"expected_cash": 40,
					"expected_card": 40,
					"expected_other": 0,
					"counted_cash": 40,
					"counted_card": 35,
					"counted_other": 0,
					"cash_difference": 0,
					"card_difference": -5,
					"other_difference": 0,
					"expected_total": 80,
					"counted_total": 75,
					"payment_difference": -5,
				}
			),
		]
		filters = frappe._dict({"payment_category": "Cash", "differences_only": 0})

		filtered = apply_shift_filters(rows, filters)
		daily = build_daily_rows(filtered)

		self.assertEqual(len(daily), 1)
		self.assertEqual(daily[0].shift_count, 1)
		self.assertEqual(daily[0].actual_sales, 80)
		self.assertEqual(daily[0].cash_payment, 40)
		self.assertEqual(daily[0].discrepancy_shift_count, 1)
