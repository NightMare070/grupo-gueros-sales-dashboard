import pyodbc
import json
import os
from datetime import datetime, timedelta

# --- CONFIGURATION ---
USER = 'usuarioconsulta'
PWD = 'Hermes2026*'
JSON_PATH = r'C:\Users\agente\dashboard_repo\dashboard_data.json'
CATALOG_PATH = r'C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md'
LOG_PATH = r'C:\Users\agente\dashboard_repo\update_cron.log'

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

def log(msg):
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    print(msg)

def load_categories():
    cat_map = {}
    if not os.path.exists(CATALOG_PATH):
        log(f"Catalog not found at {CATALOG_PATH}")
        return cat_map
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        current_cat = None
        for line in f:
            line = line.strip()
            if line.startswith('## '):
                current_cat = line.replace('## ', '').strip()
            elif line.startswith('- ') and current_cat:
                sub = line.replace('- ', '').strip()
                cat_map[sub.upper()] = (current_cat, sub)
    return cat_map

def get_category(desc, cat_map):
    if not desc: return "OTROS", "OTROS"
    desc_up = desc.upper()
    for sub_up in sorted(cat_map.keys(), key=len, reverse=True):
        if sub_up in desc_up:
            return cat_map[sub_up]
    return "OTROS", "OTROS"

def run_update():
    try:
        # Clear log
        with open(LOG_PATH, 'w', encoding='utf-8') as f:
            f.write("Starting update process...\n")

        yesterday = datetime.now() - timedelta(days=1)
        date_sql = yesterday.strftime('%Y%m%d')
        date_json = yesterday.strftime('%Y-%m-%d')
        log(f"Target date: {date_json} (SQL: {date_sql})")

        cat_map = load_categories()
        log(f"Loaded {len(cat_map)} categories")

        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if date_json not in data['dates']:
            data['dates'].append(date_json)
            log(f"Added date {date_json} to JSON")

        daily_products = []
        
        for b in BRANCHES:
            conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={b['server']};DATABASE={b['db']};UID={USER};PWD={PWD};Encrypt=no;TrustServerCertificate=yes;"
            try:
                log(f"Connecting to {b['name']}...")
                with pyodbc.connect(conn_str, timeout=10) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute(f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{date_sql}' AND Nombre <> 'FALTANTES EMPLEADOS'")
                    total = cursor.fetchone()[0]
                    val = float(total) if total else 0.0
                    
                    # FIX: branches is a list of dicts
                    branch_obj = next((item for item in data['branches'] if item["name"] == b['name']), None)
                    if branch_obj:
                        branch_obj['values'].append(val)
                    else:
                        data['branches'].append({"name": b['name'], "values": [val]})
                    
                    cursor.execute(f"SELECT Articulo, Descripcion, SUM(CAST(Total AS FLOAT)) as Venta FROM rventas WHERE Fecha = '{date_sql}' AND Nombre <> 'FALTANTES EMPLEADOS' AND Descripcion NOT LIKE '%PROM%' AND Descripcion NOT LIKE '%bloq%' GROUP BY Articulo, Descripcion")
                    rows = cursor.fetchall()
                    for row in rows:
                        cat, sub = get_category(row.Descripcion, cat_map)
                        daily_products.append({
                            "Articulo": row.Articulo,
                            "Descripcion": row.Descripcion,
                            "Venta": float(row.Venta),
                            "Categoria": cat,
                            "Subcategoria": sub
                        })
                    log(f"Extracted {b['name']}: Total {val}, Items {len(rows)}")
            except Exception as e:
                log(f"Error extracting from {b['name']}: {e}")
                # Fill with 0.0 to keep length consistent
                branch_obj = next((item for item in data['branches'] if item["name"] == b['name']), None)
                if branch_obj:
                    branch_obj['values'].append(0.0)
                else:
                    data['branches'].append({"name": b['name'], "values": [0.0]})

        # Optimized Product Update
        prod_consolidated = {}
        for p in daily_products:
            name = p['Descripcion']
            if name not in prod_consolidated:
                prod_consolidated[name] = {"Venta": 0.0, "Cat": p['Categoria'], "Sub": p['Subcategoria']}
            prod_consolidated[name]["Venta"] += p['Venta']

        # Map existing products for O(1) lookup
        existing_prods = { (p.get('name') or p.get('Descripcion')): p for p in data['products'] }

        for name, info in prod_consolidated.items():
            if name in existing_prods:
                p_entry = existing_prods[name]
                if 'dates' not in p_entry: p_entry['dates'] = {}
                p_entry['dates'][date_json] = info['Venta']
                p_entry['categoria'] = info['Cat']
                p_entry['subcategoria'] = info['Sub']
            else:
                data['products'].append({
                    "name": name,
                    "categoria": info['Cat'],
                    "subcategoria": info['Sub'],
                    "dates": {date_json: info['Venta']}
                })

        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        log("Successfully updated dashboard_data.json")
        return True

    except Exception as e:
        log(f"FATAL ERROR: {e}")
        return False

if __name__ == '__main__':
    if not run_update():
        exit(1)
