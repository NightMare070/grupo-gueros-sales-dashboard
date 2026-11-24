
import pyodbc
import json
import os
import subprocess
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# Use dynamic dates based on current execution time
now = datetime.now()
yesterday = now - timedelta(days=1)
YESTERDAY_ISO = yesterday.strftime('%Y-%m-%d')
YESTERDAY_SQL = yesterday.strftime('%Y%m%d')

REPO_PATH = r'C:\Users\agente\dashboard_repo'
JSON_PATH = os.path.join(REPO_PATH, 'dashboard_data.json')
CATALOG_PATH = r'C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md'

SERVERS = {
    "Centeno": {"server": r"25.66.11.46\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    "Dibujantes": {"server": r"25.47.107.243\SQLEXPRESS,1400", "db": "ACULCO"},
    "GC1": {"server": r"25.58.53.229\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    "GC2": {"server": r"25.60.248.44\SQLEXPRESS,1400", "db": "GCII"},
    "GC3": {"server": r"25.36.154.112\SQLEXPRESS,1400", "db": "GCIII"},
    "Xochimilco Uno": {"server": r"25.36.200.140\SQLEXPRESS,1400", "db": "XU"},
    "Xochimilco Dos": {"server": r"25.36.21.81\SQLEXPRESS,1400", "db": "XD"},
    "La Nueva": {"server": r"25.17.7.172\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabases\MyBusinessPOS2010.mdf"},
    "Los Güeros": {"server": r"25.71.106.101\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    "Sur 16": {"server": r"25.36.2.227\SQLEXPRESS,1400", "db": "S16"},
    "Monarca": {"server": r"25.36.119.112\SQLEXPRESS,1400", "db": "ERMITA"},
    "Mineros": {"server": r"25.27.27.7\SQLEXPRESS,1400", "db": "MINEROS"},
}

CREDENTIALS = {"uid": "usuarioconsulta", "pwd": "Hermes2026*"}

def get_connection(server_info):
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server_info['server']};"
        f"DATABASE={server_info['db']};"
        f"UID={CREDENTIALS['uid']};"
        f"PWD={CREDENTIALS['pwd']};"
        f"Encrypt=no;TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str, timeout=15)

def load_categories():
    cats = {}
    if not os.path.exists(CATALOG_PATH): return cats
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        current_cat = "OTROS"
        for line in f:
            line = line.strip()
            if line.startswith("## "): current_cat = line.replace("## ", "").strip()
            elif line.startswith("- "): cats[line.replace("- ", "").strip()] = current_cat
    return cats

def map_product(desc, cat_map):
    if not desc: return "OTROS", "OTROS"
    sorted_subcats = sorted(cat_map.keys(), key=len, reverse=True)
    for sc in sorted_subcats:
        if sc.upper() in desc.upper(): return cat_map[sc], sc
    return "OTROS", "OTROS"

def main():
    print(f"Processing data for: {YESTERDAY_ISO}")
    cat_map = load_categories()
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if YESTERDAY_ISO in data['dates']:
        print(f"Date {YESTERDAY_ISO} already exists. Skipping extraction.")
        return

    data['dates'].append(YESTERDAY_ISO)
    
    for branch_name, info in SERVERS.items():
        print(f"Updating {branch_name}...", end=" ")
        try:
            conn = get_connection(info)
            cursor = conn.cursor()
            
            # 1. Total Sales
            cursor.execute(f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE CONVERT(VARCHAR, Fecha, 112) = '{YESTERDAY_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'")
            row = cursor.fetchone()
            total_sales = float(row[0]) if row and row[0] else 0.0
            
            # Update branch value in list of dicts
            found = False
            for b_obj in data['branches']:
                if b_obj['name'] == branch_name:
                    b_obj['values'].append(total_sales)
                    found = True
                    break
            if not found:
                padding = [0.0] * (len(data['dates']) - 1)
                data['branches'].append({"name": branch_name, "values": padding + [total_sales]})

            # 2. Product details
            cursor.execute(f"SELECT Descripcion, SUM(CAST(Total AS FLOAT)), SUM(CAST(Cantidad AS FLOAT)) FROM rventas WHERE CONVERT(VARCHAR, Fecha, 112) = '{YESTERDAY_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS' GROUP BY Descripcion")
            rows = cursor.fetchall()
            
            for r in rows:
                desc, total, qty = r
                if not desc or "PROM" in desc.upper() or "BLOQ" in desc.upper(): continue
                cat, subcat = map_product(desc, cat_map)
                data['products'].append({
                    "Sucursal": branch_name,
                    "Fecha": YESTERDAY_ISO,
                    "Descripcion": desc,
                    "Cantidad": float(qty),
                    "Total": float(total),
                    "categoria": cat,
                    "subcategoria": subcat
                })
            conn.close()
            print("Done.")
        except Exception as e:
            print(f"ERROR: {e}")
            for b_obj in data['branches']:
                if b_obj['name'] == branch_name:
                    b_obj['values'].append(0.0)
                    break

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print("Running optimizer...")
    # Run optimizer in the repo directory
    subprocess.run(['node', 'convert_data.js'], cwd=REPO_PATH, check=True)
    print("Optimizer finished.")

if __name__ == "__main__":
    main()
