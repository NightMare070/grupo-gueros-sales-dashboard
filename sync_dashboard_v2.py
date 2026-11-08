import pyodbc
import json
import os
import sys
import subprocess
from datetime import datetime

# --- CONFIGURATION ---
REPO_PATH = r"C:\Users\agente\dashboard_repo"
DATA_JSON_PATH = os.path.join(REPO_PATH, "dashboard_data.json")
CATALOG_PATH = r"C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md"
LOG_FILE = os.path.join(REPO_PATH, "sync_log.txt")

# DATE LOGIC (Fixed for this specific cron run)
DATE_SQL = "20261101"
DATE_ISO = "2026-11-01"

# CREDENTIALS
UID = "usuarioconsulta"
PWD = "Hermes2026*"

# BRANCHES (Excluding Sede Aeronautica)
BRANCHES = {
    "Centeno": {"server": r"25.66.11.46\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    "Dibujantes": {"server": r"25.47.107.243\SQLEXPRESS,1400", "db": "ACULCO"},
    "GC1": {"server": r"25.58.53.229\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    "GC2": {"server": r"25.60.248.44\SQLEXPRESS,1400", "db": "GCII"},
    "GC3": {"server": r"25.36.154.112\SQLEXPRESS,1400", "db": "GCIII"},
    "Xochimilco 1": {"server": r"25.36.200.140\SQLEXPRESS,1400", "db": "XU"},
    "Xochimilco 2": {"server": r"25.36.21.81\SQLEXPRESS,1400", "db": "XD"},
    "La Nueva": {"server": r"25.17.7.172\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabases\MyBusinessPOS2010.mdf"},
    "Los Gueros": {"server": r"25.71.106.101\SQLEXPRESS,1400", "db": r"C:\MyBusinessDatabase\MyBusinessPOS2010.mdf"},
    "Sur 16": {"server": r"25.36.2.227\SQLEXPRESS,1400", "db": "S16"},
    "Monarca": {"server": r"25.36.119.112\SQLEXPRESS,1400", "db": "ERMITA"},
    "Mineros": {"server": r"25.27.27.7\SQLEXPRESS,1400", "db": "MINEROS"},
}

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    print(msg)

def load_categories():
    mapping = {} # subcat -> cat
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        current_cat = None
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith("##"):
                current_cat = line.replace("##", "").strip()
            elif line.startswith("-") and current_cat:
                subcat = line.replace("-", "").strip()
                mapping[subcat] = current_cat
        return mapping
    except Exception as e:
        log(f"Error loading catalog: {e}")
        return {}

def get_category_for_prod(desc, mapping):
    if not desc: return "Otros", "Otros"
    desc_up = desc.upper()
    sorted_subcats = sorted(mapping.keys(), key=len, reverse=True)
    for sub in sorted_subcats:
        if sub.upper() in desc_up:
            return mapping[sub], sub
    return "Otros", "Otros"

def extract_branch_data(name, config, mapping):
    log(f"Extracting {name}...")
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={config['server']};DATABASE={config['db']};"
        f"UID={UID};PWD={PWD};Encrypt=no;TrustServerCertificate=yes;"
    )
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        # Use simple query to avoid casting errors on old SQL versions
        query = f"SELECT Articulo, Descripcion, Cantidad, Total FROM rventas WHERE Fecha = '{DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'"
        df = pd.read_sql(query, conn)
        conn.close()
        
        total_sales = float(df['Total'].sum())
        products_list = []
        for _, row in df.iterrows():
            cat, subcat = get_category_for_prod(row['Descripcion'], mapping)
            products_list.append({
                "Sucursal": name,
                "Fecha": DATE_ISO,
                "Descripcion": row['Descripcion'],
                "Cantidad": float(row['Cantidad']) if row['Cantidad'] else 0.0,
                "Total": float(row['Total']) if row['Total'] else 0.0,
                "proveedor": "",
                "categoria": cat,
                "subcategoria": subcat
            })
        return total_sales, products_list
    except Exception as e:
        log(f"FAILED {name}: {e}")
        return 0.0, []

def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f: f.write("--- Sync Start ---\n")
    mapping = load_categories()
    log(f"Loaded {len(mapping)} mapping entries.")
    
    try:
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log(f"Error loading JSON: {e}")
        sys.exit(1)
    
    # 1. Handle Date
    if DATE_ISO not in data['dates']:
        data['dates'].append(DATE_ISO)
    
    all_new_products = []
    
    # 2. Process Branches
    for name, config in BRANCHES.items():
        sales, prods = extract_branch_data(name, config, mapping)
        
        # Ensure branches is a dict: { "BranchName": [val1, val2...] }
        if name not in data['branches']:
            data['branches'][name] = []
        
        # Pad to match dates length
        while len(data['branches'][name]) < len(data['dates']) - 1:
            data['branches'][name].append(0.0)
            
        data['branches'][name].append(sales)
        all_new_products.extend(prods)
    
    # 3. Update products list
    data['products'].extend(all_new_products)
    
    # Save JSON
    with open(DATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log("Updated dashboard_data.json")
    
    # 4. Optimize
    try:
        subprocess.run(["node", "convert_data.js"], cwd=REPO_PATH, check=True)
        log("Optimized assets via convert_data.js")
    except Exception as e:
        log(f"Optimization failed: {e}")
        
    # 5. Git Push
    try:
        subprocess.run(["git", "add", "."], cwd=REPO_PATH, check=True)
        subprocess.run(["git", "commit", "-m", f"Update dashboard: data for {DATE_ISO}"], cwd=REPO_PATH, check=True)
        subprocess.run(["git", "push"], cwd=REPO_PATH, check=True)
        log("Pushed to GitHub successfully")
    except Exception as e:
        log(f"Git push failed: {e}")

if __name__ == "__main__":
    import pandas as pd
    main()
