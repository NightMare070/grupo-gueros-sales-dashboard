import json
import os

EXTRACTED_FILE = "extracted_sales.json"
DASHBOARD_FILE = "dashboard_data.json"

def main():
    if not os.path.exists(EXTRACTED_FILE):
        print(f"Error: {EXTRACTED_FILE} not found. Run extract_sales.py first.")
        return
    
    if not os.path.exists(DASHBOARD_FILE):
        print(f"Error: {DASHBOARD_FILE} not found.")
        return

    with open(EXTRACTED_FILE, 'r', encoding='utf-8') as f:
        new_records = json.load(f)
    
    if not new_records:
        print("No new records to add.")
        return

    with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract the date from the first record
    target_date = new_records[0]['Fecha']
    
    # Update dates array
    if 'dates' not in data:
        data['dates'] = []
    if target_date not in data['dates']:
        data['dates'].append(target_date)
        data['dates'].sort() # Keep them chronological

    # Add records to products array
    if 'products' not in data:
        data['products'] = []
    
    # To avoid duplicates if the script is run twice for the same day,
    # we can filter out existing records for that date and sucursal/descripcion
    # But according to rules, we just append. Let's be safe and deduplicate.
    existing_keys = { (r['Sucursal'], r['Fecha'], r['Descripcion']) for r in data['products'] }
    
    added_count = 0
    for rec in new_records:
        key = (rec['Sucursal'], rec['Fecha'], rec['Descripcion'])
        if key not in existing_keys:
            data['products'].append(rec)
            added_count += 1

    with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully merged {added_count} new records for {target_date} into {DASHBOARD_FILE}.")

if __name__ == "__main__":
    main()
