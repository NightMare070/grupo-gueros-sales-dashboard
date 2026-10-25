
import pyodbc
import json
import os
import subprocess
from datetime import datetime, timedelta

# --- Configuration ---
today = datetime.now()
yesterday = today - timedelta(days=1)
DATE_SQL = yesterday.strftime('%Y%m%d')
DATE_ISO = yesterday.strftime('%Y-%m-%d')

REPO_DIR = r'C:\Users\agente\dashboard_repo'
JSON_PATH = os.path.join(REPO_DIR, 'dashboard_data.json')
CATALOG_PATH = r'C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md'
USER = 'usuarioconsulta'
PWD = 'Hermes2026*'

# Connectivity map (Excluding Sede Aeronáutica)
BRANCHES = [
    {"name": "Centeno", "server": "25.66.11.46\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf", "json_name": "Centeno"},
    {"name": "Dibujantes", "server": "25.47.107.243\\SQLEXPRESS,1400", "db": "ACULCO", "json_name": "Dibujantes"},
    {"name": "Güero Cremero I", "server": "25.58.53.229\\SQLEXPRESS,1400", "db": "CUAJIMALPA", "json_name": "G. Cremero I"},
    {"name": "Güero Cremero II", "server": "25.60.248.44\\SQLEXPRESS,1400", "db": "GCII", "json_name": "G. Cremero II"},
    {"name": "Güero Cremero III", "server": "25.36.154.112\\SQLEXPRESS,1400", "db": "GCIII", "json_name": "G. Cremero III"},
    {"name": "Xochimilco Uno", "server": "25.36.200.140\\SQLEXPRESS,1400", "db": "XU", "json_name": "Xochimilco Uno"},
    {"name": "Xochimilco Dos", "server": "25.36.21.81\\SQLEXPRESS,1400", "db": "XD", "json_name": "Xochimilco Dos"},
    {"name": "La Nueva", "server": "25.17.7.172\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabases\\MyBusinessPOS2010.mdf", "json_name": "La Nueva"},
    {"name": "Los Güeros", "server": "25.71.106.101\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf", "json_name": "Los Güeros"},
    {"name": "Sur 16", "server": "25.36.2.227\\SQLEXPRESS,1400", "db": "S16", "json_name": "Sur 16"},
    {"name": "La Gran Monarca", "server": "25.36.119.112\\SQLEXPRESS,1400", "db": "ERMITA", "json_name": "La Gran Monarca"},
    {"name": "Mineros", "server": "25.27.27.7\\SQLEXPRESS,1400", "db": "MINEROS", "json_name": "Mineros"},
]

def parse_categories(path):
    cats = {}
    current_cat = None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('## ') and not line.startswith('## Resumen'):
                    current_cat = line[3:].strip()
                elif line.startswith('- ') and current_cat:
                    sub = line[2:].strip()
                    cats[sub.lower()] = (current_cat, sub)
    except Exception as e:
        print(f"Error parsing categories: {e}")
    return cats

def map_product(desc, cat_map):
    if not desc: return "OTROS", "OTROS"
    desc_low = desc.lower()
    sorted_subs = sorted(cat_map.keys(), key=len, reverse=True)
    for sub in sorted_subs:
        if sub in desc_low:
            return cat_map[sub]
    return "OTROS", "OTROS"

def get_branch_data(branch):
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={branch['server']};"
        f"DATABASE={branch['db']};"
        f"UID={USER};PWD={PWD};"
        f"Encrypt=no;TrustServerCertificate=yes;"
    )
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        cursor.execute(f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'")
        total = cursor.fetchone()[0] or 0.0
        cursor.execute(f"SELECT Descripcion, CAST(Total AS FLOAT), CAST(Cantidad AS FLOAT), proveedor FROM rventas WHERE Fecha = '{DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'")
        details = cursor.fetchall()
        conn.close()
        return total, details
    except Exception as e:
        print(f"Error querying {branch['name']}: {e}")
        return None, None

def main():
    print(f"--- Dashboard Update for {DATE_ISO} ---")
    cat_map = parse_categories(CATALOG_PATH)
    
    if not os.path.exists(JSON_PATH):
        print(f"JSON not found: {JSON_PATH}")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if DATE_ISO not in data['dates']:
        data['dates'].append(DATE_ISO)
    
    new_products = []
    for branch in BRANCHES:
        total, details = get_branch_data(branch)
        if total is None:
            total, details = 0.0, []
        
        # Update branches list: find the object with name == json_name
        branch_obj = next((b for b in data['branches'] if b['name'] == branch['json_name']), None)
        if branch_obj:
            branch_obj['values'].append(total)
        else:
            data['branches'].append({
                "name": branch['json_name'], 
                "values": [0.0] * (len(data['dates']) - 1) + [total]
            })

        for row in details:
            desc, val, qty, prov = row
            if not desc or "PROM" in desc.upper() or "BLOQ" in desc.upper():
                continue
            cat, sub = map_product(desc, cat_map)
            new_products.append({
                "Sucursal": branch['name'],
                "Fecha": DATE_ISO,
                "Descripcion": desc,
                "Cantidad": qty,
                "Total": val,
                "proveedor": prov,
                "categoria": cat,
                "subcategoria": sub
            })
    
    data['products'].extend(new_products)
    
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("Running optimizer (convert_data.js)...")
    subprocess.run(['node', 'convert_data.js'], cwd=REPO_DIR, capture_output=True)
    
    print("Pushing to GitHub...")
    try:
        # Git commands
        subprocess.run(['git', 'add', '.'], cwd=REPO_DIR, check=True)
        subprocess.run(['git', 'commit', '-m', f'Update dashboard: data for {DATE_ISO}'], cwd=REPO_DIR, check=True)
        subprocess.run(['git', 'push'], cwd=REPO_DIR, check=True)
        print("Successfully pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")

if __name__ == '__main__':
    main()
