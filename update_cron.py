import pyodbc
import json
import os
from datetime import datetime, timedelta

# --- CONFIGURATION ---
today = datetime.now()
yesterday = today - timedelta(days=1)
YESTERDAY_SQL = yesterday.strftime('%Y%m%d')
YESTERDAY_ISO = yesterday.strftime('%Y-%m-%d')

REPO_PATH = r'C:\Users\agente\dashboard_repo'
JSON_PATH = os.path.join(REPO_PATH, 'dashboard_data.json')
CATALOG_PATH = r'C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md'

BRANCHES = {
    "Centeno": {"server": "25.66.11.46\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    "Dibujantes": {"server": "25.47.107.243\\SQLEXPRESS,1400", "db": "ACULCO"},
    "GC1": {"server": "25.58.53.229\\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    "GC2": {"server": "25.60.248.44\\SQLEXPRESS,1400", "db": "GCII"},
    "GC3": {"server": "25.36.154.112\\SQLEXPRESS,1400", "db": "GCIII"},
    "Xochimilco Uno": {"server": "25.36.200.140\\SQLEXPRESS,1400", "db": "XU"},
    "Xochimilco Dos": {"server": "25.36.21.81\\SQLEXPRESS,1400", "db": "XD"},
    "La Nueva": {"server": "25.17.7.172\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabases\\MyBusinessPOS2010.mdf"},
    "Los Güeros": {"server": "25.71.106.101\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    "Sur 16": {"server": "25.36.2.227\\SQLEXPRESS,1400", "db": "S16"},
    "Monarca": {"server": "25.36.119.112\\SQLEXPRESS,1400", "db": "ERMITA"},
    "Mineros": {"server": "25.27.27.7\\SQLEXPRESS,1400", "db": "MINEROS"},
}

UID = 'usuarioconsulta'
PWD = 'Hermes2026*'

def get_conn_str(server, db):
    return f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={db};UID={UID};PWD={PWD};Encrypt=no;TrustServerCertificate=yes;'

def load_catalog():
    catalog = {}
    if not os.path.exists(CATALOG_PATH):
        return catalog, []
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        current_cat = None
        for line in f:
            line = line.strip()
            if line.startswith('## ') and not line.startswith('## CATEGORIA'):
                current_cat = line.replace('## ', '').strip()
            elif line.startswith('- ') and current_cat:
                subcat = line.replace('- ', '').strip()
                catalog[subcat] = current_cat
    sorted_subcats = sorted(catalog.keys(), key=len, reverse=True)
    return catalog, sorted_subcats

def categorize(desc, catalog, sorted_subcats):
    if not desc: return "OTROS", "OTROS"
    desc_up = desc.upper()
    for sub in sorted_subcats:
        if sub.upper() in desc_up: return catalog[sub], sub
    return "OTROS", "OTROS"

def main():
    print(f"Updating dashboard for {YESTERDAY_ISO}")
    catalog, sorted_subcats = load_catalog()
    
    if not os.path.exists(JSON_PATH):
        print(f"Error: JSON file not found at {JSON_PATH}")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if YESTERDAY_ISO not in data['dates']:
        data['dates'].append(YESTERDAY_ISO)

    daily_products = []
    for branch_name, cfg in BRANCHES.items():
        print(f"Processing {branch_name}...", end=" ")
        try:
            conn = pyodbc.connect(get_conn_str(cfg['server'], cfg['db']), timeout=10)
            cursor = conn.cursor()
            
            # Total Sales
            cursor.execute(f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{YESTERDAY_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'")
            row = cursor.fetchone()
            total_sales = float(row[0]) if row and row[0] else 0.0
            
            # update branches totals (dict structure)
            if branch_name in data['branches']:
                data['branches'][branch_name].append(total_sales)
            else:
                data['branches'][branch_name] = [0.0] * (len(data['dates']) - 1) + [total_sales]

            # Detailed Products
            cursor.execute(f"SELECT Articulo, Descripcion, SUM(CAST(Cantidad AS FLOAT)), SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{YESTERDAY_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS' GROUP BY Articulo, Descripcion")
            for row in cursor.fetchall():
                art, desc, cant, tot = row
                cat, subcat = categorize(desc, catalog, sorted_subcats)
                daily_products.append({
                    "Sucursal": branch_name, "Fecha": YESTERDAY_ISO, "Descripcion": desc,
                    "Cantidad": cant, "Total": tot, "categoria": cat, "subcategoria": subcat
                })
            conn.close()
            print(f"Done (${total_sales:,.2f})")
        except Exception as e:
            print(f"Error: {e}")
            if branch_name in data['branches']:
                data['branches'][branch_name].append(0.0)
            else:
                data['branches'][branch_name] = [0.0] * (len(data['dates']) - 1) + [0.0]

    data['products'].extend(daily_products)
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print("Successfully updated dashboard_data.json.")

if __name__ == '__main__':
    main()
