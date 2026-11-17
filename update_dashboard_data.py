import pyodbc
import json
import os
from datetime import datetime, timedelta

# --- Configuration ---
SESSIONS_CONFIG = [
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
    {"name": "Maria Pistolas", "server": r"25.29.129.162\SQLEXPRESS,1400", "db": "MARIAPISTOLAS"},
    {"name": "La Gran Monarca", "server": r"25.36.119.112\SQLEXPRESS,1400", "db": "ERMITA"},
    {"name": "Mineros", "server": r"25.27.27.7\SQLEXPRESS,1400", "db": "MINEROS"},
]

JSON_PATH = r'C:\Users\agente\dashboard_repo\dashboard_data.json'
CATS_PATH = r'C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md'
USER_ID = 'usuarioconsulta'
PASSWORD = 'Hermes2026*'
TARGET_DATE_SQL = '20261116'
TARGET_DATE_ISO = '2026-11-16'

def parse_categories(path):
    cats = {}
    current_cat = None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('## '):
                    current_cat = line.replace('## ', '').strip()
                    cats[current_cat] = []
                elif line.startswith('- ') and current_cat:
                    sub = line.replace('- ', '').strip()
                    cats[current_cat].append(sub)
    except Exception as e:
        print(f"Error reading categories file: {e}")
    return cats

def get_category_mapping(cats_dict):
    mapping = {}
    for cat, subs in cats_dict.items():
        for sub in sorted(subs, key=len, reverse=True):
            mapping[sub.lower()] = (cat, sub)
    return mapping

def fetch_branch_data(branch):
    conn_str = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server={branch['server']};Database={branch['db']};"
        f"UID={USER_ID};PWD={PASSWORD};"
        f"Encrypt=no;TrustServerCertificate=yes;"
    )
    
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        
        # Total daily sales
        cursor.execute(f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{TARGET_DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'")
        total = cursor.fetchone()[0] or 0.0
        
        # Detailed records - Removed 'Proveedor' as it caused errors in previous run
        cursor.execute(f"SELECT Descripcion, Cantidad, Total FROM rventas WHERE Fecha = '{TARGET_DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'")
        records = cursor.fetchall()
        
        conn.close()
        return total, records
    except Exception as e:
        print(f"Error fetching data from {branch['name']}: {e}")
        return 0.0, []

def main():
    cats_dict = parse_categories(CATS_PATH)
    cat_map = get_category_mapping(cats_dict)
    
    if not os.path.exists(JSON_PATH):
        print(f"JSON file not found at {JSON_PATH}")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Update Dates
    if TARGET_DATE_ISO not in data['dates']:
        data['dates'].append(TARGET_DATE_ISO)
    
    daily_products = []
    
    # Process branches
    # data['branches'] is expected to be a list of objects: {"name": "...", "values": []}
    for b_conf in SESSIONS_CONFIG:
        total, records = fetch_branch_data(b_conf)
        
        branch_name = b_conf['name']
        found = False
        for b_data in data['branches']:
            if b_data['name'] == branch_name:
                b_data['values'].append(total)
                found = True
                break
        if not found:
            data['branches'].append({"name": branch_name, "values": [0.0] * (len(data['dates'])-1) + [total]})
            
        for rec in records:
            desc = rec[0] if rec[0] else "UNKNOWN"
            qty = float(rec[1]) if rec[1] else 0.0
            val = float(rec[2]) if rec[2] else 0.0
            
            desc_lower = desc.lower()
            cat, sub = "OTROS", "OTROS"
            for sub_key, (c, s) in cat_map.items():
                if sub_key in desc_lower:
                    cat, sub = c, s
                    break
            
            daily_products.append({
                "Sucursal": branch_name,
                "Fecha": TARGET_DATE_ISO,
                "Descripcion": desc,
                "Cantidad": qty,
                "Total": val,
                "proveedor": "Unknown", # Placeholder since column is missing in DB
                "categoria": cat,
                "subcategoria": sub
            })
            
    data['products'].extend(daily_products)
    
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully updated {JSON_PATH} with data for {TARGET_DATE_ISO}")

if __name__ == '__main__':
    main()
