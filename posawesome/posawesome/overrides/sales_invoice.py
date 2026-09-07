"""Custom Sales Invoice class that preserves Item Tax Template precedence over payment taxes."""

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice as ERPNextSalesInvoice
from posawesome.posawesome.overrides.pos_invoice import _apply_item_tax_template_precedence


class CustomSalesInvoice(ERPNextSalesInvoice):
    def update_item_tax_map(self):
        super().update_item_tax_map()
        _apply_item_tax_template_precedence(self)
