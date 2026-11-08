import json
import os
import subprocess

# Paths
REPO_PATH = r"C:\Users\agente\dashboard_repo"
CAT_PATH = r"C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md"
DATA_JSON_PATH = os.path.join(REPO_PATH, "dashboard_data.json")
RAW_JSON_PATH = os.path.join(REPO_PATH, "yesterday_sales_raw.json")

def load_categories(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    categories_map = {}
    lines = text.split('\n')
    current_cat = None
    for line in lines:
        line = line.strip()
        if line.startswith('### '):
            current_cat = line[4:].strip()
        elif current_cat and line and not line.startswith('#'):
            cleaned = line.replace('- ', '').replace('* ', '')
            parts = cleaned.split(',')
            for p in parts:
                p = p.strip()
                if p:
                    categories_map[p.lower()] = current_cat
    return categories_map

def main():
    # 1. Load Category Mapping
    cat_map = load_categories(CAT_PATH)
    sorted_keywords = sorted(cat_map.keys(), key=len, reverse=True)

    # 2. Load Existing Dashboard Data
    if not os.path.exists(DATA_JSON_PATH):
        print(f"Error: {DATA_JSON_PATH} not found")
        return
    with open(DATA_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 3. Load Yesterday's Raw Data
    if not os.path.exists(RAW_JSON_PATH):
        print(f"Error: {RAW_JSON_PATH} not found")
        return
    with open(RAW_JSON_PATH, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    y_date = raw['date']
    y_branch_totals = raw['branch_totals']
    y_products = raw['products']

    print(f"Updating dashboard for date: {y_date}")

    # 4. Update Dates
    if y_date not in data['dates']:
        data['dates'].append(y_date)
    else:
        # If date already exists, we remove it and the corresponding values to avoid duplication
        # (Simple approach: remove the date and pop the last value from each branch)
        idx = data['dates'].index(y_date)
        data['dates'].remove(y_date)
        for b in data['branches']:
            if len(b['values']) > idx:
                b['values'].pop(idx)
        data['dates'].append(y_date)

    # 5. Update Branch Totals
    for branch_name, total in y_branch_totals.items():
        branch_found = False
        for b in data['branches']:
            if b['name'] == branch_name:
                b['values'].append(total)
                branch_found = True
                break
        if not branch_found:
            # Create new branch entry
            data['branches'].append({
                "name": branch_name,
                "values": [0.0] * (len(data['dates']) - 1) + [total]
            })

    # 6. Update Products with Categorization
    for p in y_products:
        desc = p['Descripcion'].lower()
        cat_assigned = "Otros"
        subcat_assigned = "General"
        
        for kw in sorted_keywords:
            if kw in desc:
                cat_assigned = cat_map[kw]
                subcat_assigned = kw.title()
                break
        
        p['categoria'] = cat_assigned
        p['subcategoria'] = subcat_assigned
        
        # Append product to the list
        data['products'].append(p)

    # 7. Save Updated JSON
    with open(DATA_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Successfully updated {DATA_JSON_PATH}")

    # 8. Run Optimizer
    print("Running convert_data.js...")
    try:
        result = subprocess.run(['node', 'convert_data.js'], cwd=REPO_PATH, capture_output=True, text=True)
        if result.returncode == 0:
            print("Optimizer finished successfully.")
        else:
            print(f"Optimizer failed: {result.stderr}")
    except Exception as e:
        print(f"Error running optimizer: {e}")

if __name__ == "__main__":
    main()
