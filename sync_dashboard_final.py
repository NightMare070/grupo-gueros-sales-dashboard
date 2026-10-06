import pyodbc
import json
import os
import re

# Configuration
USER = "usuarioconsulta"
PASS = "Hermes2026*"
DATE_SQL = "20261003"
DATE_ISO = "2026-10-03"

# Branches based on sucursales-grupo-gueros (excluding Aeronautica)
BRANCHES = {
    "Centeno": {"server": "25.66.11.46\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    "Dibujantes": {"server": "25.47.107.243\\SQLEXPRESS,1400", "db": "ACULCO"},
    "G. Cremero I": {"server": "25.58.53.229\\SQLEXPRESS,1400", "db": "CUAJIMALPA"},
    "G. Cremero II": {"server": "25.60.248.44\\SQLEXPRESS,1400", "db": "GCII"},
    "G. Cremero III": {"server": "25.36.154.112\\SQLEXPRESS,1400", "db": "GCIII"},
    "Xochimilco Uno": {"server": "25.36.200.140\\SQLEXPRESS,1400", "db": "XU"},
    "Xochimilco Dos": {"server": "25.36.21.81\\SQLEXPRESS,1400", "db": "XD"},
    "La Nueva": {"server": "25.17.7.172\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabases\\MyBusinessPOS2010.mdf"},
    "Los Gueros": {"server": "25.71.106.101\\SQLEXPRESS,1400", "db": "C:\\MyBusinessDatabase\\MyBusinessPOS2010.mdf"},
    "Sur 16": {"server": "25.36.2.227\\SQLEXPRESS,1400", "db": "S16"},
    "La Gran Monarca": {"server": "25.36.119.112\\SQLEXPRESS,1400", "db": "ERMITA"},
    "Mineros": {"server": "25.27.27.7\\SQLEXPRESS,1400", "db": "MINEROS"},
}

CAT_FILE = r"C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md"
DATA_FILE = r"C:\Users\agente\dashboard_repo\dashboard_data.json"

def get_branch_sales(name, config):
    conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={config['server']};DATABASE={config['db']};UID={USER};PWD={PASS};Encrypt=no;TrustServerCertificate=yes;"
    query = f"SELECT SUM(CAST(Total AS FLOAT)) as Total FROM rventas WHERE Fecha = '{DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'"
    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        cursor.execute(query)
        row = cursor.fetchone()
        conn.close()
        return float(row[0]) if row and row[0] else 0.0
    except Exception as e:
        print(f"Error querying {name}: {e}")
        return 0.0

def get_product_details(name, config):
    conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={config['server']};DATABASE={config['db']};UID={USER};PWD={PASS};Encrypt=no;TrustServerCertificate=yes;"
    query = f"SELECT Articulo, Descripcion, SUM(Cantidad) as Qty, SUM(CAST(Total AS FLOAT)) as Total FROM rventas WHERE Fecha = '{DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS' GROUP BY Articulo, Descripcion"
    products = []
    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        cursor.execute(query)
        for row in cursor.fetchall():
            products.append({"Articulo": row[0], "Descripcion": row[1], "Qty": float(row[2]) if row[2] else 0.0, "Total": float(row[3]) if row[3] else 0.0})
        conn.close()
    except Exception as e:
        print(f"Error details for {name}: {e}")
    return products

def main():
    print(f"Starting update for {DATE_ISO}...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if DATE_ISO not in data['dates']:
        data['dates'].append(DATE_ISO)

    for branch_name, config in BRANCHES.items():
        print(f"Processing {branch_name}...")
        total = get_branch_sales(branch_name, config)
        found = False
        for b in data['branches']:
            if isinstance(b, dict) and (b['name'].lower() == branch_name.lower() or branch_name.lower() in b['name'].lower()):
                b['data'].append(total)
                found = True
                break
        if not found:
            data['branches'].append({"name": branch_name, "data": [0.0] * (len(data['dates'])-1) + [total]})

    daily_products = {}
    for branch_name, config in BRANCHES.items():
        prods = get_product_details(branch_name, config)
        for p in prods:
            key = p['Articulo']
            if key not in daily_products:
                daily_products[key] = {"Descripcion": p['Descripcion'], "Qty": 0.0, "Total": 0.0}
            daily_products[key]['Qty'] += p['Qty']
            daily_products[key]['Total'] += p['Total']

    for key, p in daily_products.items():
        desc = p['Descripcion'].upper()
        cat, sub = "Otros", "Otros"
        if "QUESO" in desc: cat, sub = "Lácteos", "Quesos"
        elif "JAMON" in desc or "JAMÓN" in desc: cat, sub = "Embutidos", "Jamones"
        elif "SALCHICHA" in desc: cat, sub = "Embutidos", "Salchichas"
        elif "CREMA" in desc: cat, sub = "Lácteos", "Cremas"
        p['categoria'], p['subcategoria'] = cat, sub

    if "products" not in data: data["products"] = []
    for key, p in daily_products.items():
        found_prod = next((prod for prod in data['products'] if prod.get('Articulo') == key), None)
        if found_prod:
            if "values" not in found_prod: found_prod["values"] = {}
            found_prod["values"][DATE_ISO] = p['Total']
            found_prod['categoria'], found_prod['subcategoria'] = p['categoria'], p['subcategoria']
        else:
            data['products'].append({"Articulo": key, "Descripcion": p['Descripcion'], "categoria": p['categoria'], "subcategoria": p['subcategoria'], "values": {DATE_ISO: p['Total']}})

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print("Update complete.")

if __name__ == "__main__":
    main()
