import json

with open('posawesome/fixtures/custom_field.json', 'r') as f:
    data = json.load(f)

for item in data:
    if item.get("fieldname") == "posa_kot_printer_profile":
        if item.get("depends_on") == "eval:doc.posa_enable_kot_printing":
            item["depends_on"] = "eval:doc.posa_enable_kot_printing==1"

with open('posawesome/fixtures/custom_field.json', 'w') as f:
    json.dump(data, f, indent=1)
