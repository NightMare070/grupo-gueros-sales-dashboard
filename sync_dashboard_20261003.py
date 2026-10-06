import pyodbc
import json
import os
import re

# Configuration
USER = "usuarioconsulta"
PASS = "Hermes2026*"
DATE_SQL = "20261003"
DATE_ISO = "2026-10-03"

# Branch list according to sucursales-grupo-gueros, excluding Sede Aeronautica
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

def get_conn_str(server, db):
    return f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={db};UID={USER};PWD={PASS};Encrypt=no;TrustServerCertificate=yes;"

def parse_categories(content):
    categories = {}
    current_cat = None
    for line in content.split('\n'):
        line = line.strip()
        if not line: continue
        if line.startswith('## '):
            current_cat = line.replace('## ', '').strip()
            categories[current_cat] = []
        elif line.startswith('- ') and current_cat:
            subcat = line.replace('- ', '').strip()
            categories[current_cat].append(subcat)
    
    flat_map = []
    for cat, subs in categories.items():
        for sub in subs:
            flat_map.append((sub, cat))
    
    flat_map.sort(key=lambda x: len(x[0]), reverse=True)
    return flat_map

def categorize_product(desc, flat_map):
    if not desc: return "OTRO", "OTRO"
    desc_up = desc.upper()
    for sub, cat in flat_map:
        if sub.upper() in desc_up:
            return cat, sub
    return "OTRO", "OTRO"

def main():
    cat_file = r"C:\Users\agente\AppData\Local\HermesSecondBrain\Catalog\Categories_Summary.md"
    if not os.path.exists(cat_file):
        print(f"Category file not found: {cat_file}")
        return

    with open(cat_file, 'r', encoding='utf-8') as f:
        cat_map = parse_categories(f.read())

    branch_totals = {}
    daily_products = []

    for branch, config in BRANCHES.items():
        print(f"Processing {branch}...")
        try:
            conn_str = get_conn_str(config["server"], config["db"])
            with pyodbc.connect(conn_str, timeout=10) as conn:
                cursor = conn.cursor()
                
                # Total Sales
                cursor.execute(f"SELECT SUM(CAST(Total AS FLOAT)) FROM rventas WHERE Fecha = '{DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'")
                row = cursor.fetchone()
                total = float(row[0]) if row and row[0] else 0.0
                branch_totals[branch] = total
                
                # Detailed Sales
                cursor.execute(f"SELECT Descripcion, Total FROM rventas WHERE Fecha = '{DATE_SQL}' AND Nombre <> 'FALTANTES EMPLEADOS'")
                for row in cursor.fetchall():
                    desc = row[0]
                    val = float(row[1]) if row[1] else 0.0
                    cat, sub = categorize_product(desc, cat_map)
                    daily_products.append({
                        "fecha": DATE_ISO,
                        "sucursal": branch,
                        "producto": desc,
                        "valor": val,
                        "categoria": cat,
                        "subcategoria": sub
                    })
        except Exception as e:
            print(f"Error in {branch}: {e}")
            branch_totals[branch] = 0.0

    json_path = r"C:\Users\agente\dashboard_repo\dashboard_data.json"
    if not os.path.exists(json_path):
        print(f"Data JSON not found: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if DATE_ISO not in data["dates"]:
        data["dates"].append(DATE_ISO)

    for branch_name, total in branch_totals.items():
        found = False
        for b in data["branches"]:
            if b["name"].lower() == branch_name.lower() or branch_name.lower() in b["name"].lower():
                b["values"].append(total)
                found = True
                break
        if not found:
            data["branches"].append({"name": branch_name, "values": [0.0]* (len(data["dates"])-1) + [total]})

    data["products"].extend(daily_products)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Dashboard data updated successfully.")

if __name__ == "__main__":
    main()
