import frappe
from frappe import _


def validate_pos_profile(doc, method=None):
    # Auto-enable and auto-populate default custom order types if table is empty
    custom_types = doc.get("posa_custom_order_types") or []
    if not custom_types:
        doc.posa_use_custom_order_types = 1
        doc.append("posa_custom_order_types", {
            "order_type": "Dine In",
            "is_default": 1,
            "allow_table_selection": 1,
            "allow_rider_selection": 0
        })
        doc.append("posa_custom_order_types", {
            "order_type": "Delivery",
            "is_default": 0,
            "allow_table_selection": 0,
            "allow_rider_selection": 1
        })
        custom_types = doc.get("posa_custom_order_types") or []

    if getattr(doc, "posa_use_custom_order_types", 0):
        defaults_count = 0
        for row in custom_types:
            if getattr(row, "is_default", 0):
                defaults_count += 1

        if defaults_count == 0 and custom_types:
            custom_types[0].is_default = 1
            defaults_count = 1

        if defaults_count > 1:
            frappe.throw(
                _(
                    "Only one Order Type can be set as default in the Custom Order Types table."
                )
            )
