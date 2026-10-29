import pyodbc
import json
import os
from datetime import datetime, timedelta

# Paths
REPO_DIR = r"C:\Users\agente\dashboard_repo"
CATEGORIES_PATH = r"C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md"
JSON_PATH = os.path.join(REPO_DIR, "dashboard_data.json")

# Date Logic: Yesterday relative to 2026-10-29
DATE_STAMP = "2026-10-28"
SQL_DATE = "20261028"

BRANCHES = [
    {"name": "Centeno", "server": r"25.66.11.46\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    {"name": "Dibujantes", "server": r"25.47.107.243\SQLEXPRESS,1400", "db": "ACULCO"},
    {"name": "G. Cremero I", "server": r"25.58.53.229\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    {"name": "G. Cremero II", "server": r"25.60.248.44\SQLEXPRESS,1400", "db": "GCII"},
    {"name": "G. Cremero III", "server": r"25.36.154.112\SQLEXPRESS,1400", "db": "GCIII"},
    {"name": "Xochimilco Uno", "server": r"25.36.200.140\SQLEXPRESS,1400", "db": "XU"},
    {"name": "Xochimilco Dos", "server": r"25.36.21.81\SQLEXPRESS,1400", "db": "XD"},
    {"name": "La Nueva", "server": r"25.17.7.172\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabases\MyBusinessPOS2010.mdf"},
    {"name": "Los Güeros", "server": r"25.71.106.101\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    {"name": "Sur 16", "server": r"25.36.2.227\SQLEXPRESS,1400", "db": "S16"},
    {"name": "La Gran Monarca", "server": r"25.36.119.112\SQLEXPRESS,1400", "db": "ERMITA"},
    {"name": "Mineros", "server": r"25.27.27.7\SQLEXPRESS,1400", "db": "MINEROS"},
]

def get_category_map():
    cat_map = {}
    current_cat = "OTROS"
    if not os.path.exists(CATEGORIES_PATH):
        return [], {}
    with open(CATEGORIES_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("## ") and not line.startswith("## Resumen"):
                current_cat = line.replace("## ", "").strip()
            elif line.startswith("- "):
                sub = line.replace("- ", "").strip()
                cat_map[sub] = current_cat
    sorted_subs = sorted(cat_map.keys(), key=len, reverse=True)
    return sorted_subs, cat_map

def get_category(desc, sorted_subs, cat_map):
    if not desc: return "OTROS", "OTROS"
    desc_up = desc.upper()
    for sub in sorted_subs:
        if sub.upper() in desc_up:
            return cat_map[sub], sub
    return "OTROS", "OTROS"

def fetch_branch_data(branch):
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={branch['server']};"
        f"DATABASE={branch['db']};"
        f"UID=usuarioconsulta;PWD=Hermes2026*;"
        f"Encrypt=no;TrustServerCertificate=yes;"
    )
    try:
        conn = pyodbc.connect(conn_str, timeout=15)
        cursor = conn.cursor()
        cursor.execute(f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{SQL_DATE}' AND Nombre <> 'FALTANTES EMPLEADOS'")
        total_sales = cursor.fetchone()[0] or 0.0
        cursor.execute(f"SELECT Articulo, Descripcion, SUM(CAST(Total AS FLOAT)) as Total, SUM(CAST(Cantidad AS FLOAT)) as Cantidad FROM rventas WHERE Fecha = '{SQL_DATE}' AND Nombre <> 'FALTANTES EMPLEADOS' GROUP BY Articulo, Descripcion")
        products = cursor.fetchall()
        conn.close()
        return total_sales, products
    except Exception as e:
        print(f"Error fetching {branch['name']}: {e}")
        return 0.0, []

def main():
    sorted_subs, cat_map = get_category_map()
    if not os.path.exists(JSON_PATH):
        print(f"Critical: JSON file not found at {JSON_PATH}")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if DATE_STAMP not in data['dates']:
        data['dates'].append(DATE_STAMP)
    
    new_products_list = []
    for branch in BRANCHES:
        print(f"Querying {branch['name']}...")
        total, prods = fetch_branch_data(branch)
        
        for b_entry in data['branches']:
            if b_entry['name'] == branch['name']:
                b_entry['values'].append(total)
                break
        
        for p in prods:
            cat, sub = get_category(p.Descripcion, sorted_subs, cat_map)
            new_products_list.append({
                "Sucursal": branch['name'],
                "Fecha": DATE_STAMP,
                "Descripcion": p.Descripcion,
                "Cantidad": float(p.Cantidad),
                "Total": float(p.Total),
                "categoria": cat,
                "subcategoria": sub
            })
    
    data['products'].extend(new_products_list)
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Successfully updated {JSON_PATH} for {DATE_STAMP}")

if __name__ == "__main__":
    main()
