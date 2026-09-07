"""Custom POS Invoice class that integrates POS Awesome shift logic."""

from erpnext.accounts.doctype.pos_invoice.pos_invoice import POSInvoice as ERPNextPOSInvoice

from posawesome.posawesome.api.invoice import validate_shift


class CustomPOSInvoice(ERPNextPOSInvoice):
    """Override ERPNext POS Invoice to respect POS Awesome opening shifts."""

    def validate_pos_opening_entry(self):
        """Allow POS invoices when a POS Awesome shift is open.

        If the invoice references ``posa_pos_opening_shift`` we validate that
        shift using POS Awesome's rules and skip the standard ERPNext
        validation for ``POS Opening Entry``. Otherwise, fall back to the
        default ERPNext behaviour.
        """

        if getattr(self, "posa_pos_opening_shift", None):
            # Use existing shift validation from POS Awesome
            validate_shift(self)
            return

        # No POS Awesome shift - use ERPNext's validation
        super().validate_pos_opening_entry()

    def update_item_tax_map(self):
        super().update_item_tax_map()
        _apply_item_tax_template_precedence(self)


def _apply_item_tax_template_precedence(doc):
    import json
    for item in doc.get("items") or []:
        if item.get("item_tax_template"):
            item_map = {}
            if item.get("item_tax_rate"):
                try:
                    item_map = json.loads(item.item_tax_rate) if isinstance(item.item_tax_rate, str) else dict(item.item_tax_rate)
                except Exception:
                    item_map = {}
            for tax in doc.get("taxes") or []:
                if tax.get("account_head") and tax.account_head not in item_map:
                    item_map[tax.account_head] = 0.0
            item.item_tax_rate = json.dumps(item_map)

