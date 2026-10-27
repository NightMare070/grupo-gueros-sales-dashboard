import pyodbc
import json
import os
from datetime import datetime, timedelta

# --- CONFIG ---
USER = "usuarioconsulta"
PASS = "Hermes2026*"
JSON_PATH = r"C:\Users\agente\dashboard_repo\dashboard_data.json"
CATALOG_PATH = r"C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md"

BRANCHES = [
    {"name": "Centeno", "server": "25.66.11.46\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    {"name": "Dibujantes", "server": "25.47.107.243\\SQLEXPRESS,1400", "db": "ACULCO"},
    {"name": "GC1", "server": "25.58.53.229\\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    {"name": "GC2", "server": "25.60.248.44\\SQLEXPRESS,1400", "db": "GCII"},
    {"name": "GC3", "server": "25.36.154.112\\SQLEXPRESS,1400", "db": "GCIII"},
    {"name": "Xochimilco 1", "server": "25.36.200.140\\SQLEXPRESS,1400", "db": "XU"},
    {"name": "Xochimilco 2", "server": "25.36.21.81\\SQLEXPRESS,1400", "db": "XD"},
    {"name": "La Nueva", "server": "25.17.7.172\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabases\\MyBusinessPOS2010.mdf"},
    {"name": "Los Güeros", "server": "25.71.106.101\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    {"name": "Sur 16", "server": "25.36.2.227\\SQLEXPRESS,1400", "db": "S16"},
    {"name": "Monarca", "server": "25.36.119.112\\SQLEXPRESS,1400", "db": "ERMITA"},
    {"name": "Mineros", "server": "25.27.27.7\\SQLEXPRESS,1400", "db": "MINEROS"},
]

# 1. Date Calculation (Yesterday)
yesterday_dt = datetime.now() - timedelta(days=1)
yesterday_sql = yesterday_dt.strftime('%Y%m%d')
yesterday_disp = yesterday_dt.strftime('%Y-%m-%d')

def load_categories(path):
    catalog = {}
    current_cat = None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("## "):
                    current_cat = line.replace("## ", "").strip()
                    catalog[current_cat] = []
                elif line.startswith("- ") and current_cat:
                    catalog[current_cat].append(line.replace("- ", "").strip())
    except Exception as e:
        print(f"Error loading catalog: {e}")
    return catalog

def map_product(desc, catalog):
    if not desc: return "OTROS", "SIN CATEGORIA"
    desc_upper = desc.upper()
    best_match = None # (cat, subcat, len)
    for cat, subcats in catalog.items():
        if cat == "CATEGORIA": continue
        for sub in subcats:
            if sub.upper() in desc_upper:
                if best_match is None or len(sub) > best_match[2]:
                    best_match = (cat, sub, len(sub))
    if best_match:
        return best_match[0], best_match[1]
    return "OTROS", "SIN CATEGORIA"

def get_conn(server, db):
    # Using Driver 18 standard for current environment as per skills
    conn_str = f"Driver={{ODBC Driver 18 for SQL Server}};Server={server};Database={db};UID={USER};PWD={PASS};Encrypt=no;TrustServerCertificate=yes;"
    return pyodbc.connect(conn_str, timeout=15)

def main():
    print(f"--- Starting Dashboard Update for {yesterday_disp} ---")
    catalog = load_categories(CATALOG_PATH)
    
    if not os.path.exists(JSON_PATH):
        print(f"Error: JSON file not found at {JSON_PATH}")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    daily_sales = {} # branch: total
    daily_products = [] # list of {name, amount, cat, sub}
    
    for b in BRANCHES:
        print(f"Querying {b['name']}...")
        try:
            conn = get_conn(b['server'], b['db'])
            # Total Sales for Yesterday
            q_total = f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{yesterday_sql}' AND Nombre <> 'FALTANTES EMPLEADOS'"
            res = conn.execute(q_total).fetchone()
            val = float(res[0]) if res[0] else 0.0
            daily_sales[b['name']] = val
            
            # Detailed Products for Yesterday
            q_prod = f"SELECT Articulo, Descripcion, SUM(CAST(Total AS FLOAT)) AS total FROM rventas WHERE Fecha = '{yesterday_sql}' AND Nombre <> 'FALTANTES EMPLEADOS' GROUP BY Articulo, Descripcion"
            prods = conn.execute(q_prod).fetchall()
            for p in prods:
                # Use the a-priori mapped categories
                cat, sub = map_product(p.Descripcion, catalog)
                daily_products.append({
                    "name": p.Descripcion,
                    "amount": float(p.total),
                    "category": cat,
                    "subcategory": sub
                })
            conn.close()
        except Exception as e:
            print(f"Warning: Failed to extract data from {b['name']}: {e}")
            daily_sales[b['name']] = 0.0

    # Update JSON structure
    data['dates'].append(yesterday_disp)
    
    # Update Branch totals
    for b_entry in data['branches']:
        name = b_entry['name']
        val = daily_sales.get(name, 0.0)
        b_entry['values'].append(val)
    
    # Update Products distribution
    # We store history of daily totals for each product to enable trends
    for p in daily_products:
        existing = next((x for x in data['products'] if x['name'] == p['name']), None)
        if existing:
            existing['sales'].append(p['amount'])
            existing['category'] = p['category']
            existing['subcategory'] = p['subcategory']
        else:
            data['products'].append({
                "name": p['name'],
                "category": p['category'],
                "subcategory": p['subcategory'],
                "sales": [p['amount']]
            })
    
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully updated {JSON_PATH} for {yesterday_disp}")

if __name__ == "__main__":
    main()
