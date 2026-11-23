import json
import os
from datetime import datetime, timedelta

# Paths
DASHBOARD_DATA_PATH = r"C:\Users\agente\dashboard_repo\dashboard_data.json"
RAW_SALES_PATH = r"C:\Users\agente\dashboard_repo\yesterday_sales_raw.json"
CATEGORIES_PATH = r"C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md"

def load_categories(path):
    cats = {}
    current_cat = None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('# Resumen'): continue
                if line.startswith('## '):
                    current_cat = line.replace('## ', '').strip()
                    cats[current_cat] = []
                elif line.startswith('- ') and current_cat:
                    subcat = line.replace('- ', '').strip()
                    cats[current_cat].append(subcat)
    except Exception as e:
        print(f"Error loading categories: {e}")
    return cats

def find_category(description, categories):
    desc_up = description.upper()
    # Search by subcategory first (more specific)
    # Sort subcategories by length descending to match the most specific first
    for cat, subcats in categories.items():
        sorted_subcats = sorted(subcats, key=len, reverse=True)
        for sub in sorted_subcats:
            if sub.upper() in desc_up:
                return cat, sub
    return "OTROS", "OTROS"

def main():
    # Load data
    try:
        with open(DASHBOARD_DATA_PATH, 'r', encoding='utf-8') as f:
            dashboard_data = json.load(f)
        with open(RAW_SALES_PATH, 'r', encoding='utf-8') as f:
            raw_sales = json.load(f)
    except Exception as e:
        print(f"Error loading JSON files: {e}")
        return

    categories_map = load_categories(CATEGORIES_PATH)

    # 1. Handle Date
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')

    if yesterday_str not in dashboard_data['dates']:
        dashboard_data['dates'].append(yesterday_str)

    # 2. Update Branch Totals
    for branch_info in raw_sales['branches']:
        name = branch_info['name']
        total_sales = branch_info['total_sales']
        
        branch_found = False
        for b in dashboard_data['branches']:
            if b['name'] == name:
                b['sales'].append(total_sales)
                branch_found = True
                break
        
        if not branch_found:
            dashboard_data['branches'].append({
                "name": name,
                "sales": [total_sales] 
            })

    # 3. Update Products
    yesterday_products = {}
    for branch_info in raw_sales['branches']:
        for p in branch_info['products']:
            key = p['articulo']
            if key not in yesterday_products:
                yesterday_products[key] = {
                    "descripcion": p['descripcion'],
                    "ventas": 0,
                    "monto": 0
                }
            yesterday_products[key]['ventas'] += p['cantidad']
            yesterday_products[key]['monto'] += p['total']

    for key, data in yesterday_products.items():
        cat, subcat = find_category(data['descripcion'], categories_map)
        
        prod_found = False
        for p in dashboard_data['products']:
            if p['articulo'] == key:
                p['ventas_diarias'].append({
                    "fecha": yesterday_str,
                    "cantidad": data['ventas'],
                    "monto": data['monto']
                })
                prod_found = True
                break
        
        if not prod_found:
            dashboard_data['products'].append({
                "articulo": key,
                "descripcion": data['descripcion'],
                "categoria": cat,
                "subcategoria": subcat,
                "ventas_diarias": [{
                    "fecha": yesterday_str,
                    "cantidad": data['ventas'],
                    "monto": data['monto']
                }]
            })

    # Save updated JSON
    with open(DASHBOARD_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully updated dashboard_data.json for {yesterday_str}")

if __name__ == "__main__":
    main()
