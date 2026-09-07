# -*- coding: utf-8 -*-
# Copyright (c) 2026, defendicon and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from posawesome.posawesome.api.payment_tax import resolve_tax_template_for_payments, apply_payment_tax_template


class TestPaymentTaxResolution(FrappeTestCase):
    def setUp(self):
        super(TestPaymentTaxResolution, self).setUp()

        # Get or create company
        company = frappe.db.get_single_value("Global Defaults", "default_company")
        if not company:
            company = frappe.db.get_value("Company", {})
        if not company:
            company = "_Test Company"
            if not frappe.db.exists("Company", company):
                c = frappe.new_doc("Company")
                c.company_name = company
                c.default_currency = "USD"
                c.insert(ignore_permissions=True)
        self.company = company

        # Find a cost center for the company
        cost_center = frappe.db.get_value("Cost Center", {"company": self.company})
        if not cost_center:
            cc = frappe.new_doc("Cost Center")
            cc.cost_center_name = "Test CC"
            cc.company = self.company
            cc.insert(ignore_permissions=True)
            cost_center = cc.name
        self.cost_center = cost_center

        # Find a warehouse for the company
        warehouse = frappe.db.get_value("Warehouse", {"company": self.company})
        if not warehouse:
            w = frappe.new_doc("Warehouse")
            w.warehouse_name = "Test Warehouse"
            w.company = self.company
            w.insert(ignore_permissions=True)
            warehouse = w.name
        self.warehouse = warehouse

        # Find an account for taxes
        account = frappe.db.get_value("Account", {"company": self.company, "is_group": 0})
        if not account:
            account = "Stock Adjustment - _TC" # fallback
        self.account = account

        # Create modes of payment
        if not frappe.db.exists("Mode of Payment", "Cash Payment Test"):
            mop = frappe.new_doc("Mode of Payment")
            mop.mode_of_payment = "Cash Payment Test"
            mop.type = "Cash"
            mop.append("accounts", {
                "company": self.company,
                "default_account": self.account
            })
            mop.insert(ignore_permissions=True)
        else:
            mop = frappe.get_doc("Mode of Payment", "Cash Payment Test")
            mop.type = "Cash"
            if not mop.accounts:
                mop.append("accounts", {
                    "company": self.company,
                    "default_account": self.account
                })
                mop.save(ignore_permissions=True)

        if not frappe.db.exists("Mode of Payment", "Card Payment Test"):
            mop = frappe.new_doc("Mode of Payment")
            mop.mode_of_payment = "Card Payment Test"
            mop.type = "Bank"
            mop.append("accounts", {
                "company": self.company,
                "default_account": self.account
            })
            mop.insert(ignore_permissions=True)
        else:
            mop = frappe.get_doc("Mode of Payment", "Card Payment Test")
            mop.type = "Bank"
            if not mop.accounts:
                mop.append("accounts", {
                    "company": self.company,
                    "default_account": self.account
                })
                mop.save(ignore_permissions=True)

        # Create tax templates using actual ERPNext names
        cash_tmpl_name = frappe.db.get_value("Sales Taxes and Charges Template", {"title": "Cash Tax Template", "company": self.company})
        if not cash_tmpl_name:
            tmpl = frappe.new_doc("Sales Taxes and Charges Template")
            tmpl.title = "Cash Tax Template"
            tmpl.company = self.company
            tmpl.append("taxes", {
                "charge_type": "On Net Total",
                "account_head": self.account,
                "rate": 5,
                "description": "Cash Tax"
            })
            tmpl.insert(ignore_permissions=True)
            cash_tmpl_name = tmpl.name
        self.cash_tmpl_name = cash_tmpl_name

        card_tmpl_name = frappe.db.get_value("Sales Taxes and Charges Template", {"title": "Card Tax Template", "company": self.company})
        if not card_tmpl_name:
            tmpl = frappe.new_doc("Sales Taxes and Charges Template")
            tmpl.title = "Card Tax Template"
            tmpl.company = self.company
            tmpl.append("taxes", {
                "charge_type": "On Net Total",
                "account_head": self.account,
                "rate": 10,
                "description": "Card Tax"
            })
            tmpl.insert(ignore_permissions=True)
            card_tmpl_name = tmpl.name
        self.card_tmpl_name = card_tmpl_name

        # Create POS Profile
        if not frappe.db.exists("POS Profile", "Test Payment Tax POS Profile"):
            profile = frappe.new_doc("POS Profile")
            profile.name = "Test Payment Tax POS Profile"
            profile.pos_profile_name = "Test Payment Tax POS Profile"
            profile.company = self.company
            profile.warehouse = self.warehouse
            profile.cost_center = self.cost_center
            profile.taxes_and_charges = self.cash_tmpl_name
            profile.posa_enable_payment_tax_templates = 1
            profile.write_off_account = self.account
            profile.write_off_cost_center = self.cost_center

            # Add child payment tax templates
            profile.append("posa_payment_tax_templates", {
                "mode_of_payment": "Cash Payment Test",
                "tax_template": self.cash_tmpl_name
            })
            profile.append("posa_payment_tax_templates", {
                "mode_of_payment": "Card Payment Test",
                "tax_template": self.card_tmpl_name
            })

            # Add mandatory payments
            profile.append("payments", {
                "mode_of_payment": "Cash Payment Test",
                "default": 1
            })
            profile.append("payments", {
                "mode_of_payment": "Card Payment Test",
                "default": 0
            })
            profile.insert(ignore_permissions=True)
        else:
            profile = frappe.get_doc("POS Profile", "Test Payment Tax POS Profile")
            profile.company = self.company
            profile.warehouse = self.warehouse
            profile.cost_center = self.cost_center
            profile.posa_enable_payment_tax_templates = 1
            profile.taxes_and_charges = self.cash_tmpl_name
            profile.write_off_account = self.account
            profile.write_off_cost_center = self.cost_center

            profile.set("posa_payment_tax_templates", [])
            profile.append("posa_payment_tax_templates", {
                "mode_of_payment": "Cash Payment Test",
                "tax_template": self.cash_tmpl_name
            })
            profile.append("posa_payment_tax_templates", {
                "mode_of_payment": "Card Payment Test",
                "tax_template": self.card_tmpl_name
            })

            profile.set("payments", [])
            profile.append("payments", {
                "mode_of_payment": "Cash Payment Test",
                "default": 1
            })
            profile.append("payments", {
                "mode_of_payment": "Card Payment Test",
                "default": 0
            })
            profile.save(ignore_permissions=True)

    def test_resolution_logic(self):
        # 1. Cash only
        template = resolve_tax_template_for_payments(
            "Test Payment Tax POS Profile",
            [{"mode_of_payment": "Cash Payment Test", "amount": 100}]
        )
        self.assertEqual(template, self.cash_tmpl_name)

        # 2. Card only
        template = resolve_tax_template_for_payments(
            "Test Payment Tax POS Profile",
            [{"mode_of_payment": "Card Payment Test", "amount": 100}]
        )
        self.assertEqual(template, self.card_tmpl_name)

        # 3. Mixed payments (Card dominant)
        template = resolve_tax_template_for_payments(
            "Test Payment Tax POS Profile",
            [
                {"mode_of_payment": "Cash Payment Test", "amount": 40},
                {"mode_of_payment": "Card Payment Test", "amount": 60}
            ]
        )
        self.assertEqual(template, self.card_tmpl_name)

        # 4. Mixed payments (Cash dominant)
        template = resolve_tax_template_for_payments(
            "Test Payment Tax POS Profile",
            [
                {"mode_of_payment": "Cash Payment Test", "amount": 70},
                {"mode_of_payment": "Card Payment Test", "amount": 30}
            ]
        )
        self.assertEqual(template, self.cash_tmpl_name)

        # 5. Disabled feature
        frappe.db.set_value("POS Profile", "Test Payment Tax POS Profile", "posa_enable_payment_tax_templates", 0)
        template = resolve_tax_template_for_payments(
            "Test Payment Tax POS Profile",
            [{"mode_of_payment": "Card Payment Test", "amount": 100}]
        )
        self.assertIsNone(template)
