"""Custom Sales Order class that preserves Item Tax Template precedence over payment taxes."""

from erpnext.selling.doctype.sales_order.sales_order import SalesOrder as ERPNextSalesOrder
from posawesome.posawesome.overrides.pos_invoice import _apply_item_tax_template_precedence


class CustomSalesOrder(ERPNextSalesOrder):
    def update_item_tax_map(self):
        super().update_item_tax_map()
        _apply_item_tax_template_precedence(self)
