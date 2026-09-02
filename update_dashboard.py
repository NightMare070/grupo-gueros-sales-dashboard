import json
import os
import pyodbc
from datetime import datetime, timedelta

# --- CONFIGURATION ---
REPO_DIR = 'C:/Users/agente/dashboard_repo'
DATA_FILE = os.path.join(REPO_DIR, 'dashboard_data.json')
HTML_FILE = os.path.join(REPO_DIR, 'index.html')

# Connectivity from sucursales-grupo-gueros skill
BRANCHES = [
    {"name": "Centeno", "server": "25.66.11.46\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    {"name": "Sede Aeronautica", "server": "25.59.101.93\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    {"name": "Dibujantes", "server": "25.47.107.243\\SQLEXPRESS,1400", "db": "ACULCO"},
    {"name": "G. Cremero I", "server": "25.58.53.229\\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    {"name": "G. Cremero II", "server": "25.60.248.44\\SQLEXPRESS,1400", "db": "GCII"},
    {"name": "G. Cremero III", "server": "25.36.154.112\\SQLEXPRESS,1400", "db": "GCIII"},
    {"name": "Xochimilco Uno", "server": "25.36.200.140\\SQLEXPRESS,1400", "db": "XU"},
    {"name": "Xochimilco Dos", "server": "25.36.21.81\\SQLEXPRESS,1400", "db": "XD"},
    {"name": "La Nueva", "server": "25.17.7.172\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabases\\MyBusinessPOS2010.mdf"},
    {"name": "Los Güeros", "server": "25.71.106.101\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    {"name": "Sur 16", "server": "25.36.2.227\\SQLEXPRESS,1400", "db": "S16"},
    {"name": "La Gran Monarca", "server": "25.36.119.112\\SQLEXPRESS,1400", "db": "ERMITA"},
]

def get_dates():
    now = datetime.now()
    yesterday_dash = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday_sql = (now - timedelta(days=1)).strftime('%Y%m%d')
    return yesterday_dash, yesterday_sql

def fetch_branch_data(branch, sql_date):
    # Connection parameters from skill
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={branch['server']};"
        f"DATABASE={branch['db']};"
        f"UID=usuarioconsulta;"
        f"PWD=Hermes2026*;"
        f"Encrypt=no;TrustServerCertificate=yes;"
    )
    
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        
        # 1. Total Sales
        cursor.execute(f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{sql_date}' AND Nombre <> 'FALTANTES EMPLEADOS'")
        row = cursor.fetchone()
        total = float(row[0]) if row and row[0] else 0.0
        
        # 2. Product Detail
        cursor.execute(f"SELECT Descripcion, CAST(Cantidad AS FLOAT), CAST(Total AS FLOAT) FROM rventas WHERE Fecha = '{sql_date}' AND Nombre <> 'FALTANTES EMPLEADOS'")
        products = []
        for r in cursor.fetchall():
            products.append({
                "Descripcion": r[0] if r[0] else "Unknown",
                "Cantidad": r[1] if r[1] else 0.0,
                "Total": r[2] if r[2] else 0.0
            })
        
        conn.close()
        return total, products
    except Exception as e:
        print(f"Error connecting to {branch['name']} ({branch['server']}): {e}")
        return 0.0, []

def main():
    yesterday_dash, yesterday_sql = get_dates()
    print(f"Processing real data for: {yesterday_dash} (SQL: {yesterday_sql})")

    daily_totals = {}
    all_products = []
    
    for b in BRANCHES:
        print(f"Extracting from {b['name']}...")
        total, prods = fetch_branch_data(b, yesterday_sql)
        daily_totals[b['name']] = total
        for p in prods:
            all_products.append({
                "Sucursal": b['name'],
                "Fecha": yesterday_dash,
                "Descripcion": p['Descripcion'],
                "Cantidad": p['Cantidad'],
                "Total": p['Total']
            })

    # Update JSON database
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            db = json.load(f)
    else:
        db = {"dates": [], "branches": {}, "products": []}

    if yesterday_dash not in db['dates']:
        db['dates'].append(yesterday_dash)
        db['dates'].sort()

    for branch, total in daily_totals.items():
        if branch not in db['branches']:
            db['branches'][branch] = [0] * (len(db['dates']) - 1)
        while len(db['branches'][branch]) < len(db['dates']):
            db['branches'][branch].append(0)
        idx = db['dates'].index(yesterday_dash)
        db['branches'][branch][idx] = total

    db['products'].extend(all_products)
    
    with open(DATA_FILE, 'w') as f:
        json.dump(db, f, indent=4)
    print("Successfully updated dashboard_data.json with real data")

    # Regenerate HTML
    if not os.path.exists(HTML_FILE):
        print("Critical Error: index.html template not found!")
        return

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()

    html_full_data = {
        "dates": db['dates'],
        "branches": db['branches'],
        "colors": ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316', '#6366f1', '#14b8a6', '#a855f7']
    }
    html_product_data = db['products']

    def replace_constant(content, var_name, new_value):
        start_marker = f"const {var_name} ="
        start_idx = content.find(start_marker)
        if start_idx == -1: return content
        end_idx = content.find(";", start_idx)
        if end_idx == -1: return content
        return content[:start_idx] + start_marker + " " + json.dumps(new_value, indent=12) + ";" + content[end_idx+1:]

    html_content = replace_constant(html_content, "FULL_DATA", html_full_data)
    html_content = replace_constant(html_content, "PRODUCT_DATA", html_product_data)

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Successfully regenerated index.html")

if __name__ == "__main__":
    main()
