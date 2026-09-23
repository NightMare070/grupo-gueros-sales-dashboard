import json
import re

def load_categories(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    categories = {}
    current_cat = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('## '):
            current_cat = line[3:].strip()
            categories[current_cat] = []
        elif line.startswith('- ') and current_cat:
            categories[current_cat].append(line[2:].strip())
    return categories

def categorize_product(description, categories):
    desc_upper = description.upper()
    # Search for subcategories first (most specific)
    all_subs = []
    for cat, subs in categories.items():
        for sub in subs:
            all_subs.append((sub, cat))
    
    # Sort by length descending to match most specific first
    all_subs.sort(key=lambda x: len(x[0]), reverse=True)
    
    for sub, cat in all_subs:
        if sub.upper() in desc_upper:
            return cat, sub
            
    return "OTROS", "OTROS"

# Paths
cat_path = r'C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md'
data_path = r'C:\Users\agente\dashboard_repo\dashboard_data.json'
ext_path = r'C:\Users\agente\dashboard_repo\yesterday_extraction.json'

# Load data
categories = load_categories(cat_path)
with open(data_path, 'r', encoding='utf-8') as f:
    dashboard_data = json.load(f)

with open(ext_path, 'r', encoding='utf-8') as f:
    extraction = json.load(f)

# 1. Update dates
yesterday_date = "2026-09-22"
if yesterday_date not in dashboard_data['dates']:
    dashboard_data['dates'].append(yesterday_date)

# 2. Update branch totals
for branch_name, total in extraction['totals'].items():
    if branch_name in dashboard_data['branches']:
        dashboard_data['branches'][branch_name].append(total)
    else:
        # If branch missing in dashboard_data but present in extraction
        dashboard_data['branches'][branch_name] = [0.0] * (len(dashboard_data['dates']) - 1) + [total]

# 3. Update product details with categories
for item in extraction['details']:
    # Exclusion filter (PROM or bloq)
    desc = item['Descripcion']
    if 'PROM' in desc.upper() or 'BLOQ' in desc.upper():
        continue
        
    cat, subcat = categorize_product(desc, categories)
    
    dashboard_data['products'].append({
        "Sucursal": item['Sucursal'],
        "Fecha": item['Fecha'],
        "Descripcion": desc,
        "Cantidad": item['Cantidad'],
        "Total": item['Total'],
        "categoria": cat,
        "subcategoria": subcat
    })

# Save updated dashboard_data.json
with open(data_path, 'w', encoding='utf-8') as f:
    json.dump(dashboard_data, f, indent=2, ensure_ascii=False)

print("Dashboard data updated successfully.")
