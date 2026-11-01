import pyodbc
import json
import os
from datetime import datetime

# --- Configuration ---
DATE_YESTERDAY_JSON = "2026-10-31"
DATE_YESTERDAY_SQL = "20261031"

REPO_PATH = r'C:\Users\agente\dashboard_repo'
JSON_DATA_PATH = os.path.join(REPO_PATH, 'dashboard_data.json')
CATEGORIES_PATH = r'C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md'

BRANCHES = [
    {"name": "Centeno", "server": r"25.66.11.46\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    {"name": "Dibujantes", "server": r"25.47.107.243\SQLEXPRESS,1400", "db": "ACULCO"},
    {"name": "GC1", "server": r"25.58.53.229\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    {"name": "GC2", "server": r"25.60.248.44\SQLEXPRESS,1400", "db": "GCII"},
    {"name": "GC3", "server": r"25.36.154.112\SQLEXPRESS,1400", "db": "GCIII"},
    {"name": "Xochimilco Uno", "server": r"25.36.200.140\SQLEXPRESS,1400", "db": "XU"},
    {"name": "Xochimilco Dos", "server": r"25.36.21.81\SQLEXPRESS,1400", "db": "XD"},
    {"name": "La Nueva", "server": r"25.17.7.172\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabases\MyBusinessPOS2010.mdf"},
    {"name": "Los Güeros", "server": r"25.71.106.101\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    {"name": "Sur 16", "server": r"25.36.2.227\SQLEXPRESS,1400", "db": "S16"},
    {"name": "Monarca", "server": r"25.36.119.112\SQLEXPRESS,1400", "db": "ERMITA"},
    {"name": "Mineros", "server": r"25.27.27.7\SQLEXPRESS,1400", "db": "MINEROS"},
]

CREDENTIALS = {
    "uid": "usuarioconsulta",
    "pwd": "Hermes2026*",
}

def load_categories():
    cats = {}
    try:
        with open(CATEGORIES_PATH, 'r', encoding='utf-8') as f:
            current_cat = None
            for line in f:
                line = line.strip()
                if line.startswith('## '):
                    current_cat = line.replace('## ', '').strip()
                    cats[current_cat] = []
                elif line.startswith('- ') and current_cat:
                    subcat = line.replace('- ', '').strip()
                    cats[current_cat].append(subcat)
    except Exception as e:
        print(f"Error loading categories: {e}")
    
    # Flat list of (subcat, cat) sorted by subcat length descending for matching
    flat = []
    for cat, subcats in cats.items():
        for sc in subcats:
            flat.append((sc, cat))
    flat.sort(key=lambda x: len(x[0]), reverse=True)
    return flat

def categorize_product(description, category_map):
    if not description: return "OTROS", "S/C"
    desc_up = description.upper()
    for sub, cat in category_map:
        if sub.upper() in desc_up:
            return cat, sub
    return "OTROS", "S/C"

def get_sales_for_branch(branch):
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={branch['server']};DATABASE={branch['db']};"
        f"UID={CREDENTIALS['uid']};PWD={CREDENTIALS['pwd']};"
        f"Encrypt=no;TrustServerCertificate=yes;"
    )
    
    total_sales = 0.0
    product_details = []
    
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        
        # Total Sales
        query_total = f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{DATE_YESTERDAY_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'"
        cursor.execute(query_total)
        row = cursor.fetchone()
        total_sales = float(row[0]) if row and row[0] else 0.0
        
        # Product Details
        query_prod = f"SELECT Descripcion, SUM(CAST(Cantidad AS FLOAT)) as Qty, SUM(CAST(Total AS FLOAT)) as Amt FROM rventas WHERE Fecha = '{DATE_YESTERDAY_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS' GROUP BY Descripcion"
        cursor.execute(query_prod)
        for row in cursor.fetchall():
            product_details.append({
                "descripcion": row[0],
                "qty": float(row[1]) if row[1] else 0.0,
                "amount": float(row[2]) if row[2] else 0.0
            })
        
        conn.close()
    except Exception as e:
        print(f"Error querying {branch['name']}: {e}")
        
    return total_sales, product_details

def main():
    cat_map = load_categories()
    
    # 1. Extract
    branch_totals = {}
    all_products_yesterday = []
    
    for b in BRANCHES:
        print(f"Processing {b['name']}...")
        total, prods = get_sales_for_branch(b)
        branch_totals[b['name']] = total
        for p in prods:
            cat, sub = categorize_product(p['descripcion'], cat_map)
            all_products_yesterday.append({
                "descripcion": p['descripcion'],
                "cantidad": p['qty'],
                "monto": p['amount'],
                "categoria": cat,
                "subcategoria": sub,
                "sucursal": b['name']
            })

    # 2. Update JSON
    try:
        with open(JSON_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Append date
        if DATE_YESTERDAY_JSON not in data['dates']:
            data['dates'].append(DATE_YESTERDAY_JSON)
        
        # Update branch totals
        for b_info in data['branches']:
            name = b_info['name']
            val = branch_totals.get(name, 0.0)
            b_info['values'].append(val)
        
        # Update products
        data['products'].extend(all_products_yesterday)
        
        with open(JSON_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print("dashboard_data.json updated successfully.")
        
    except Exception as e:
        print(f"Error updating JSON: {e}")
        exit(1)

if __name__ == "__main__":
    main()
