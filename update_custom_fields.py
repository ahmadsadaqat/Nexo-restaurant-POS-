import json

with open('posawesome/fixtures/custom_field.json', 'r') as f:
    data = json.load(f)

# Fields to add
new_fields = [
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "dt": "POS Profile",
        "fieldname": "posa_enable_kot_printing",
        "fieldtype": "Check",
        "insert_after": "print_format",
        "label": "Enable KOT Printing",
        "module": "POSAwesome"
    },
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "dt": "POS Profile",
        "fieldname": "posa_kot_printer_profile",
        "fieldtype": "Link",
        "options": "POSA Printer Profile",
        "insert_after": "posa_enable_kot_printing",
        "label": "KOT Printer Profile",
        "depends_on": "eval:doc.posa_enable_kot_printing==1",
        "module": "POSAwesome"
    },
    {
        "docstatus": 0,
        "doctype": "Custom Field",
        "dt": "POS Profile",
        "fieldname": "posa_kot_print_format",
        "fieldtype": "Link",
        "options": "Print Format",
        "insert_after": "posa_kot_printer_profile",
        "label": "KOT Print Format",
        "depends_on": "eval:doc.posa_enable_kot_printing==1",
        "module": "POSAwesome"
    }
]

# Avoid duplicates
existing_fields = {f.get("fieldname") for f in data if f.get("dt") == "POS Profile"}
for nf in new_fields:
    if nf["fieldname"] not in existing_fields:
        data.append(nf)

with open('posawesome/fixtures/custom_field.json', 'w') as f:
    json.dump(data, f, indent=1)

