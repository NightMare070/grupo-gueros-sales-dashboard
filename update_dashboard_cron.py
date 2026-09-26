import pyodbc
import json
import os
from datetime import datetime, timedelta

# --- CONFIGURATION ---
USER = 'usuarioconsulta'
PWD = 'Hermes2026*'
JSON_PATH = r'C:\Users\agente\dashboard_repo\dashboard_data.json'
CATALOG_PATH = r'C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md'

# Branch List from sucursales-grupo-gueros (Excluding Sede Aeronautica)
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

def load_categories():
    cat_map = {}
    if not os.path.exists(CATALOG_PATH):
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
    # Sort keys by length to match most specific first
    for sub_up in sorted(cat_map.keys(), key=len, reverse=True):
        if sub_up in desc_up:
            return cat_map[sub_up]
    return "OTROS", "OTROS"

def run_update():
    yesterday = datetime.now() - timedelta(days=1)
    date_sql = yesterday.strftime('%Y%m%d')
    date_json = yesterday.strftime('%Y-%m-%d')
    
    print(f"Updating for date: {date_json} (SQL: {date_sql})")
    
    cat_map = load_categories()
    
    # Load JSON
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 1. Update Dates list
    if date_json not in data['dates']:
        data['dates'].append(date_json)
    
    # 2. Extract and update totals + products
    daily_products = []
    
    for b in BRANCHES:
        conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={b['server']};DATABASE={b['db']};UID={USER};PWD={PWD};Encrypt=no;TrustServerCertificate=yes;"
        try:
            with pyodbc.connect(conn_str, timeout=10) as conn:
                cursor = conn.cursor()
                
                # Total for the branch
                cursor.execute(f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{date_sql}' AND Nombre <> 'FALTANTES EMPLEADOS'")
                total = cursor.fetchone()[0]
                val = float(total) if total else 0.0
                
                # Update branch array in JSON
                if b['name'] in data['branches']:
                    data['branches'][b['name']].append(val)
                else:
                    data['branches'][b['name']] = [val]
                
                # Detailed products
                cursor.execute(f"SELECT Articulo, Descripcion, SUM(CAST(Total AS FLOAT)) as Venta FROM rventas WHERE Fecha = '{date_sql}' AND Nombre <> 'FALTANTES EMPLEADOS' AND Descripcion NOT LIKE '%PROM%' AND Descripcion NOT LIKE '%bloq%' GROUP BY Articulo, Descripcion")
                for row in cursor.fetchall():
                    cat, sub = get_category(row.Descripcion, cat_map)
                    daily_products.append({
                        "Articulo": row.Articulo,
                        "Descripcion": row.Descripcion,
                        "Venta": float(row.Venta),
                        "Categoria": cat,
                        "Subcategoria": sub
                    })
                print(f"Extracted {b['name']}: total {val}")
        except Exception as e:
            print(f"Error {b['name']}: {e}")
            if b['name'] in data['branches']:
                data['branches'][b['name']].append(0.0)
            else:
                data['branches'][b['name']] = [0.0]

    # 3. Update Products list
    # Since the structure of 'products' in dashboard_data.json is an array of objects:
    # { "name": "...", "categoria": "...", "subcategoria": "...", "dates": { "YYYY-MM-DD": value } }
    
    # Consolidate products across branches for the day
    prod_consolidated = {}
    for p in daily_products:
        name = p['Descripcion']
        if name not in prod_consolidated:
            prod_consolidated[name] = {
                "Venta": 0.0, 
                "Cat": p['Categoria'], 
                "Sub": p['Subcategoria']
            }
        prod_consolidated[name]["Venta"] += p['Venta']

    for name, info in prod_consolidated.items():
        found = False
        for p_entry in data['products']:
            # Handle different potential structures of p_entry
            p_name = p_entry.get('name') or p_entry.get('Descripcion')
            if p_name == name:
                if 'dates' not in p_entry:
                    p_entry['dates'] = {}
                p_entry['dates'][date_json] = info['Venta']
                p_entry['categoria'] = info['Cat']
                p_entry['subcategoria'] = info['Sub']
                found = True
                break
        if not found:
            data['products'].append({
                "name": name,
                "categoria": info['Cat'],
                "subcategoria": info['Sub'],
                "dates": {date_json: info['Venta']}
            })

    # Save results
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("Successfully updated dashboard_data.json")

if __name__ == '__main__':
    run_update()
