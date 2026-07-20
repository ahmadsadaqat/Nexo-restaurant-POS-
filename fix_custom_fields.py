import json

with open('posawesome/fixtures/custom_field.json', 'r') as f:
    data = json.load(f)

for item in data:
    if "name" not in item and "dt" in item and "fieldname" in item:
        item["name"] = f"{item['dt']}-{item['fieldname']}"

with open('posawesome/fixtures/custom_field.json', 'w') as f:
    json.dump(data, f, indent=1)

