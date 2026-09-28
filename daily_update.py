import pyodbc
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# Target Yesterday's data
today = datetime.now()
yesterday = today - timedelta(days=1)
DATE_SQL = yesterday.strftime('%Y%m%d')
DATE_DISPLAY = yesterday.strftime('%Y-%m-%d')

REPO_PATH = r'C:\Users\agente\dashboard_repo'
JSON_PATH = os.path.join(REPO_PATH, 'dashboard_data.json')
CATALOG_PATH = r'C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md'

BRANCHES_CONFIG = [
    {"name": "Centeno", "server": "25.66.11.46\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    {"name": "Dibujantes", "server": "25.47.107.243\\SQLEXPRESS,1400", "db": "ACULCO"},
    {"name": "GC1", "server": "25.58.53.229\\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    {"name": "GC2", "server": "25.60.248.44\\SQLEXPRESS,1400", "db": "GCII"},
    {"name": "GC3", "server": "25.36.154.112\\SQLEXPRESS,1400", "db": "GCIII"},
    {"name": "Xochimilco Uno", "server": "25.36.200.140\\SQLEXPRESS,1400", "db": "XU"},
    {"name": "Xochimilco Dos", "server": "25.36.21.81\\SQLEXPRESS,1400", "db": "XD"},
    {"name": "La Nueva", "server": "25.17.7.172\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabases\\MyBusinessPOS2010.mdf"},
    {"name": "Los Güeros", "server": "25.71.106.101\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    {"name": "Sur 16", "server": "25.36.2.227\\SQLEXPRESS,1400", "db": "S16"},
    {"name": "Monarca", "server": "25.36.119.112\\SQLEXPRESS,1400", "db": "ERMITA"},
    {"name": "Mineros", "server": "25.27.27.7\\SQLEXPRESS,1400", "db": "MINEROS"},
]

def get_connection(server, db):
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};DATABASE={db};"
        f"UID=usuarioconsulta;PWD=Hermes2026*;"
        f"Encrypt=no;TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str, timeout=20)

def parse_categories(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    categories = {}
    current_cat = None
    for line in content.splitlines():
        line = line.strip()
        if not line: continue
        if line.startswith('## ') or line.startswith('# '):
            current_cat = line.replace('#', '').strip()
        elif line.startswith('- ') and ':' in line and current_cat:
            parts = line[2:].split(':', 1)
            subcat = parts[0].strip()
            keywords = [k.strip().lower() for k in parts[1].split(',')]
            for kw in keywords:
                if kw:
                    categories[kw] = (current_cat, subcat)
    return categories

def categorize_product(description, categories_map):
    desc_lower = description.lower()
    sorted_kws = sorted(categories_map.keys(), key=len, reverse=True)
    for kw in sorted_kws:
        if kw in desc_lower:
            return categories_map[kw]
    return ("Otros", "Otros")

def main():
    print(f"Updating dashboard for Date: {DATE_DISPLAY} (SQL: {DATE_SQL})")
    cat_map = parse_categories(CATALOG_PATH)
    
    if not os.path.exists(JSON_PATH):
        print(f"Error: JSON file not found at {JSON_PATH}")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if DATE_DISPLAY not in data.get('dates', []):
        if 'dates' not in data: data['dates'] = []
        data['dates'].append(DATE_DISPLAY)

    if 'branches' not in data: data['branches'] = {}
    if 'products' not in data: data['products'] = []

    for b_cfg in BRANCHES_CONFIG:
        name = b_cfg['name']
        server = b_cfg['server']
        db = b_cfg['db']
        
        try:
            print(f"Fetching {name}...", end=' ')
            conn = get_connection(server, db)
            
            sql_total = f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'"
            res_total = pd.read_sql(sql_total, conn).iloc[0, 0]
            total_val = float(res_total) if res_total is not None else 0.0
            
            sql_prods = f"SELECT Articulo, Descripcion, SUM(CAST(Total AS FLOAT)) as Total FROM rventas WHERE Fecha = '{DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS' GROUP BY Articulo, Descripcion"
            df_prods = pd.read_sql(sql_prods, conn)
            
            if name not in data['branches']:
                data['branches'][name] = []
            data['branches'][name].append(total_val)
            
            for _, row in df_prods.iterrows():
                desc = str(row['Descripcion'])
                if "PROM" in desc.upper() or "BLOQ" in desc.upper():
                    continue
                cat, subcat = categorize_product(desc, cat_map)
                data['products'].append({
                    "date": DATE_DISPLAY,
                    "branch": name,
                    "articulo": row['Articulo'],
                    "descripcion": desc,
                    "total": float(row['Total']),
                    "categoria": cat,
                    "subcategoria": subcat
                })
            conn.close()
            print(f"OK (${total_val:,.2f})")
        except Exception as e:
            print(f"ERROR: {e}")

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Success: {JSON_PATH} updated.")

if __name__ == '__main__':
    main()
